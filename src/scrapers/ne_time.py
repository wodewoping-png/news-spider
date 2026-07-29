from __future__ import annotations

import re
from urllib.parse import urlparse

from .generic import GenericListingScraper


class NETimeScraper(GenericListingScraper):
    """NE时代服务端渲染的“全部”文章列表。"""

    link_selectors = ("a.article-item[href]",)
    article_path_re = re.compile(r"^/web/article/\d+/?$", re.I)

    def discover_article_urls(self, limit: int) -> list[str]:
        urls = super().discover_article_urls(limit * 2)
        return [url for url in urls if self.article_path_re.match(urlparse(url).path)][:limit]
