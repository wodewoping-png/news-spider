from __future__ import annotations

import re
from urllib.parse import urlparse

from .multi_page import MultiPageListingScraper


class BJXStorageScraper(MultiPageListingScraper):
    """北极星储能网要闻、独家和市场三个指定板块。"""

    additional_listing_urls = (
        "https://chuneng.bjx.com.cn/yw/",
        "https://chuneng.bjx.com.cn/dj/",
        "https://chuneng.bjx.com.cn/sc/",
    )
    link_selectors = ("a[href*='news.bjx.com.cn/html/']",)
    article_path_re = re.compile(r"^/html/20\d{6}/\d+\.shtml$", re.I)

    def discover_article_urls(self, limit: int) -> list[str]:
        urls = super().discover_article_urls(limit * 2)
        return [url for url in urls if self.article_path_re.match(urlparse(url).path)][:limit]
