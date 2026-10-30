from __future__ import annotations

import re
from datetime import date
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from ..date_utils import date_from_url
from .generic import GenericListingScraper


class NCSTIArtificialIntelligenceScraper(GenericListingScraper):
    """北京国际科技创新中心的人工智能科技热点栏目。"""

    article_path = re.compile(
        r"^/kjdt/kjrd/rgzn_kjrd/20\d{4}/t20\d{6}_\d+\.html$"
    )

    def scrape(self, limit: int = 20, *, target_date: date | None = None,
               candidate_limit: int | None = None) -> list[dict]:
        self._requested_target_date = target_date
        return super().scrape(limit, target_date=target_date, candidate_limit=candidate_limit)

    def discover_article_urls(self, limit: int) -> list[str]:
        urls: list[str] = []
        titles: dict[str, str] = {}
        seen: set[str] = set()
        target_date = getattr(self, "_requested_target_date", None)
        # The site's pager is static (index_1.html, index_2.html, ...).
        # A few pages cover bursts of daily posts without traversing the archive.
        for page in range(3):
            listing_url = urljoin(self.source.url, "index.html" if page == 0 else f"index_{page}.html")
            result = self.client.get(listing_url)
            if not result:
                break
            soup = BeautifulSoup(result.text, "html.parser")
            page_dates: list[date] = []
            found = 0
            for link in soup.select("a[href]"):
                url = urljoin(result.url, link.get("href", ""))
                parsed = urlparse(url)
                if parsed.hostname != "www.ncsti.gov.cn" or not self.article_path.fullmatch(parsed.path):
                    continue
                published = date_from_url(url)
                if published:
                    page_dates.append(published)
                if url in seen:
                    continue
                seen.add(url)
                found += 1
                urls.append(url)
                heading = link.select_one("h2")
                if heading:
                    time = heading.select_one(".i-time")
                    if time:
                        time.decompose()
                    titles[url] = heading.get_text(" ", strip=True)
                if len(urls) >= limit:
                    break
            if not found or len(urls) >= limit or (target_date and page_dates and min(page_dates) < target_date):
                break
        self.listing_candidate_titles = titles
        return urls
