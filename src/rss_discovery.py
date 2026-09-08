from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Iterable, Optional
from urllib.parse import quote, urljoin, urlparse, urlunparse

import feedparser
from bs4 import BeautifulSoup

from .http_client import HttpClient


RSS_MIME_KEYWORDS = ("rss", "atom", "rdf", "xml")
COMMON_RSS_PATHS = ("/feed", "/rss", "/atom.xml", "/feed.xml", "/rss.xml", "/index.xml")
FEEDLY_STREAM_API = "https://feedly.com/v3/streams/contents"


@dataclass(frozen=True)
class FeedEntry:
    title: str
    url: str
    published_at: str
    summary: str = ""
    content_is_full: bool = False


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


def _entry_text(entry) -> tuple[str, bool]:
    excerpt_values = [
        entry.get("summary"),
        entry.get("description"),
    ]
    full_values = []
    for content_item in entry.get("content") or []:
        if isinstance(content_item, dict):
            full_values.append(content_item.get("value"))

    candidates: list[tuple[str, bool]] = []
    for value, is_full in [
        *((value, False) for value in excerpt_values),
        *((value, True) for value in full_values),
    ]:
        if not value:
            continue
        text = " ".join(BeautifulSoup(str(value), "html.parser").stripped_strings)
        if text:
            candidates.append((text, is_full))
    # feedparser can expose content:encoded through both summary and content.
    # Prefer the explicitly full variant when their lengths tie.
    return max(
        candidates,
        key=lambda item: (len(item[0]), item[1]),
        default=("", False),
    )


def parse_feed(text: str) -> list[FeedEntry]:
    feed = feedparser.parse(text)
    entries: list[FeedEntry] = []
    for entry in feed.entries:
        url = entry.get("link", "")
        if not url:
            continue
        entry_text, content_is_full = _entry_text(entry)
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
                summary=entry_text,
                content_is_full=content_is_full,
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
    *,
    auth: tuple[str, str] | None = None,
    required: bool = False,
) -> Iterable[FeedEntry]:
    request_options = {}
    if auth is not None:
        request_options["auth"] = auth
    if required:
        request_options["required"] = True
    result = client.get(feed_url, **request_options)
    if not result:
        return []
    entries = parse_feed(result.text)
    return entries if limit is None else entries[:limit]


def fetch_feedly_stream_entries(
    client: HttpClient,
    feed_url: str,
    limit: int | None = 100,
) -> list[FeedEntry]:
    """Read a public publisher feed through Feedly's unauthenticated reader API."""
    count = 100 if limit is None else max(1, min(int(limit), 1000))
    stream_id = f"feed/{feed_url}"
    request_url = (
        f"{FEEDLY_STREAM_API}?streamId={quote(stream_id, safe='')}&count={count}"
    )
    result = client.get(request_url)
    if not result:
        return []
    try:
        payload = json.loads(result.text)
    except json.JSONDecodeError:
        logging.warning("Feedly returned invalid JSON for %s", feed_url)
        return []
    if not isinstance(payload, dict) or not isinstance(payload.get("items"), list):
        logging.warning("Feedly returned an invalid stream for %s", feed_url)
        return []
    returned_stream_id = str(payload.get("id") or "")
    if returned_stream_id and returned_stream_id != stream_id:
        logging.warning("Feedly returned a different stream for %s", feed_url)
        return []

    expected_host = (urlparse(feed_url).hostname or "").lower()
    if expected_host.startswith("www."):
        expected_host = expected_host[4:]

    entries: list[FeedEntry] = []
    for item in payload["items"]:
        if not isinstance(item, dict):
            continue
        url = next(
            (
                str(alternate.get("href") or "").strip()
                for alternate in item.get("alternate") or []
                if isinstance(alternate, dict)
                and str(alternate.get("type") or "").lower() == "text/html"
                and alternate.get("href")
            ),
            "",
        )
        if not url:
            continue
        parsed_url = urlparse(url)
        article_host = (parsed_url.hostname or "").lower()
        if article_host.startswith("www."):
            article_host = article_host[4:]
        if (
            parsed_url.scheme not in {"http", "https"}
            or not expected_host
            or not (
                article_host == expected_host
                or article_host.endswith(f".{expected_host}")
            )
        ):
            logging.warning("Feedly item did not belong to %s: %s", feed_url, url)
            continue
        content_value = ""
        for key in ("content", "summary"):
            container = item.get(key)
            if isinstance(container, dict) and container.get("content"):
                content_value = str(container["content"])
                break
        summary = " ".join(
            BeautifulSoup(content_value, "html.parser").stripped_strings
        )
        timestamp = item.get("published") or item.get("updated")
        published_at = ""
        if isinstance(timestamp, (int, float)):
            published_at = datetime.fromtimestamp(timestamp / 1000, UTC).isoformat()
        entries.append(
            FeedEntry(
                title=str(item.get("title") or "").strip(),
                url=url,
                published_at=published_at,
                summary=summary,
                # Feedly mirrors the publisher's public payload. It must never
                # upgrade an excerpt to verified full text.
                content_is_full=False,
            )
        )
    return entries if limit is None else entries[:limit]
