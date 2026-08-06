from __future__ import annotations

import re
from urllib.parse import urlparse

from .generic import GenericListingScraper


class EnergyTrendScraper(GenericListingScraper):
    """集邦新能源新闻页；排除 RSS 中的价格和研究栏目。"""

    link_selectors = (".entry-title a[href]",)
    article_path_re = re.compile(r"^/news/20\d{6}-\d+\.html$", re.I)

    @classmethod
    def accepts_rss_entry(cls, entry) -> bool:
        return bool(cls.article_path_re.match(urlparse(entry.url).path))

    def discover_article_urls(self, limit: int) -> list[str]:
        urls = super().discover_article_urls(limit * 2)
        return [url for url in urls if self.article_path_re.match(urlparse(url).path)][:limit]
