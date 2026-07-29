from __future__ import annotations

import re
from urllib.parse import urlparse

from .multi_page import MultiPageListingScraper


class InternationalEnergyScraper(MultiPageListingScraper):
    """国际能源网宏观新闻及国内、国际政策板块。"""

    additional_listing_urls = (
        "https://www.in-en.com/article/news/",
        "https://www.in-en.com/article/policy/intl/",
        "https://www.in-en.com/article/policy/china/",
    )
    link_selectors = ("a[href*='/article/html/energy-']",)
    article_path_re = re.compile(r"^/article/html/energy-\d+\.shtml$", re.I)

    def discover_article_urls(self, limit: int) -> list[str]:
        urls = super().discover_article_urls(limit * 2)
        return [url for url in urls if self.article_path_re.match(urlparse(url).path)][:limit]
