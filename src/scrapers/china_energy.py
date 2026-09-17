from __future__ import annotations

import re
from datetime import date
from urllib.parse import urldefrag, urljoin
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from .multi_page import MultiPageListingScraper


class ChinaEnergyScraper(MultiPageListingScraper):
    """中国能源网首页需会话，改用无需登录的能源经济公开栏目。"""

    additional_listing_urls = (
        "https://www.china5e.com/",
        "https://www.china5e.com/power/power-gird/",
    )
    link_selectors = (
        ".list-item h2 a[href]",
        "a[href*='/news/news-']",
    )
    article_path_re = re.compile(r"^/news/news-\d+-\d+\.html$", re.I)
    periodical_index_url = "https://www.china5e.com/periodical/"

    def scrape(
        self,
        limit: int = 20,
        *,
        target_date: date | None = None,
        candidate_limit: int | None = None,
    ) -> list[dict]:
        self._target_date = target_date
        try:
            return super().scrape(
                limit,
                target_date=target_date,
                candidate_limit=candidate_limit,
            )
        finally:
            self._target_date = None

    def discover_article_urls(self, limit: int) -> list[str]:
        target_date = getattr(self, "_target_date", None)
        if target_date:
            index_result = self.client.get(self.periodical_index_url)
            if index_result:
                index_soup = BeautifulSoup(index_result.text, "html.parser")
                issue_url = ""
                for option in index_soup.select("option[value]"):
                    if target_date.isoformat() in option.get_text(" ", strip=True):
                        issue_url = urljoin(
                            index_result.url,
                            str(option.get("value") or ""),
                        )
                        break
                if issue_url:
                    issue_result = self.client.get(issue_url)
                    if issue_result:
                        issue_soup = BeautifulSoup(issue_result.text, "html.parser")
                        urls: list[str] = []
                        dates: dict[str, date] = {}
                        titles: dict[str, str] = {}
                        seen: set[str] = set()
                        for link in issue_soup.select("a[href*='/news/news-']"):
                            url = urldefrag(
                                urljoin(issue_result.url, str(link.get("href") or ""))
                            )[0]
                            if (
                                url in seen
                                or not self.article_path_re.match(urlparse(url).path)
                            ):
                                continue
                            seen.add(url)
                            urls.append(url)
                            dates[url] = target_date
                            title = link.get_text(" ", strip=True)
                            if title and title != "[详细内容]":
                                titles[url] = title
                            if len(urls) >= limit:
                                break
                        if urls:
                            self.listing_candidate_dates = dates
                            self.listing_candidate_titles = titles
                            return urls
        urls = super().discover_article_urls(limit * 2)
        return [url for url in urls if self.article_path_re.match(urlparse(url).path)][:limit]
