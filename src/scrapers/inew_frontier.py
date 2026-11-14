from __future__ import annotations

import re
import json
from html import escape
from ..article_parser import parse_article_html
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from ..date_utils import parse_published_datetime
from .generic import GenericListingScraper


class INEWFrontierScraper(GenericListingScraper):
    """Read article links scoped to the academic frontier news section."""

    handles_configured_feed = True
    api_root = "https://mtl.inew.cn/prod-api/public/academic/content"

    def scrape(self, limit=20, *, target_date=None, candidate_limit=None):
        self.last_failed_fetch_count = 0
        self.last_fetch_issues = ""
        self.last_fetched_count = 0
        self.last_candidate_count = 0
        result = self.client.get(self.api_root + "/list?pageNum=1&pageSize=200&lang=zh")
        if not result:
            self.last_failed_fetch_count = 1
            self.last_fetch_issues = getattr(self.client, "last_failure_reason", "") or "public API unavailable"
            return []
        payload = json.loads(result.text)
        if payload.get("code") != 200 or not isinstance(payload.get("rows"), list):
            raise ValueError("INEW public listing returned an invalid response")
        rows = [r for r in payload["rows"] if r.get("columnCode") == "FRONTIER"]
        self.last_candidate_count = len(rows)
        dated = [(r, parse_published_datetime(r.get("publishTime", ""))) for r in rows]
        dates = [d.date() for _, d in dated if d]
        self.last_candidate_date_min = min(dates).isoformat() if dates else ""
        self.last_candidate_date_max = max(dates).isoformat() if dates else ""
        self.last_undated_candidate_count = sum(d is None for _, d in dated)
        self.last_date_filtered_count = sum(bool(target_date and d and d.date() != target_date) for _, d in dated)
        self.last_target_date_absent = bool(dates and target_date not in dates and not self.last_undated_candidate_count)
        articles = []
        for row, published in dated:
            if target_date and (not published or published.date() != target_date):
                continue
            content_id = str(row.get("contentId", ""))
            if not content_id.isdigit():
                continue
            detail = self.client.get(self.api_root + "/" + content_id + "?lang=zh")
            self.last_fetched_count += 1
            if not detail:
                self.last_failed_fetch_count += 1
                self.last_fetch_issues = getattr(self.client, "last_failure_reason", "") or "public detail unavailable"
                continue
            data = json.loads(detail.text).get("data", {}).get("content", {})
            if str(data.get("contentId")) != content_id or not data.get("contentHtml"):
                self.last_failed_fetch_count += 1
                self.last_fetch_issues = "public detail missing body or mismatched ID"
                continue
            html = '<h1>' + escape(data.get("title", "")) + '</h1><article>' + data["contentHtml"] + '</article>'
            article = parse_article_html(html, "https://mtl.inew.cn/academic-news/detail/" + content_id, self.source)
            article["published_at"] = row.get("publishTime", "")
            articles.append(article)
            if len(articles) >= limit:
                break
        return articles

    def discover_article_urls(self, limit: int) -> list[str]:
        result = self.client.get(self.source.url)
        if not result:
            return []
        soup = BeautifulSoup(result.text, "html.parser")
        urls: list[str] = []
        titles: dict[str, str] = {}
        dates = {}
        for link in soup.select("a[href]"):
            url = urljoin(result.url, link.get("href", ""))
            parsed = urlparse(url)
            if (parsed.hostname != "mtl.inew.cn"
                    or not re.match(r"^/academic-news/.+", parsed.path)
                    or parsed.path.rstrip("/") == "/academic-news/frontier"
                    or url in titles):
                continue
            title = link.get_text(" ", strip=True) or link.get("title", "").strip()
            if len(title) < 6:
                continue
            urls.append(url)
            titles[url] = title
            nearby = link.parent.get_text(" ", strip=True) if link.parent else ""
            match = re.search(r"20\d{2}[-/.年]\d{1,2}[-/.月]\d{1,2}日?", nearby)
            if match:
                parsed_date = parse_published_datetime(match.group(0))
                if parsed_date:
                    dates[url] = parsed_date.date()
            if len(urls) >= limit:
                break
        self.listing_candidate_titles = titles
        self.listing_candidate_dates = dates
        return urls
