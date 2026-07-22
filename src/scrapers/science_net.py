from __future__ import annotations

import re
from datetime import date
from urllib.parse import urldefrag, urljoin, urlparse

from bs4 import BeautifulSoup

from .generic import GenericListingScraper


class ScienceNetScraper(GenericListingScraper):
    """Handle ScienceNet's ASP.NET listings and .shtm article URLs."""

    article_path_re = re.compile(r"^/htmlnews/20\d{2}/\d{1,2}/\d+\.shtm$", re.I)
    browser_user_agent = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/138.0 Safari/537.36"
    )

    def scrape(
        self,
        limit: int = 20,
        *,
        target_date: date | None = None,
        candidate_limit: int | None = None,
    ) -> list[dict]:
        session = getattr(self.client, "session", None)
        if session is None:
            return super().scrape(
                limit,
                target_date=target_date,
                candidate_limit=candidate_limit,
            )
        previous_user_agent = session.headers.get("User-Agent")
        session.headers["User-Agent"] = self.browser_user_agent
        try:
            return super().scrape(
                limit,
                target_date=target_date,
                candidate_limit=candidate_limit,
            )
        finally:
            if previous_user_agent is None:
                session.headers.pop("User-Agent", None)
            else:
                session.headers["User-Agent"] = previous_user_agent

    def discover_article_urls(self, limit: int) -> list[str]:
        listing_urls = (
            self.source.url,
            urljoin(self.source.url, "/todaynews.aspx"),
            urljoin(self.source.url, "/"),
        )
        urls: list[str] = []
        seen: set[str] = set()
        for listing_url in listing_urls:
            result = self.client.get(listing_url)
            if not result:
                continue
            soup = BeautifulSoup(result.text, "html.parser")
            for link in soup.select("a[href*='/htmlnews/']"):
                href = link.get("href")
                if not href:
                    continue
                url = urldefrag(urljoin(result.url, href))[0]
                if not self.article_path_re.match(urlparse(url).path):
                    continue
                if url in seen:
                    continue
                seen.add(url)
                urls.append(url)
                if len(urls) >= limit:
                    return urls
        return urls
