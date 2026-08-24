from __future__ import annotations

import re
from urllib.parse import urlparse

from ..date_utils import article_date
from ..rss_discovery import fetch_feed_entries
from .multi_page import MultiPageListingScraper


class InternationalEnergyScraper(MultiPageListingScraper):
    """国际能源网宏观新闻及国内、国际政策板块。"""

    official_feed_url = "https://in-en.com/feed/rss.php?mid=21"
    additional_listing_urls = (
        "https://in-en.com/article/news/",
        "https://in-en.com/article/policy/intl/",
        "https://in-en.com/article/policy/china/",
    )
    link_selectors = ("a[href*='/article/html/energy-']",)
    article_path_re = re.compile(r"^/article/html/energy-\d+\.shtml$", re.I)

    @staticmethod
    def public_url(url: str) -> str:
        parsed = urlparse(url)
        if parsed.netloc.lower() == "www.in-en.com":
            return parsed._replace(netloc="in-en.com").geturl()
        return url

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
        urls = super().discover_article_urls(limit * 2)
        return [
            self.public_url(url)
            for url in urls
            if self.article_path_re.match(urlparse(url).path)
        ][:limit]
