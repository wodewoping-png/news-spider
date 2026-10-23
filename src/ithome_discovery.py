from __future__ import annotations

from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from .http_client import HttpClient
from .rss_discovery import FeedEntry


DISCOVERY_URL = "https://discovery.ithome.com/"


def parse_discovery_entries(html: str, *, limit: int) -> list[FeedEntry]:
    """Read the science channel's dated news cards, excluding navigation and tags."""
    soup = BeautifulSoup(html, "html.parser")
    entries: list[FeedEntry] = []
    seen: set[str] = set()
    for card in soup.select("#list ul.bl > li"):
        content = card.select_one(".c[data-ot]")
        link = card.select_one("a.title[href]")
        if content is None or link is None:
            continue
        url = urljoin(DISCOVERY_URL, link.get("href", ""))
        parsed = urlparse(url)
        if (parsed.scheme != "https" or parsed.hostname != "www.ithome.com"
                or not parsed.path.endswith(".htm") or url in seen):
            continue
        title = link.get_text(" ", strip=True)
        published_at = str(content.get("data-ot") or "").strip()
        if not title or not published_at:
            continue
        seen.add(url)
        excerpt = card.select_one(".m")
        entries.append(FeedEntry(
            title=title,
            url=url,
            published_at=published_at,
            summary=excerpt.get_text(" ", strip=True) if excerpt else "",
        ))
        if len(entries) >= limit:
            break
    return entries


def fetch_discovery_entries(client: HttpClient, limit: int) -> list[FeedEntry]:
    result = client.get(DISCOVERY_URL, strict_robots=True)
    return parse_discovery_entries(result.text, limit=limit) if result else []
