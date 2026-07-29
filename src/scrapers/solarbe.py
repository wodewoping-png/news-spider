from __future__ import annotations

import re
from urllib.parse import urlparse

from .generic import GenericListingScraper


class SolarbeScraper(GenericListingScraper):
    """索比光伏要闻页，只保留带日期目录的新闻详情链接。"""

    link_selectors = (
        ".recommend-content-right a.title2[href]",
        ".Select-recommend-item a[href]",
    )
    article_path_re = re.compile(r"^/20\d{4}/\d{1,2}/\d+\.html$", re.I)

    def discover_article_urls(self, limit: int) -> list[str]:
        urls = super().discover_article_urls(limit * 2)
        return [url for url in urls if self.article_path_re.match(urlparse(url).path)][:limit]
