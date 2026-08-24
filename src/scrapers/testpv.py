from __future__ import annotations

from urllib.parse import parse_qs, urldefrag, urljoin, urlparse

from bs4 import BeautifulSoup

from ..date_utils import parse_published_datetime
from .generic import GenericListingScraper


class TestPVScraper(GenericListingScraper):
    """Discuz portal listing used by 光伏测试网."""

    link_selectors = ("a.xi2[href*='portal.php?mod=view']",)

    def discover_article_urls(self, limit: int) -> list[str]:
        result = self.client.get(self.source.url)
        if not result:
            self.listing_candidate_dates = {}
            return []

        soup = BeautifulSoup(result.text, "html.parser")
        urls: list[str] = []
        dates = {}
        seen: set[str] = set()
        for link in soup.select("a.xi2[href*='portal.php?mod=view']"):
            url = urldefrag(urljoin(result.url, str(link.get("href") or "")))[0]
            parsed = urlparse(url)
            if (
                url in seen
                or not parsed.path.endswith("/portal.php")
                or parse_qs(parsed.query).get("mod") != ["view"]
                or not parse_qs(parsed.query).get("aid")
            ):
                continue
            seen.add(url)
            urls.append(url)
            card = link.find_parent("dl")
            date_node = card.select_one("span.xg1") if card else None
            published = parse_published_datetime(
                date_node.get_text(" ", strip=True) if date_node else ""
            )
            dates[url] = published.date() if published else None
            if len(urls) >= limit:
                break
        self.listing_candidate_dates = dates
        return urls
