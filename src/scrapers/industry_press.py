"""Dated, bounded news listings for PES Wind and RecyclingInside."""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from ..date_utils import article_date
from .generic import GenericListingScraper


class DatedIndustryListingScraper(GenericListingScraper):
    handles_configured_feed = True
    max_listing_pages = 5
    precise_listing_dates = True

    def scrape(self, limit=20, *, target_date=None, candidate_limit=None):
        self._target_date = target_date
        self._listing_failure = ""
        articles = super().scrape(limit, target_date=target_date, candidate_limit=candidate_limit)
        if self._listing_failure:
            self.last_target_date_absent = False
            self.last_failed_fetch_count = max(1, self.last_failed_fetch_count)
            self.last_fetch_issues = self._listing_failure
        return articles

    def _url(self, raw: str, base: str, *, listing=False) -> str | None:
        parsed = urlparse(urljoin(base, raw))
        pattern = self.listing_path if listing else self.article_path
        if parsed.scheme != "https" or parsed.netloc != self.host or not pattern.fullmatch(parsed.path):
            return None
        return parsed._replace(query="", fragment="").geturl()

    def discover_article_urls(self, limit: int) -> list[str]:
        self.listing_candidate_dates = {}
        self.listing_candidate_titles = {}
        self._listing_failure = ""
        urls, seen_pages = [], set()
        page_url = self._url(self.source.url, self.source.url, listing=True)
        target = getattr(self, "_target_date", None)
        for _ in range(self.max_listing_pages):
            if not page_url or page_url in seen_pages or len(urls) >= limit:
                break
            seen_pages.add(page_url)
            result = self.client.get(page_url, allow_non_html=False)
            if not result:
                self._listing_failure = str(getattr(self.client, "last_failure_reason", "") or "listing fetch failed")
                break
            if not self._url(result.url, page_url, listing=True):
                self._listing_failure = "listing redirected outside configured column"
                break
            soup = BeautifulSoup(result.text, "html.parser")
            cards = soup.select(self.card_selector)
            if not cards:
                self._listing_failure = "news cards missing from listing"
                break
            page_dates = []
            for card in cards:
                title_node = card.select_one(self.title_selector)
                link = card.select_one(self.link_selector)
                if not title_node or not link:
                    continue
                url = self._url(str(link.get("href") or ""), result.url)
                title = title_node.get_text(" ", strip=True)
                if not url or not title:
                    continue
                published = self.card_date(card)
                if published:
                    page_dates.append(published)
                if url in self.listing_candidate_titles:
                    continue
                self.listing_candidate_titles[url] = title
                # Date-only publisher labels cannot safely prefilter a Beijing
                # calendar day. The detail's timestamp is authoritative for PES.
                self.listing_candidate_dates[url] = published if self.precise_listing_dates else None
                urls.append(url)
                if len(urls) >= limit:
                    break
            # Only stop on dates once every card on this page is dated and older.
            # This also avoids letting a single pinned old item stop recovery.
            margin = timedelta(days=0 if self.precise_listing_dates else 1)
            if target and len(page_dates) == len(cards) and max(page_dates) + margin < target:
                break
            next_link = soup.select_one(self.next_selector)
            page_url = self._url(str(next_link.get("href") or ""), result.url, listing=True) if next_link else None
        return urls[:limit]


class PESWindScraper(DatedIndustryListingScraper):
    precise_listing_dates = False
    host = "pes.eu.com"
    listing_path = re.compile(r"/press-releases/tag/wind(?:/page/[1-9]\d*)?/?")
    article_path = re.compile(r"/press-releases/(?!tag$|page$|rss\.xml$)[a-z0-9-]+/?")
    card_selector = "#hs_cos_wrapper_blog_listing_body article"
    link_selector = "a[href]"
    title_selector = "h3"
    next_selector = 'link[rel="next"][href], a[aria-label="Next"][href]'

    def card_date(self, card) -> date | None:
        stamp = card.select_one("p.p-small")
        match = re.search(r"\b(\d{1,2} [A-Za-z]+, 20\d{2})\b", stamp.get_text(" ", strip=True)) if stamp else None
        try:
            return datetime.strptime(match.group(1), "%d %B, %Y").date() if match else None
        except ValueError:
            return None


class RecyclingInsideScraper(DatedIndustryListingScraper):
    host = "recyclinginside.com"
    listing_path = re.compile(r"/recycling-waste-news(?:/page/[1-9]\d*)?/?")
    article_path = re.compile(r"/news/[a-z0-9-]+/")
    card_selector = "#latest article.gs-post-card"
    link_selector = ".gs-post-card__title a[href]"
    title_selector = ".gs-post-card__title"
    next_selector = "a.next.page-numbers[href]"

    def card_date(self, card) -> date | None:
        stamp = card.select_one("time[datetime]")
        return article_date({"published_at": str(stamp.get("datetime") or "")}) if stamp else None
