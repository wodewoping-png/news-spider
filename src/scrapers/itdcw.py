from __future__ import annotations

import re
from urllib.parse import urlparse

from .multi_page import MultiPageListingScraper


class ITDCWScraper(MultiPageListingScraper):
    """电池网国内、国际和企业新闻列表。"""

    additional_listing_urls = (
        "https://www.itdcw.com/news/guonei/",
        "https://www.itdcw.com/news/guoji/",
        "https://www.itdcw.com/news/qiye/",
    )
    link_selectors = (".list-item .item-top h2 a[href]",)
    article_path_re = re.compile(r"^/news/[a-z0-9-]+/[a-z0-9]+\.html$", re.I)

    def discover_article_urls(self, limit: int) -> list[str]:
        urls = super().discover_article_urls(limit * 2)
        return [url for url in urls if self.article_path_re.match(urlparse(url).path)][:limit]
