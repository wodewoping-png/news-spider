from __future__ import annotations

import re
from urllib.parse import urlparse

from .multi_page import MultiPageListingScraper


class ChinaEnergyScraper(MultiPageListingScraper):
    """中国能源网首页需会话，改用无需登录的能源经济公开栏目。"""

    additional_listing_urls = ("https://www.china5e.com/news/energy-economy/",)
    link_selectors = (
        ".list-item h2 a[href]",
        "a[href*='/news/news-']",
    )
    article_path_re = re.compile(r"^/news/news-\d+-\d+\.html$", re.I)

    def discover_article_urls(self, limit: int) -> list[str]:
        urls = super().discover_article_urls(limit * 2)
        return [url for url in urls if self.article_path_re.match(urlparse(url).path)][:limit]
