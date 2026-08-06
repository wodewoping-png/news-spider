from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from urllib.parse import urldefrag, urljoin, urlparse

from bs4 import BeautifulSoup

from ..article_parser import fetch_and_parse_article, utc_now_iso
from ..date_utils import article_date, parse_published_datetime
from ..rss_discovery import FeedEntry, fetch_feed_entries
from .base import BaseScraper


@dataclass(frozen=True)
class InterestingEngineeringCard:
    url: str
    published_date: date | None


class InterestingEngineeringScraper(BaseScraper):
    """Combine the public news archive with the site's public full-text RSS."""

    handles_configured_feed = True
    max_pages = 20

    @staticmethod
    def _parse_section_date(section) -> date | None:
        for node in section.find_all("div", recursive=False):
            parsed = parse_published_datetime(node.get_text(" ", strip=True))
            if parsed:
                return parsed.date()
        return None

    @classmethod
    def parse_listing(
        cls,
        html: str,
        page_url: str,
    ) -> tuple[list[InterestingEngineeringCard], str]:
        soup = BeautifulSoup(html, "html.parser")
        page_host = urlparse(page_url).netloc.lower().removeprefix("www.")
        cards: list[InterestingEngineeringCard] = []
        seen: set[str] = set()

        news_heading = soup.find(
            lambda tag: tag.name == "h1"
            and tag.get_text(" ", strip=True).lower() == "news"
        )
        article_root = news_heading.find_parent("article") if news_heading else None
        if article_root:
            for section in article_root.find_all("section", recursive=False):
                section_date = cls._parse_section_date(section)
                if not section_date:
                    continue
                for heading in section.select("h3"):
                    link = heading.find("a", href=True)
                    if not link:
                        continue
                    url = urldefrag(urljoin(page_url, str(link.get("href") or "")))[0]
                    host = urlparse(url).netloc.lower().removeprefix("www.")
                    if not url or host != page_host or url in seen:
                        continue
                    if urlparse(url).path.startswith("/news/page/"):
                        continue
                    seen.add(url)
                    cards.append(
                        InterestingEngineeringCard(
                            url=url,
                            published_date=section_date,
                        )
                    )

        next_link = soup.select_one('a[aria-label="Go to next page"][href]')
        next_url = (
            urldefrag(urljoin(page_url, str(next_link.get("href") or "")))[0]
            if next_link
            else ""
        )
        return cards, next_url

    def _feed_entries(self, candidate_limit: int) -> dict[str, FeedEntry]:
        feed_url = self.source.configured_rss_url or urljoin(self.source.url, "/feed")
        return {
            urldefrag(entry.url)[0].rstrip("/"): entry
            for entry in fetch_feed_entries(self.client, feed_url, candidate_limit)
        }

    def _article_from_card(
        self,
        card: InterestingEngineeringCard,
        feed_entries: dict[str, FeedEntry],
    ) -> dict | None:
        entry = feed_entries.get(card.url.rstrip("/"))
        if entry and entry.summary:
            return {
                "title": entry.title,
                "published_at": entry.published_at or (
                    card.published_date.isoformat() if card.published_date else ""
                ),
                "content": entry.summary,
                "content_extraction": (
                    "rss_full_content" if entry.content_is_full else "rss_excerpt"
                ),
                "url": entry.url or card.url,
                "source_name": self.source.name,
                "domain": self.source.domain,
                "sub_domain": self.source.sub_domain,
                "crawled_at": utc_now_iso(),
            }

        article = fetch_and_parse_article(self.client, card.url, self.source)
        if article:
            # The public page may expose only the pre-subscription preview. Keep it,
            # but label it incomplete instead of attempting to bypass the wall.
            article["content_extraction"] = "public_preview"
        if article and card.published_date and not article.get("published_at"):
            article["published_at"] = card.published_date.isoformat()
        return article

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
                if candidates_seen >= effective_candidate_limit or len(articles) >= limit:
                    break
                candidates_seen += 1
                if card.url in seen_urls:
                    continue
                seen_urls.add(card.url)
                entry = feed_entries.get(card.url.rstrip("/"))
                if target_date:
                    if entry and entry.published_at:
                        published = parse_published_datetime(entry.published_at)
                        if not published or published.date() != target_date:
                            continue
                    elif card.published_date not in {
                        target_date,
                        target_date - timedelta(days=1),
                    }:
                        continue
                article = self._article_from_card(card, feed_entries)
                fetched_count += 1
                if not article:
                    continue
                if target_date and article_date(article) != target_date:
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

        self.last_candidate_count = candidates_seen
        self.last_fetched_count = fetched_count
        return articles
