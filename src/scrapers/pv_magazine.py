from __future__ import annotations

import re
from urllib.parse import urldefrag, urljoin, urlparse

from bs4 import BeautifulSoup

from .generic import GenericListingScraper


class PVMagazineScraper(GenericListingScraper):
    link_selectors = (
        "a.post-block__title[href]",
        "article h3 a[href]",
        "article h2 a[href]",
        ".article-list a[href]",
        ".entry-title a[href]",
    )


class PVMagazineCIPVScraper(GenericListingScraper):
    """Read only the chronological article feed requested for this channel."""

    listing_url = "https://www.pv-magazine.com/latest-news/"
    max_listing_pages = 12
    article_path_re = re.compile(
        r"^/20\d{2}/\d{1,2}/\d{1,2}/[^/?#]+/?$",
        re.I,
    )

    def discover_article_urls(self, limit: int) -> list[str]:
        urls: list[str] = []
        seen_urls: set[str] = set()
        seen_pages: set[str] = set()
        page_url = self.listing_url
        pages_fetched = 0

        while (
            page_url
            and page_url not in seen_pages
            and pages_fetched < self.max_listing_pages
            and len(urls) < limit
        ):
            seen_pages.add(page_url)
            result = self.client.get(page_url)
            if not result:
                break
            pages_fetched += 1
            soup = BeautifulSoup(result.text, "html.parser")
            feed = soup.select_one(".pvmagazine-article-feed")
            if not feed:
                break

            # The empty __container is the user-specified start marker.
            # Chronological post cards live in its sibling __inner section.
            article_list = feed.select_one(".pvmagazine-article-feed__inner")
            if not article_list:
                break
            source_host = urlparse(result.url).netloc
            for link in article_list.select(
                ".post-block a.post-block__title[href]"
            ):
                href = link.get("href")
                if not href:
                    continue
                url = urldefrag(urljoin(result.url, href))[0]
                parsed = urlparse(url)
                if (
                    parsed.scheme not in {"http", "https"}
                    or not self.same_site(parsed.netloc, source_host)
                    or not self.article_path_re.match(parsed.path)
                    or url in seen_urls
                ):
                    continue
                seen_urls.add(url)
                urls.append(url)
                if len(urls) >= limit:
                    break

            next_link = feed.select_one(
                ".pv-pagination-pagination a.next.page-numbers[href]"
            )
            page_url = (
                urldefrag(urljoin(result.url, next_link.get("href")))[0]
                if next_link and next_link.get("href")
                else ""
            )

        self.last_listing_page_count = pages_fetched
        return urls
