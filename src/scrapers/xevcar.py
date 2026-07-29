from __future__ import annotations

import re
from urllib.parse import urlparse

from .generic import GenericListingScraper


class XEVCarScraper(GenericListingScraper):
    """我爱电车网首页新闻卡片。"""

    link_selectors = (
        ".entry-title a[href]",
        "a.topic-post-big[href]",
    )
    article_path_re = re.compile(r"^/[a-z0-9-]+/[a-z0-9]+\.html$", re.I)

    def discover_article_urls(self, limit: int) -> list[str]:
        urls = super().discover_article_urls(limit * 2)
        return [url for url in urls if self.article_path_re.match(urlparse(url).path)][:limit]
