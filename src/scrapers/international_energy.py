from __future__ import annotations

import re
from datetime import date, timedelta
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from ..date_utils import article_date, local_today, parse_published_datetime
from ..rss_discovery import fetch_feed_entries
from .multi_page import MultiPageListingScraper


class InternationalEnergyScraper(MultiPageListingScraper):
    """国际能源网宏观新闻及国内、国际政策板块。"""

    official_feed_url = "https://in-en.com/feed/rss.php?mid=21"
    official_mobile_listing_url = "https://m.in-en.com/article/"
    additional_listing_urls = (
        "https://in-en.com/article/news/",
        "https://in-en.com/article/policy/intl/",
        "https://in-en.com/article/policy/china/",
    )
    link_selectors = ("a[href*='/article/html/energy-']",)
    article_path_re = re.compile(r"^/article/html/energy-\d+\.shtml$", re.I)
    relative_days_re = re.compile(r"^(\d+)\s*天前$")

    @staticmethod
    def public_url(url: str) -> str:
        parsed = urlparse(url)
        if parsed.netloc.lower() == "www.in-en.com":
            return parsed._replace(netloc="in-en.com").geturl()
        return url

    @classmethod
    def mobile_listing_date(
        cls,
        value: str,
        *,
        today: date | None = None,
    ) -> date | None:
        value = (value or "").strip()
        reference_date = today or local_today()
        if value in {"刚刚", "今天"} or value.endswith(("分钟前", "小时前")):
            return reference_date
        if value == "昨天":
            return reference_date - timedelta(days=1)
        relative_match = cls.relative_days_re.match(value)
        if relative_match:
            return reference_date - timedelta(days=int(relative_match.group(1)))
        parsed = parse_published_datetime(value)
        return parsed.date() if parsed else None

    def discover_mobile_article_urls(self, limit: int) -> list[str]:
        result = self.client.get(self.official_mobile_listing_url)
        if not result:
            return []

        soup = BeautifulSoup(result.text, "html.parser")
        urls: list[str] = []
        dates: dict[str, date | None] = {}
        seen: set[str] = set()
        for item in soup.select(".item"):
            link = item.select_one("a[href*='/article/html/energy-']")
            if not link or not link.get("href"):
                continue
            url = urljoin(result.url, link["href"])
            if not self.article_path_re.match(urlparse(url).path) or url in seen:
                continue
            seen.add(url)
            urls.append(url)
            time_node = item.select_one(".time")
            dates[url] = self.mobile_listing_date(
                time_node.get_text(" ", strip=True) if time_node else ""
            )
            if len(urls) >= limit:
                break
        if urls:
            self.listing_candidate_dates = dates
        return urls

    def discover_article_urls(self, limit: int) -> list[str]:
        entries = list(fetch_feed_entries(self.client, self.official_feed_url, limit))
        if entries:
            urls: list[str] = []
            dates = {}
            for entry in entries:
                url = self.public_url(entry.url)
                if not self.article_path_re.match(urlparse(url).path):
                    continue
                urls.append(url)
                dates[url] = article_date(
                    {"published_at": entry.published_at, "url": url}
                )
            if urls:
                self.listing_candidate_dates = dates
                return urls[:limit]

        self.listing_candidate_dates = {}
        mobile_urls = self.discover_mobile_article_urls(limit)
        if mobile_urls:
            return mobile_urls

        urls = super().discover_article_urls(limit * 2)
        return [
            self.public_url(url)
            for url in urls
            if self.article_path_re.match(urlparse(url).path)
        ][:limit]
