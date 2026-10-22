from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from .generic import GenericListingScraper


class CNPCRefiningNewsScraper(GenericListingScraper):
    """The CNPC refining/materials listing links to dated /system/ pages."""

    article_path = re.compile(r"^/system/20\d{2}/\d{1,2}/\d{1,2}/\d+\.shtml$", re.I)

    def discover_article_urls(self, limit: int) -> list[str]:
        result = self.client.get(self.source.url)
        if not result:
            return []

        soup = BeautifulSoup(result.text, "html.parser")
        urls: list[str] = []
        seen: set[str] = set()
        titles: dict[str, str] = {}
        for link in soup.select("a[href]"):
            url = urljoin(result.url, link.get("href", ""))
            parsed = urlparse(url)
            if parsed.hostname != "news.cnpc.com.cn" or not self.article_path.fullmatch(parsed.path):
                continue
            # The listing uses HTTP links while its HTTPS article pages work.
            url = f"https://news.cnpc.com.cn{parsed.path}"
            if url in seen:
                continue
            seen.add(url)
            urls.append(url)
            titles[url] = link.get_text(" ", strip=True)
            if len(urls) >= limit:
                break
        self.listing_candidate_titles = titles
        return urls
