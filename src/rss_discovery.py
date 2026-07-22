from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Iterable, Optional
from urllib.parse import urljoin, urlparse, urlunparse

import feedparser
from bs4 import BeautifulSoup

from .http_client import HttpClient


RSS_MIME_KEYWORDS = ("rss", "atom", "rdf", "xml")
COMMON_RSS_PATHS = ("/feed", "/rss", "/atom.xml", "/feed.xml", "/rss.xml", "/index.xml")


@dataclass(frozen=True)
class FeedEntry:
    title: str
    url: str
    published_at: str


def _site_root(url: str) -> str:
    parsed = urlparse(url)
    return urlunparse((parsed.scheme, parsed.netloc, "", "", "", ""))


def _candidate_urls(page_url: str, html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    candidates: list[str] = []
    for link in soup.find_all("link"):
        type_value = (link.get("type") or "").lower()
        rel_value = " ".join(link.get("rel") or []).lower()
        href = link.get("href")
        if href and ("alternate" in rel_value or any(item in type_value for item in RSS_MIME_KEYWORDS)):
            if any(item in type_value for item in RSS_MIME_KEYWORDS):
                candidates.append(urljoin(page_url, href))

    root = _site_root(page_url)
    candidates.extend(urljoin(root, path) for path in COMMON_RSS_PATHS)
    candidates.extend(urljoin(page_url.rstrip("/") + "/", path.lstrip("/")) for path in COMMON_RSS_PATHS)

    seen = set()
    unique = []
    for url in candidates:
        if url not in seen:
            seen.add(url)
            unique.append(url)
    return unique


def parse_feed(text: str) -> list[FeedEntry]:
    feed = feedparser.parse(text)
    entries: list[FeedEntry] = []
    for entry in feed.entries:
        url = entry.get("link", "")
        if not url:
            continue
        entries.append(
            FeedEntry(
                title=entry.get("title", "").strip(),
                url=url,
                published_at=(
                    entry.get("published")
                    or entry.get("updated")
                    or entry.get("created")
                    or ""
                ).strip(),
            )
        )
    return entries


def discover_feed(client: HttpClient, page_url: str) -> Optional[str]:
    page = client.get(page_url)
    candidates: list[str] = []
    if page:
        candidates.extend(_candidate_urls(page.url, page.text))
    else:
        root = _site_root(page_url)
        candidates.extend(urljoin(root, path) for path in COMMON_RSS_PATHS)

    for feed_url in candidates:
        result = client.get(feed_url)
        if not result:
            continue
        entries = parse_feed(result.text)
        if entries:
            logging.info("RSS discovered for %s: %s (%s entries)", page_url, feed_url, len(entries))
            return result.url

    logging.info("No RSS discovered for %s", page_url)
    return None


def fetch_feed_entries(
    client: HttpClient,
    feed_url: str,
    limit: int | None = 100,
) -> Iterable[FeedEntry]:
    result = client.get(feed_url)
    if not result:
        return []
    entries = parse_feed(result.text)
    return entries if limit is None else entries[:limit]
