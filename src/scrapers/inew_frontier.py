from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from ..date_utils import parse_published_datetime
from .generic import GenericListingScraper


class INEWFrontierScraper(GenericListingScraper):
    """Read article links scoped to the academic frontier news section."""

    def discover_article_urls(self, limit: int) -> list[str]:
        result = self.client.get(self.source.url)
        if not result:
            return []
        soup = BeautifulSoup(result.text, "html.parser")
        urls: list[str] = []
        titles: dict[str, str] = {}
        dates = {}
        for link in soup.select("a[href]"):
            url = urljoin(result.url, link.get("href", ""))
            parsed = urlparse(url)
            if (parsed.hostname != "mtl.inew.cn"
                    or not re.match(r"^/academic-news/.+", parsed.path)
                    or parsed.path.rstrip("/") == "/academic-news/frontier"
                    or url in titles):
                continue
            title = link.get_text(" ", strip=True) or link.get("title", "").strip()
            if len(title) < 6:
                continue
            urls.append(url)
            titles[url] = title
            nearby = link.parent.get_text(" ", strip=True) if link.parent else ""
            match = re.search(r"20\d{2}[-/.年]\d{1,2}[-/.月]\d{1,2}日?", nearby)
            if match:
                parsed_date = parse_published_datetime(match.group(0))
                if parsed_date:
                    dates[url] = parsed_date.date()
            if len(urls) >= limit:
                break
        self.listing_candidate_titles = titles
        self.listing_candidate_dates = dates
        return urls
