"""Verified policy lists with stable document paths outside the original 10 channels."""
from __future__ import annotations

import re
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from .base import ContractViolation, ListingItem, normalize_space, parse_platform_date
from .scrapers import StaticMinistryScraper


class LswzPolicyReleasesScraper(StaticMinistryScraper):
    source_id = "lswz_policy_releases_candidate"
    source_name = "国家粮食和物资储备局—政策发布（候选）"
    allowed_host = "www.lswz.gov.cn"
    listing_url = "https://www.lswz.gov.cn/html/zcfb/index.shtml"
    row_selector = "ul.lists > li"
    date_selector = "a"
    detail_path_re = re.compile(r"/html/zcfb/20\d{2}-\d{2}/\d{2}/content_\d+\.shtml")
    body_selector = ".pub-det-content"
    site_marker = "国家粮食和物资储备局"
    max_items = 30

    def parse_listing(self, html: str, page_url: str) -> list[ListingItem]:
        self.guard_url(page_url)
        items = []
        for node in BeautifulSoup(html, "html.parser").select(self.row_selector):
            anchor = node.select_one("a[href]")
            if not anchor:
                continue
            try:
                url = self._candidate_url(page_url, str(anchor["href"]))
                match = re.search(r"/zcfb/(20\d{2})-(\d{2})/(\d{2})/", urlparse(url).path)
                if match is None:
                    continue
                published = parse_platform_date("-".join(match.groups()))
            except ContractViolation:
                continue
            title = normalize_space(str(anchor.get("title") or anchor.get_text(" ", strip=True)))
            if title:
                items.append(ListingItem(title, url, published))
            if len(items) >= self.max_items:
                break
        return items


class ForestryPolicyDocumentsScraper(StaticMinistryScraper):
    source_id = "forestry_policy_documents_candidate"
    source_name = "国家林业和草原局—林草政策（候选）"
    allowed_host = "www.forestry.gov.cn"
    listing_url = "https://www.forestry.gov.cn/zcgg.jhtml"
    row_selector = "div.news_list li"
    date_selector = "span"
    detail_path_re = re.compile(r"/lyj/1/lczc/20\d{6}/\d+\.html")
    body_selector = "#zoomit"
    title_selector = ".new_name h1"
    max_items = 30

    def _detail_date(self, soup: BeautifulSoup) -> str:
        for node in soup.select(".new_name p"):
            text = normalize_space(node.get_text(" ", strip=True))
            if re.search(r"20\d{2}-\d{2}-\d{2}", text):
                return text
        return ""

    def parse_detail(self, html: str, url: str):
        soup = BeautifulSoup(html, "html.parser")
        page_title = normalize_space(soup.title.get_text(" ", strip=True)) if soup.title else ""
        if not page_title.endswith("_国家林业和草原局政府网"):
            raise ContractViolation("forestry site title marker missing")
        return super().parse_detail(html, url)
