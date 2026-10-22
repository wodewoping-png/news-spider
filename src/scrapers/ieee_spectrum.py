from __future__ import annotations

from urllib.parse import urlparse

from bs4 import BeautifulSoup

from .generic import GenericListingScraper


class IEEESpectrumScraper(GenericListingScraper):
    """Use the official RSS; if unavailable, inspect news-page article cards."""

    @staticmethod
    def accepts_rss_entry(entry) -> bool:
        parsed = urlparse(entry.url)
        return parsed.scheme == "https" and parsed.hostname == "spectrum.ieee.org"

    def discover_article_urls(self, limit: int) -> list[str]:
        result = self.client.get(self.source.url)
        if not result:
            return []
        soup = BeautifulSoup(result.text, "html.parser")
        urls: list[str] = []
        titles: dict[str, str] = {}
        for link in soup.select('a[href]'):
            parsed = urlparse(link.get("href", ""))
            if parsed.scheme != "https" or parsed.hostname != "spectrum.ieee.org":
                continue
            if not parsed.path.strip("/") or len(parsed.path.strip("/").split("/")) != 1:
                continue
            title = link.get("aria-label") or link.get_text(" ", strip=True)
            if len(title) < 12 or parsed.path in {"/join", "/about"}:
                continue
            url = f"https://spectrum.ieee.org{parsed.path}"
            if url not in titles:
                titles[url] = title
                urls.append(url)
            if len(urls) >= limit:
                break
        self.listing_candidate_titles = titles
        return urls
