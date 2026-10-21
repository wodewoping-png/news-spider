"""China Government Network policy lists, with separate document and analysis scopes."""
from __future__ import annotations

import json
import re
from typing import ClassVar
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from .base import CandidateArticle, ContractViolation, ListingItem, normalize_space, parse_platform_date
from .scrapers import StaticMinistryScraper, _text_only


class GovCnJsonScraper(StaticMinistryScraper):
    allowed_host = "www.gov.cn"
    listing_url: ClassVar[str]
    data_url: ClassVar[str]
    body_selector = "#UCAP-CONTENT"
    max_items = 60
    # A JSON list replaces the empty, JavaScript-populated HTML list.
    row_selector = ""
    date_selector = ""

    def _guard_path(self, path: str, *, detail: bool) -> None:
        if detail:
            valid = bool(self.detail_path_re.fullmatch(path))
        else:
            valid = path in {urlparse(self.listing_url).path, urlparse(self.data_url).path}
        if not valid:
            raise ContractViolation(f"unverified gov.cn path: {path}")

    def accepts_title(self, title: str) -> bool:
        raise NotImplementedError

    def parse_listing_json(self, payload: str | bytes, data_url: str | None = None) -> list[ListingItem]:
        self.guard_url(data_url or self.data_url)
        try:
            rows = json.loads(payload)
        except (ValueError, TypeError) as exc:
            raise ContractViolation("invalid gov.cn policy JSON") from exc
        if not isinstance(rows, list):
            raise ContractViolation("gov.cn policy JSON must be an array")
        items: list[ListingItem] = []
        seen: set[str] = set()
        for row in rows:
            if not isinstance(row, dict):
                continue
            title = normalize_space(BeautifulSoup(str(row.get("TITLE") or ""), "html.parser").get_text(" ", strip=True))
            try:
                url = self.guard_url(str(row.get("URL") or ""), detail=True)
                published = parse_platform_date(str(row.get("DOCRELPUBTIME") or ""))
            except ContractViolation:
                continue
            if title and self.accepts_title(title) and url not in seen:
                seen.add(url)
                items.append(ListingItem(title, url, published))
                if len(items) >= self.max_items:
                    break
        return items

    def parse_listing(self, html: str, page_url: str) -> list[ListingItem]:
        raise ContractViolation("gov.cn list is populated from JSON; use parse_listing_json")


class GovCnPolicyDocumentsScraper(GovCnJsonScraper):
    source_id = "gov_cn_policy_documents_candidate"
    source_name = "中国政府网—最新政策（候选）"
    listing_url = "https://www.gov.cn/zhengce/zuixin/"
    data_url = "https://www.gov.cn/zhengce/zuixin/ZUIXINZHENGCE.json"
    detail_path_re = re.compile(r"/zhengce/(?:content/)?20\d{4}/content_\d+\.htm")
    _policy_terms = re.compile(r"意见|通知|批复|条例|办法|决定|规划|规定|方案|规则|指南|措施|法律|纲要|国务院令")
    _non_document = re.compile(r"答记者问|政策解读|发布会|记者会|访谈|图表|图解|负责人解读")

    def accepts_title(self, title: str) -> bool:
        return bool(self._policy_terms.search(title)) and not self._non_document.search(title)

    def parse_detail(self, html: str, url: str) -> CandidateArticle:
        self.guard_url(url, detail=True)
        soup = BeautifulSoup(html, "html.parser")
        page_title = normalize_space(soup.title.get_text(" ", strip=True)) if soup.title else ""
        if not page_title.endswith("_中国政府网"):
            raise ContractViolation("gov.cn site title marker missing")
        body = soup.select_one(self.body_selector)
        time_node = soup.select_one('meta[name="firstpublishedtime"][content]')
        title = page_title.split("_", 1)[0]
        if body is None or time_node is None or not self.accepts_title(title):
            raise ContractViolation("gov.cn policy document selector missing")
        return self._article(title=title, url=url,
                             published=parse_platform_date(str(time_node["content"])),
                             content=_text_only(body), source="中国政府网")


class GovCnPolicyInterpretationsScraper(GovCnJsonScraper):
    source_id = "gov_cn_policy_interpretations_candidate"
    source_name = "中国政府网—政策解读（候选）"
    listing_url = "https://www.gov.cn/zhengce/jiedu/index.htm"
    data_url = "https://www.gov.cn/zhengce/jiedu/ZCJD_QZ.json"
    detail_path_re = re.compile(r"/zhengce/20\d{4}/content_\d+\.htm")
    # The listing includes news, interviews, statistics, pictures and pinned topics.
    _specific_document = re.compile(r"《[^》]{2,100}》")
    _explanation = re.compile(r"答记者问|政策解读|文件解读|负责人解读|负责人详解|解读《|解读〈")
    fetch_detail = False  # Link and metadata only; no copied interpretation prose.

    def accepts_title(self, title: str) -> bool:
        return bool(self._specific_document.search(title) and self._explanation.search(title))
