from __future__ import annotations

import re
from urllib.parse import urldefrag, urljoin, urlparse

from bs4 import BeautifulSoup

from .generic import GenericListingScraper


class RenewablesNowScraper(GenericListingScraper):
    """Only return Renewables Now article URLs, not sector/navigation pages."""

    article_path_re = re.compile(
        r"^/news/(?!archive/?$)[a-z0-9-]+-\d+/?$",
        re.I,
    )

    def discover_article_urls(self, limit: int) -> list[str]:
        result = self.client.get(self.source.url)
        if not result:
            return []

        soup = BeautifulSoup(result.text, "html.parser")
        source_host = urlparse(result.url).netloc
        urls: list[str] = []
        seen: set[str] = set()
        for link in soup.select("a[href]"):
            href = link.get("href")
            if not href:
                continue
            url = urldefrag(urljoin(result.url, href))[0]
            parsed = urlparse(url)
            if not self.same_site(parsed.netloc, source_host):
                continue
            if not self.article_path_re.match(parsed.path):
                continue
            if url not in seen:
                seen.add(url)
                urls.append(url)
                if len(urls) >= limit:
                    break
        return urls
