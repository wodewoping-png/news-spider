from __future__ import annotations

import logging
from datetime import date
from typing import ClassVar
from urllib.parse import urlencode

from candidate_sources.government_announcements.base import ContractViolation, ListingItem
from candidate_sources.government_announcements.scrapers import (
    GovernmentDocumentScraper as GovernmentDocumentParser,
    MemNoticesScraper as MemNoticesParser,
    MiitPublicNoticesScraper as MiitPublicNoticesParser,
    MnrNoticesScraper as MnrNoticesParser,
    MofcomPolicyReleasesScraper as MofcomPolicyReleasesParser,
    MostNoticesScraper as MostNoticesParser,
    MotPolicyDocumentsScraper as MotPolicyDocumentsParser,
    NeaAnnouncementsScraper as NeaAnnouncementsParser,
    NeaDocumentScraper,
    NeaNoticesScraper as NeaNoticesParser,
    NdaPolicyReleasesScraper as NdaPolicyReleasesParser,
    SamrAntitrustNoticesScraper as SamrAntitrustNoticesParser,
    StaticMinistryScraper,
)

from ..article_parser import utc_now_iso
from .base import BaseScraper


class GovernmentAnnouncementScraper(BaseScraper):
    """Production adapter for the reviewed, fail-closed ministry parsers."""

    handles_configured_feed = True
    parser_type: ClassVar[type[GovernmentDocumentParser]]

    def _listing_items(self, parser: GovernmentDocumentParser) -> list[ListingItem]:
        if isinstance(parser, NeaDocumentScraper):
            result = self.client.get(parser.data_url, strict_robots=True)
            if not result:
                return []
            return parser.parse_listing_json(result.text, result.url)
        if isinstance(parser, MiitPublicNoticesParser):
            query = urlencode(parser.query_params)
            result = self.client.get(f"{parser.data_url}?{query}", strict_robots=True)
            if not result:
                return []
            return parser.parse_api_response(result.text, result.url.split("?", 1)[0])
        if isinstance(parser, StaticMinistryScraper):
            result = self.client.get(
                parser.listing_url,
                allow_non_html=False,
                strict_robots=True,
            )
            if not result:
                return []
            return parser.parse_listing(result.text, result.url)
        raise TypeError(f"unsupported government parser: {type(parser).__name__}")

    def _metadata_article(self, item: ListingItem) -> dict:
        return {
            "title": item.title,
            "published_at": item.platform_published_at.isoformat() if item.platform_published_at else "",
            "content": "",
            "content_extraction": "metadata_only",
            "content_policy": "metadata_only",
            "url": item.url,
            "source_name": self.source.name,
            "domain": self.source.domain,
            "sub_domain": self.source.sub_domain,
            "crawled_at": utc_now_iso(),
        }

    def _full_text_article(
        self,
        parser: GovernmentDocumentParser,
        item: ListingItem,
    ) -> dict | None:
        result = self.client.get(
            item.url,
            allow_non_html=False,
            strict_robots=True,
        )
        self.last_fetched_count += 1
        if not result:
            return None
        try:
            article = parser.parse_detail(result.text, result.url)
        except ContractViolation as exc:
            logging.warning("Government document contract rejected %s: %s", item.url, exc)
            return None
        return {
            "title": article.title,
            "published_at": (
                item.platform_published_at or article.platform_published_at
            ).isoformat(),
            "content": article.content,
            "content_extraction": "government_document_text",
            "url": article.platform_url,
            "source_name": self.source.name,
            "domain": self.source.domain,
            "sub_domain": self.source.sub_domain,
            "crawled_at": utc_now_iso(),
        }

    def scrape(
        self,
        limit: int = 20,
        *,
        target_date: date | None = None,
        candidate_limit: int | None = None,
    ) -> list[dict]:
        parser = self.parser_type()
        self.last_fetched_count = 0
        try:
            items = self._listing_items(parser)
        except ContractViolation as exc:
            logging.warning("Government listing contract rejected for %s: %s", self.source.name, exc)
            items = []

        effective_candidate_limit = candidate_limit or max(limit * 5, limit)
        items = items[:effective_candidate_limit]
        self.last_candidate_count = len(items)
        dates = [item.platform_published_at for item in items if item.platform_published_at]
        self.last_date_filtered_count = sum(
            bool(target_date and item.platform_published_at and item.platform_published_at != target_date)
            for item in items
        )
        self.last_undated_candidate_count = sum(item.platform_published_at is None for item in items)
        self.last_candidate_date_min = min(dates).isoformat() if dates else ""
        self.last_candidate_date_max = max(dates).isoformat() if dates else ""
        selected = [
            item for item in items
            if target_date is None or item.platform_published_at == target_date
        ]
        self.last_target_date_absent = bool(
            target_date and items and not selected and self.last_undated_candidate_count == 0
        )

        articles: list[dict] = []
        for item in selected:
            if len(articles) >= limit:
                break
            if parser.fetch_detail:
                article = self._full_text_article(parser, item)
                if article:
                    articles.append(article)
            else:
                articles.append(self._metadata_article(item))
        return articles


class NeaNoticesScraper(GovernmentAnnouncementScraper):
    parser_type = NeaNoticesParser


class NeaAnnouncementsScraper(GovernmentAnnouncementScraper):
    parser_type = NeaAnnouncementsParser


class MiitPublicNoticesScraper(GovernmentAnnouncementScraper):
    parser_type = MiitPublicNoticesParser


class MostNoticesScraper(GovernmentAnnouncementScraper):
    parser_type = MostNoticesParser


class MnrNoticesScraper(GovernmentAnnouncementScraper):
    parser_type = MnrNoticesParser


class MotPolicyDocumentsScraper(GovernmentAnnouncementScraper):
    parser_type = MotPolicyDocumentsParser


class MofcomPolicyReleasesScraper(GovernmentAnnouncementScraper):
    parser_type = MofcomPolicyReleasesParser


class MemNoticesScraper(GovernmentAnnouncementScraper):
    parser_type = MemNoticesParser


class NdaPolicyReleasesScraper(GovernmentAnnouncementScraper):
    parser_type = NdaPolicyReleasesParser


class SamrAntitrustNoticesScraper(GovernmentAnnouncementScraper):
    parser_type = SamrAntitrustNoticesParser
