from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date
from urllib.parse import urldefrag, urljoin, urlparse

from bs4 import BeautifulSoup

from ..article_parser import fetch_and_parse_article
from ..date_utils import article_date, parse_published_datetime
from .base import BaseScraper


@dataclass(frozen=True)
class BatteriesNewsCard:
    url: str
    published_date: date | None


class BatteriesNewsScraper(BaseScraper):
    """Read only the homepage Latest module and its Load More pages."""

    max_pages = 20

    @staticmethod
    def _latest_module(soup: BeautifulSoup):
        heading = soup.find(
            lambda tag: tag.name in {"h1", "h2", "h3", "h4"}
            and "latest" in tag.get_text(" ", strip=True).lower()
        )
        if not heading:
            return None
        return heading.find_parent(
            class_=lambda value: value and "gridlove-module" in value
        )

    @classmethod
    def parse_listing(
        cls,
        html: str,
        page_url: str,
    ) -> tuple[list[BatteriesNewsCard], str]:
        soup = BeautifulSoup(html, "html.parser")
        module = cls._latest_module(soup)
        if module is None:
            return [], ""

        cards: list[BatteriesNewsCard] = []
        seen: set[str] = set()
        source_host = urlparse(page_url).netloc.lower().removeprefix("www.")
        for article in module.select("article.gridlove-post"):
            link = article.select_one("h2.entry-title a[href]")
            if not link:
                continue
            url = urldefrag(urljoin(page_url, str(link.get("href") or "")))[0]
            host = urlparse(url).netloc.lower().removeprefix("www.")
            if not url or host != source_host or url in seen:
                continue
            seen.add(url)
            date_node = article.select_one(".meta-date .updated")
            parsed = parse_published_datetime(
                date_node.get_text(" ", strip=True) if date_node else ""
            )
            cards.append(
                BatteriesNewsCard(
                    url=url,
                    published_date=parsed.date() if parsed else None,
                )
            )

        next_url = ""
        for link in soup.select("a[href]"):
            if link.get_text(" ", strip=True).lower() != "load more":
                continue
            candidate = urldefrag(urljoin(page_url, str(link.get("href") or "")))[0]
            if candidate and candidate != page_url:
                next_url = candidate
                break
        return cards, next_url

    def scrape(
        self,
        limit: int = 20,
        *,
        target_date: date | None = None,
        candidate_limit: int | None = None,
    ) -> list[dict]:
        effective_candidate_limit = candidate_limit or max(limit * 5, limit)
        articles: list[dict] = []
        seen_urls: set[str] = set()
        seen_pages: set[str] = set()
        page_url = self.source.url
        candidates_seen = 0
        fetched_count = 0
        date_filtered_count = 0
        undated_candidate_count = 0
        candidate_dates: list[date] = []

        for _ in range(self.max_pages):
            if not page_url or page_url in seen_pages or candidates_seen >= effective_candidate_limit:
                break
            seen_pages.add(page_url)
            result = self.client.get(page_url)
            if not result:
                break
            cards, next_url = self.parse_listing(result.text, result.url)
            if not cards:
                logging.warning("Batteries News Latest module unavailable: %s", result.url)
                break

            page_dates = [card.published_date for card in cards if card.published_date]
            for card in cards:
                if candidates_seen >= effective_candidate_limit or len(articles) >= limit:
                    break
                candidates_seen += 1
                if card.url in seen_urls:
                    continue
                seen_urls.add(card.url)
                if card.published_date:
                    candidate_dates.append(card.published_date)
                if target_date and card.published_date != target_date:
                    if card.published_date:
                        date_filtered_count += 1
                    else:
                        undated_candidate_count += 1
                    continue
                article = fetch_and_parse_article(self.client, card.url, self.source)
                fetched_count += 1
                if not article:
                    continue
                if card.published_date and not article.get("published_at"):
                    article["published_at"] = card.published_date.isoformat()
                if target_date and article_date(article) != target_date:
                    continue
                articles.append(article)

            if len(articles) >= limit or not next_url:
                break
            if target_date and page_dates and min(page_dates) < target_date:
                break
            page_url = next_url

        self.last_candidate_count = candidates_seen
        self.last_fetched_count = fetched_count
        self.last_date_filtered_count = date_filtered_count
        self.last_undated_candidate_count = undated_candidate_count
        self.last_candidate_date_min = (
            min(candidate_dates).isoformat() if candidate_dates else ""
        )
        self.last_candidate_date_max = (
            max(candidate_dates).isoformat() if candidate_dates else ""
        )
        return articles
