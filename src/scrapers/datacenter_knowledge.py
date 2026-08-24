from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from urllib.parse import urldefrag, urljoin, urlparse

from bs4 import BeautifulSoup

from ..article_parser import fetch_and_parse_article, utc_now_iso
from ..content_quality import assess_content
from ..date_utils import article_date, parse_published_datetime
from ..rss_discovery import FeedEntry, fetch_feed_entries
from .base import BaseScraper


@dataclass(frozen=True)
class DataCenterKnowledgeCard:
    url: str
    published_date: date | None


class DataCenterKnowledgeScraper(BaseScraper):
    """Combine every news group on Latest News with detail-page full text."""

    handles_configured_feed = True
    max_pages = 20

    listing_groups = (
        (
            ".ListContent-Content_featured",
            "a.ArticlePreview-Title[href]",
            ".ArticlePreview-Date",
        ),
        (
            ".ListContent-Content_latest",
            "a.ContentCard-Title[href]",
            ".ContentCard-Date",
        ),
        (
            ".ListContent-ContentItem",
            "a.ListPreview-Title[href]",
            ".ListPreview-Date",
        ),
    )

    @staticmethod
    def _card_date(link, date_selector: str) -> date | None:
        preview = link.find_parent(
            class_=lambda value: value and "ContentPreview" in value
        )
        date_node = preview.select_one(date_selector) if preview else None
        parsed = parse_published_datetime(
            date_node.get_text(" ", strip=True) if date_node else ""
        )
        return parsed.date() if parsed else None

    @classmethod
    def parse_listing(
        cls,
        html: str,
        page_url: str,
    ) -> tuple[list[DataCenterKnowledgeCard], str]:
        soup = BeautifulSoup(html, "html.parser")
        root = soup.select_one(".ListContent")
        if root is None:
            return [], ""

        host = urlparse(page_url).netloc.lower().removeprefix("www.")
        cards: list[DataCenterKnowledgeCard] = []
        seen: set[str] = set()
        for group_selector, link_selector, date_selector in cls.listing_groups:
            for group in root.select(group_selector):
                for link in group.select(link_selector):
                    url = urldefrag(
                        urljoin(page_url, str(link.get("href") or ""))
                    )[0]
                    candidate_host = (
                        urlparse(url).netloc.lower().removeprefix("www.")
                    )
                    if not url or candidate_host != host or url in seen:
                        continue
                    seen.add(url)
                    cards.append(
                        DataCenterKnowledgeCard(
                            url=url,
                            published_date=cls._card_date(link, date_selector),
                        )
                    )

        next_link = root.select_one(
            'nav.ListContent-Pagination a[aria-label^="Go to Next page"][href]'
        )
        next_url = (
            urldefrag(
                urljoin(page_url, str(next_link.get("href") or ""))
            )[0]
            if next_link
            else ""
        )
        return cards, next_url

    def _feed_entries(self, candidate_limit: int) -> dict[str, FeedEntry]:
        feed_url = self.source.configured_rss_url or urljoin(
            self.source.url,
            "/rss.xml",
        )
        return {
            urldefrag(entry.url)[0].rstrip("/"): entry
            for entry in fetch_feed_entries(
                self.client,
                feed_url,
                max(candidate_limit, 100),
            )
        }

    def _article_from_card(
        self,
        card: DataCenterKnowledgeCard,
        entry: FeedEntry | None,
    ) -> dict | None:
        article = fetch_and_parse_article(self.client, card.url, self.source)
        if article:
            if entry and entry.title and not article.get("title"):
                article["title"] = entry.title
            if entry and entry.published_at:
                article["published_at"] = entry.published_at
            elif card.published_date and not article.get("published_at"):
                article["published_at"] = card.published_date.isoformat()
            return article

        if not entry or not entry.summary:
            return None
        content_status, content_issue = assess_content(
            entry.summary,
            extraction_method="rss_excerpt",
        )
        return {
            "title": entry.title,
            "published_at": entry.published_at
            or (card.published_date.isoformat() if card.published_date else ""),
            "content": entry.summary,
            "content_status": content_status,
            "content_issue": content_issue,
            "content_extraction": "rss_excerpt",
            "url": entry.url or card.url,
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
        effective_candidate_limit = candidate_limit or max(limit * 5, limit)
        feed_entries = self._feed_entries(effective_candidate_limit)
        articles: list[dict] = []
        seen_urls: set[str] = set()
        seen_pages: set[str] = set()
        page_url = self.source.url
        candidates_seen = 0
        fetched_count = 0
        candidate_dates: dict[str, date | None] = {}

        for _ in range(self.max_pages):
            if (
                not page_url
                or page_url in seen_pages
                or candidates_seen >= effective_candidate_limit
            ):
                break
            seen_pages.add(page_url)
            result = self.client.get(page_url)
            if not result:
                break
            cards, next_url = self.parse_listing(result.text, result.url)
            if not cards:
                break

            page_dates = [card.published_date for card in cards if card.published_date]
            for card in cards:
                if (
                    candidates_seen >= effective_candidate_limit
                    or len(articles) >= limit
                ):
                    break
                candidates_seen += 1
                key = card.url.rstrip("/")
                if key in seen_urls:
                    continue
                seen_urls.add(key)
                entry = feed_entries.get(key)
                feed_date = (
                    article_date(
                        {
                            "published_at": entry.published_at,
                            "url": entry.url,
                        }
                    )
                    if entry and entry.published_at
                    else None
                )
                evidence_date = feed_date or card.published_date
                if (
                    target_date
                    and not feed_date
                    and card.published_date == target_date - timedelta(days=1)
                ):
                    # A date-only listing can be one local day behind a precise feed time.
                    evidence_date = None
                candidate_dates[key] = evidence_date
                if target_date:
                    if feed_date and feed_date != target_date:
                        continue
                    if not feed_date and card.published_date not in {
                        target_date,
                        target_date - timedelta(days=1),
                    }:
                        continue

                article = self._article_from_card(card, entry)
                fetched_count += 1
                if not article:
                    continue
                parsed_date = article_date(article)
                if parsed_date:
                    candidate_dates[key] = parsed_date
                if target_date and parsed_date != target_date:
                    continue
                articles.append(article)

            if len(articles) >= limit or not next_url:
                break
            if (
                target_date
                and page_dates
                and max(page_dates) < target_date - timedelta(days=1)
            ):
                break
            page_url = next_url

        # The RSS can publish before /latest-news refreshes. Include those
        # feed-only URLs so the daily run does not miss the newest articles;
        # detail pages remain the preferred source for full text.
        for key, entry in feed_entries.items():
            if len(articles) >= limit:
                break
            if key in seen_urls:
                continue
            seen_urls.add(key)
            candidates_seen += 1
            feed_date = article_date(
                {
                    "published_at": entry.published_at,
                    "url": entry.url,
                }
            )
            candidate_dates[key] = feed_date
            if target_date:
                if feed_date != target_date:
                    continue
            article = self._article_from_card(
                DataCenterKnowledgeCard(url=entry.url, published_date=None),
                entry,
            )
            fetched_count += 1
            if not article:
                continue
            parsed_date = article_date(article)
            if parsed_date:
                candidate_dates[key] = parsed_date
            if target_date and parsed_date != target_date:
                continue
            articles.append(article)

        self.last_candidate_count = candidates_seen
        self.last_fetched_count = fetched_count
        known_dates = [value for value in candidate_dates.values() if value]
        self.last_date_filtered_count = sum(
            bool(target_date and value and value != target_date)
            for value in candidate_dates.values()
        )
        self.last_undated_candidate_count = sum(
            value is None for value in candidate_dates.values()
        )
        self.last_candidate_date_min = (
            min(known_dates).isoformat() if known_dates else ""
        )
        self.last_candidate_date_max = (
            max(known_dates).isoformat() if known_dates else ""
        )
        return articles
