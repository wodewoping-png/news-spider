from __future__ import annotations

from urllib.parse import parse_qs, urlparse

from .generic import GenericListingScraper


class TestPVScraper(GenericListingScraper):
    """Discuz portal listing used by 光伏测试网."""

    link_selectors = ("a.xi2[href*='portal.php?mod=view']",)

    def discover_article_urls(self, limit: int) -> list[str]:
        urls = super().discover_article_urls(limit * 2)
        return [
            url
            for url in urls
            if urlparse(url).path.endswith("/portal.php")
            and parse_qs(urlparse(url).query).get("mod") == ["view"]
            and parse_qs(urlparse(url).query).get("aid")
        ][:limit]
