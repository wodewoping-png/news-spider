from __future__ import annotations

import re
from urllib.parse import urlparse

from .generic import GenericListingScraper


class InsideEVsScraper(GenericListingScraper):
    """Fallback for InsideEVs; normal collection uses the official News RSS."""

    link_selectors = (
        "article h3 a[href]",
        "article h2 a[href]",
        "a[href*='/news/']",
    )
    article_path_re = re.compile(r"^/news/\d+/[a-z0-9-]+/?$", re.I)

    def discover_article_urls(self, limit: int) -> list[str]:
        urls = super().discover_article_urls(limit * 2)
        return [url for url in urls if self.article_path_re.match(urlparse(url).path)][:limit]
