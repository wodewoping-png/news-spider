from __future__ import annotations

import re
from datetime import date
from urllib.parse import urldefrag, urljoin, urlparse

from bs4 import BeautifulSoup

from .generic import GenericListingScraper


class CCEDIAScraper(GenericListingScraper):
    """Chinese Energy Industry Development Network's dated category listings."""

    max_listing_pages = 5
    article_path = re.compile(r"^/energy_detail/c-_detailId(?:%3[Dd]|=)\d+\.html$")

    def scrape(self, limit=20, *, target_date=None, candidate_limit=None):
        self._target_date = target_date
        self.listing_candidate_dates = {}
        self.listing_candidate_titles = {}
        return super().scrape(
            limit=limit, target_date=target_date, candidate_limit=candidate_limit
        )

    def discover_article_urls(self, limit: int) -> list[str]:
        if not hasattr(self, "listing_candidate_dates"):
            self.listing_candidate_dates = {}
            self.listing_candidate_titles = {}
        urls: list[str] = []
        seen_urls: set[str] = set()
        page_url = self.source.url
        seen_pages: set[str] = set()
        target_date = getattr(self, "_target_date", None)

        for _ in range(self.max_listing_pages):
            if page_url in seen_pages or len(urls) >= limit:
                break
            seen_pages.add(page_url)
            result = self.client.get(page_url)
            if not result:
                break
            soup = BeautifulSoup(result.text, "html.parser")
            listing = soup.select_one('div[id^="c_new_list_139-"]')
            if listing is None:
                break
            page_dates: list[date] = []
            for item in listing.select(".p_list .p_loopitem"):
                title_link = item.select_one(".s_title a[href]")
                date_node = item.select_one(".e_timeFormat-9")
                if not title_link or not date_node:
                    continue
                raw_date = date_node.get_text(" ", strip=True)[:10]
                try:
                    published = date.fromisoformat(raw_date)
                except ValueError:
                    continue
                url = urldefrag(urljoin(result.url, title_link["href"]))[0]
                parsed = urlparse(url)
                if (
                    not self.same_site(parsed.netloc, "ccedia.com")
                    or not self.article_path.fullmatch(parsed.path)
                    or url in seen_urls
                ):
                    continue
                seen_urls.add(url)
                urls.append(url)
                page_dates.append(published)
                self.listing_candidate_dates[url] = published
                self.listing_candidate_titles[url] = title_link.get_text(" ", strip=True)
                if len(urls) >= limit:
                    break
            # A pinned old article can appear before newer ones; only the tail
            # of the listing establishes that we've passed the target day.
            if not target_date or (page_dates and page_dates[-1] < target_date):
                break
            if page_dates and max(page_dates) < target_date:
                break
            next_link = listing.select_one(".p_page .page_next[href]:not(.disabled)")
            if not next_link:
                break
            page_url = urljoin(result.url, next_link["href"])
        return urls[:limit]
