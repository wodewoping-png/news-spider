from __future__ import annotations

import logging
import re
from datetime import date
from urllib.parse import urldefrag, urljoin, urlparse

from bs4 import BeautifulSoup

from ..article_parser import fetch_and_parse_article
from ..date_utils import article_date, date_from_url, ensure_published_at
from .base import BaseScraper


class GenericListingScraper(BaseScraper):
    """Conservative fallback scraper for simple news listing pages."""

    consecutive_older_limit = 10

    link_selectors = (
        ".recommend-content-right a[href]",
        ".recommend-content a[href]",
        ".news-list a[href]",
        ".newslist a[href]",
        ".list a[href]",
        ".list_news a[href]",
        ".list-con a[href]",
        ".listCon a[href]",
        ".channel-list a[href]",
        ".sub-list a[href]",
        ".main-list a[href]",
        "article a[href]",
        ".post a[href]",
        ".entry-title a[href]",
        "h1 a[href]",
        "h2 a[href]",
        "h3 a[href]",
        "ul li a[href]",
        "main a[href]",
        "a[href]",
    )

    article_url_patterns = (
        re.compile(r"/20\d{2}(?:\d{2})?/\d{1,2}/[^/]+\.s?html?$"),
        re.compile(r"/20\d{4}/[^/]+\.s?html?$"),
        re.compile(r"/20\d{6}/[a-z0-9-]+/c\.html?$", re.I),
        re.compile(r"/20\d{2}/\d{1,2}/\d{1,2}/\d+/[^/?#]+/?$", re.I),
        re.compile(r"/story/[^/?#]+/\d+\.article/?$", re.I),
        re.compile(r"/html/[^/?#]+\.s?html?$", re.I),
        re.compile(r"/tech/\d+\.s?html?$", re.I),
        re.compile(r"/news/article/[a-z0-9]+\.s?html?$", re.I),
        re.compile(r"/\d{6}/\d+\.s?html?$"),
        re.compile(r"/t20\d{6}_\d+\.s?html?$"),
        re.compile(r"/article/\d+\.s?html?$"),
        re.compile(r"/news/(?!news_list_)[^/?#]+\.s?html?$", re.I),
    )

    embedded_article_url_re = re.compile(
        r"(?:(?:https?:)?//[^\"'<> ]+)?"
        r"/20\d{2}/\d{1,2}/\d{1,2}/\d+/[a-z0-9-]+(?:/amp)?/?",
        re.I,
    )

    def discover_article_urls(self, limit: int) -> list[str]:
        result = self.client.get(self.source.url)
        if not result:
            return []

        soup = BeautifulSoup(result.text, "html.parser")
        source_host = urlparse(result.url).netloc
        source_page = result.url.rstrip("/")
        strong_urls: list[str] = []
        weak_urls: list[str] = []
        seen = set()
        for selector in self.link_selectors:
            for link in soup.select(selector):
                href = link.get("href")
                title = link.get_text(" ", strip=True)
                if not href or href.startswith(("javascript:", "#", "mailto:")):
                    continue
                url = urldefrag(urljoin(result.url, href))[0]
                parsed = urlparse(url)
                if parsed.scheme not in ("http", "https") or not self.same_site(parsed.netloc, source_host):
                    continue
                if url.rstrip("/") == source_page:
                    continue
                looks_like_article = self.looks_like_article_url(parsed.path)
                if not looks_like_article and len(title) < 8:
                    continue
                if url not in seen:
                    seen.add(url)
                    (strong_urls if looks_like_article else weak_urls).append(url)

        decoded_html = result.text.replace("\\/", "/")
        for match in self.embedded_article_url_re.finditer(decoded_html):
            url = urldefrag(urljoin(result.url, match.group(0)))[0]
            parsed = urlparse(url)
            if not self.same_site(parsed.netloc, source_host) or url in seen:
                continue
            seen.add(url)
            strong_urls.append(url)
        return (strong_urls + weak_urls)[:limit]

    @staticmethod
    def same_site(candidate_host: str, source_host: str) -> bool:
        def site_key(host: str) -> str:
            value = host.split(":", 1)[0].lower().rstrip(".")
            if value.startswith("www."):
                value = value[4:]
            labels = value.split(".")
            compound_suffixes = {"com.cn", "net.cn", "org.cn", "co.uk", "com.au"}
            if len(labels) >= 3 and ".".join(labels[-2:]) in compound_suffixes:
                return ".".join(labels[-3:])
            return ".".join(labels[-2:]) if len(labels) >= 2 else value

        return site_key(candidate_host) == site_key(source_host)

    def looks_like_article_url(self, path: str) -> bool:
        return any(pattern.search(path) for pattern in self.article_url_patterns)

    def scrape(
        self,
        limit: int = 20,
        *,
        target_date: date | None = None,
        candidate_limit: int | None = None,
    ) -> list[dict]:
        articles: list[dict] = []
        effective_candidate_limit = candidate_limit or max(limit * 5, limit)
        urls = self.discover_article_urls(effective_candidate_limit)
        self.last_candidate_count = len(urls)
        if not urls:
            logging.warning(
                "TODO scraper needed for %s: unable to identify article links from listing page. "
                "Please provide article-list CSS selectors or API details.",
                self.source.name,
            )
            return articles

        consecutive_older = 0
        consecutive_failed = 0
        fetched_count = 0
        for url in urls:
            url_date = date_from_url(url)
            if target_date and url_date and url_date != target_date:
                continue
            article = fetch_and_parse_article(self.client, url, self.source)
            fetched_count += 1
            if not article:
                consecutive_failed += 1
                if consecutive_failed >= self.consecutive_older_limit:
                    break
                continue
            consecutive_failed = 0
            if article:
                ensure_published_at(article)
                if target_date:
                    parsed_date = article_date(article)
                    if parsed_date and parsed_date < target_date:
                        consecutive_older += 1
                        if consecutive_older >= self.consecutive_older_limit:
                            break
                        continue
                    if parsed_date != target_date:
                        consecutive_older = 0
                        continue
                    consecutive_older = 0
                articles.append(article)
            if len(articles) >= limit:
                break
        self.last_fetched_count = fetched_count
        return articles
