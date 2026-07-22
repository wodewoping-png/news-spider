from __future__ import annotations

from dataclasses import replace
from datetime import date

from .generic import GenericListingScraper


class MultiPageListingScraper(GenericListingScraper):
    """Try source-specific listing fallbacks before the configured landing page."""

    additional_listing_urls: tuple[str, ...] = ()
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
        original_source = self.source
        urls: list[str] = []
        seen: set[str] = set()
        listing_urls = self.additional_listing_urls + (original_source.url,)
        try:
            for listing_url in listing_urls:
                self.source = replace(original_source, url=listing_url)
                for url in super().discover_article_urls(limit):
                    if url in seen:
                        continue
                    seen.add(url)
                    urls.append(url)
                    if len(urls) >= limit:
                        return urls
        finally:
            self.source = original_source
        return urls


class H2ViewScraper(MultiPageListingScraper):
    additional_listing_urls = (
        "https://www.gasworld.com/h2-view/latest-news/",
    )


class SolarInEnScraper(MultiPageListingScraper):
    additional_listing_urls = (
        "https://solar.in-en.com/news/SolarPV/",
    )


class ChinaNengyuanScraper(MultiPageListingScraper):
    additional_listing_urls = (
        "http://www.china-nengyuan.com/news/",
    )


class ChinaNengyuanTechScraper(MultiPageListingScraper):
    additional_listing_urls = (
        "http://www.china-nengyuan.com/tech/",
    )


class ChinaNengyuanWindScraper(MultiPageListingScraper):
    additional_listing_urls = (
        "http://wp.china-nengyuan.com/tech/",
    )


class PerovskiteInfoScraper(GenericListingScraper):
    link_selectors = (
        "article.node--type-story a[rel='bookmark'][href]",
        "article.node--type-story .field--name-title a[href]",
        "article.node--type-story a[href]",
    )
