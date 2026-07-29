from __future__ import annotations

import logging
import re
from urllib.parse import urlparse

from .generic import GenericListingScraper


class XMolScraper(GenericListingScraper):
    """X-MOL 化学资讯；公开入口目前要求登录。"""

    link_selectors = (
        ".news-list a[href]",
        "a[href*='/news/']",
    )
    article_path_re = re.compile(r"^/news/\d+/?$", re.I)

    def discover_article_urls(self, limit: int) -> list[str]:
        result = self.client.get(self.source.url)
        if not result:
            return []
        if urlparse(result.url).path.startswith("/login"):
            logging.warning(
                "X-MOL public listing redirected to login; credentials are not configured."
            )
            return []
        urls = super().discover_article_urls(limit * 2)
        return [url for url in urls if self.article_path_re.match(urlparse(url).path)][:limit]
