from __future__ import annotations

import json
import re
from typing import ClassVar
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from .base import (
    CandidateArticle,
    CandidateScraper,
    ContractViolation,
    ListingItem,
    canonical_url,
    cleaned_html_text,
    normalize_space,
    parse_platform_date,
)


def _meta(soup: BeautifulSoup, name: str) -> str:
    for node in soup.select("meta[name][content]"):
        if str(node.get("name", "")).lower() == name.lower():
            return normalize_space(str(node.get("content", "")))
    return ""


def _text_only(node) -> str:
    clone = BeautifulSoup(str(node), "html.parser")
    for block in list(clone.select("p, li, div")):
        block_text = normalize_space(block.get_text(" ", strip=True))
        if block.select_one("a[href]") and block_text.startswith(("附件", "政策解读")):
            block.decompose()
    for anchor in list(clone.select("a[href]")):
        href = str(anchor.get("href", "")).lower().split("?", 1)[0]
        parent = anchor.parent
        parent_text = normalize_space(parent.get_text(" ", strip=True)) if parent else ""
        is_attachment = href.endswith((".doc", ".docx", ".pdf", ".wps", ".xls", ".xlsx", ".zip", ".rar"))
        is_related = parent_text.startswith(("附件", "政策解读"))
        if is_attachment or is_related:
            if parent and parent.name in {"p", "li", "div"}:
                parent.decompose()
            else:
                anchor.decompose()
        else:
            anchor.unwrap()
    for unwanted in clone.select("script, style, noscript, img, video, audio, iframe"):
        unwanted.decompose()
    text = cleaned_html_text(clone)
    if len(text) > 250_000:
        raise ContractViolation("government document body exceeds 250,000 characters")
    return text


class GovernmentDocumentScraper(CandidateScraper):
    """A fail-closed, text-only candidate for official government documents."""

    production_enabled: ClassVar[bool] = False
    downloads_attachments: ClassVar[bool] = False
    copies_images: ClassVar[bool] = False
    full_text_scope: ClassVar[str] = "official_document_only"
    fetch_detail: ClassVar[bool] = True


class NeaDocumentScraper(GovernmentDocumentScraper):
    allowed_host = "www.nea.gov.cn"
    data_url: ClassVar[str]
    listing_url: ClassVar[str]
    max_items: ClassVar[int] = 25

    def _guard_path(self, path: str, *, detail: bool) -> None:
        if detail:
            valid = bool(re.fullmatch(r"/20\d{6}/[0-9a-f]{32}/c\.html", path))
        else:
            valid = path in {urlparse(self.listing_url).path, urlparse(self.data_url).path}
        if not valid:
            raise ContractViolation(f"unverified NEA path: {path}")

    def parse_listing_json(self, payload: str | bytes, data_url: str | None = None) -> list[ListingItem]:
        self.guard_url(data_url or self.data_url)
        try:
            document = json.loads(payload)
        except (TypeError, ValueError) as exc:
            raise ContractViolation("invalid NEA listing JSON") from exc
        rows = document.get("datasource")
        if not isinstance(rows, list):
            raise ContractViolation("NEA listing JSON has no datasource array")
        items: list[ListingItem] = []
        for row in rows[: self.max_items]:
            if not isinstance(row, dict):
                continue
            raw_url = normalize_space(str(row.get("publishUrl") or ""))
            if raw_url.startswith("http://www.nea.gov.cn/"):
                raw_url = "https://" + raw_url.removeprefix("http://")
            target = urljoin(self.listing_url, raw_url)
            try:
                target = self.guard_url(target, detail=True)
                published = parse_platform_date(str(row.get("publishTime") or ""))
            except ContractViolation:
                continue
            raw_title = str(row.get("showTitle") or row.get("title") or "")
            title = normalize_space(BeautifulSoup(raw_title, "html.parser").get_text(" ", strip=True))
            if title:
                items.append(ListingItem(title, target, published))
        return items

    def parse_listing(self, html: str, page_url: str) -> list[ListingItem]:
        raise ContractViolation("NEA listing is JSON; use parse_listing_json")

    def parse_detail(self, html: str, url: str) -> CandidateArticle:
        self.guard_url(url, detail=True)
        soup = BeautifulSoup(html, "html.parser")
        if _meta(soup, "SiteName") != "国家能源局":
            raise ContractViolation("NEA SiteName marker missing")
        title = _meta(soup, "ArticleTitle")
        published = _meta(soup, "PubDate") or _meta(soup, "publishdate")
        source = _meta(soup, "ContentSource") or None
        body = soup.select_one("#detailContent")
        if not title or not published or body is None:
            raise ContractViolation("missing NEA document selector")
        return self._article(
            title=title,
            url=url,
            published=parse_platform_date(published),
            content=_text_only(body),
            source=source,
        )


class NeaNoticesScraper(NeaDocumentScraper):
    source_id = "nea_notices_candidate"
    source_name = "国家能源局—通知（候选）"
    listing_url = "https://www.nea.gov.cn/policy/tz.htm"
    data_url = "https://www.nea.gov.cn/policy/ds_7290c82b05cc4d49be4971ade193edfc.json"


class NeaAnnouncementsScraper(NeaDocumentScraper):
    source_id = "nea_announcements_candidate"
    source_name = "国家能源局—公告（候选）"
    listing_url = "https://www.nea.gov.cn/policy/gg.htm"
    data_url = "https://www.nea.gov.cn/policy/ds_6db2ed2a0ae946d882bcc769494c99be.json"


class MiitPublicNoticesScraper(GovernmentDocumentScraper):
    source_id = "miit_public_notices_candidate"
    source_name = "工业和信息化部—文件公示（候选）"
    allowed_host = "www.miit.gov.cn"
    listing_url = "https://www.miit.gov.cn/zwgk/wjgs/index.html"
    data_url = "https://www.miit.gov.cn/api-gateway/jpaas-publish-server/front/page/build/unit"
    query_params: ClassVar[dict[str, str]] = {
        "parseType": "buildstatic",
        "webId": "8d828e408d90447786ddbe128d495e9e",
        "tplSetId": "209741b2109044b5b7695700b2bec37e",
        "pageType": "column",
        "tagId": "右侧内容",
        "editType": "null",
        "pageId": "a7180b76aadf4a2ca625f403045cbaae",
    }

    def _guard_path(self, path: str, *, detail: bool) -> None:
        if detail:
            valid = bool(re.fullmatch(r"/zwgk/wjgs/art/20\d{2}/art_[0-9a-f]{32}\.html", path))
        else:
            valid = path in {urlparse(self.listing_url).path, urlparse(self.data_url).path}
        if not valid:
            raise ContractViolation(f"unverified MIIT path: {path}")

    def parse_api_response(self, payload: str | bytes, data_url: str | None = None) -> list[ListingItem]:
        self.guard_url(data_url or self.data_url)
        try:
            document = json.loads(payload)
            fragment = document["data"]["html"]
        except (TypeError, ValueError, KeyError) as exc:
            raise ContractViolation("invalid MIIT listing API response") from exc
        if not isinstance(fragment, str):
            raise ContractViolation("MIIT listing fragment is not text")
        return self.parse_listing(fragment, self.listing_url)

    def parse_listing(self, html: str, page_url: str) -> list[ListingItem]:
        self.guard_url(page_url)
        soup = BeautifulSoup(html, "html.parser")
        items: list[ListingItem] = []
        for row in soup.select("div.page-content li")[:24]:
            anchor = row.select_one("a[href]")
            date_node = row.select_one("span")
            if not anchor or not date_node:
                continue
            try:
                target = self.guard_url(urljoin(page_url, anchor["href"]), detail=True)
                published = parse_platform_date(date_node.get_text(" ", strip=True))
            except ContractViolation:
                continue
            title = normalize_space(str(anchor.get("title") or anchor.get_text(" ", strip=True)))
            if title:
                items.append(ListingItem(title, target, published))
        return items

    def parse_detail(self, html: str, url: str) -> CandidateArticle:
        self.guard_url(url, detail=True)
        soup = BeautifulSoup(html, "html.parser")
        site_name = _meta(soup, "SiteName")
        if "工业和信息化部" not in site_name:
            raise ContractViolation("MIIT SiteName marker missing")
        title_node = soup.select_one("#con_title")
        time_node = soup.select_one("#con_time")
        body = soup.select_one("#con_con")
        if title_node is None or time_node is None or body is None:
            raise ContractViolation("missing MIIT document selector")
        source = _meta(soup, "ContentSource") or None
        return self._article(
            title=normalize_space(title_node.get_text(" ", strip=True)),
            url=url,
            published=parse_platform_date(time_node.get_text(" ", strip=True)),
            content=_text_only(body),
            source=source,
        )


class StaticMinistryScraper(GovernmentDocumentScraper):
    listing_url: ClassVar[str]
    row_selector: ClassVar[str]
    anchor_selector: ClassVar[str] = "a[href]"
    date_selector: ClassVar[str]
    detail_path_re: ClassVar[re.Pattern[str]]
    body_selector: ClassVar[str]
    title_selector: ClassVar[str | None] = None
    date_detail_selector: ClassVar[str | None] = None
    source_selector: ClassVar[str | None] = None
    site_marker: ClassVar[str | None] = None
    max_items: ClassVar[int] = 40

    def _guard_path(self, path: str, *, detail: bool) -> None:
        valid = bool(self.detail_path_re.fullmatch(path)) if detail else path == urlparse(self.listing_url).path
        if not valid:
            raise ContractViolation(f"unverified {self.source_id} path: {path}")

    def _candidate_url(self, page_url: str, href: str) -> str:
        target = urljoin(page_url, href)
        parsed = urlparse(target)
        if parsed.scheme == "http" and parsed.netloc.lower() in self.allowed_hosts:
            target = "https://" + target.removeprefix("http://")
        return self.guard_url(target, detail=True)

    def parse_listing(self, html: str, page_url: str) -> list[ListingItem]:
        self.guard_url(page_url)
        soup = BeautifulSoup(html, "html.parser")
        items: list[ListingItem] = []
        for row in soup.select(self.row_selector):
            anchor = row.select_one(self.anchor_selector)
            date_node = row.select_one(self.date_selector)
            if not anchor or not date_node:
                continue
            try:
                target = self._candidate_url(page_url, str(anchor.get("href", "")))
                published = parse_platform_date(date_node.get_text(" ", strip=True))
            except ContractViolation:
                continue
            title = normalize_space(str(anchor.get("title") or anchor.get_text(" ", strip=True)))
            if title:
                items.append(ListingItem(title, target, published))
            if len(items) >= self.max_items:
                break
        return items

    def _detail_title(self, soup: BeautifulSoup) -> str:
        title = _meta(soup, "ArticleTitle")
        if not title and self.title_selector:
            node = soup.select_one(self.title_selector)
            title = normalize_space(node.get_text(" ", strip=True)) if node else ""
        return title

    def _detail_date(self, soup: BeautifulSoup) -> str:
        published = _meta(soup, "PubDate")
        if not published and self.date_detail_selector:
            node = soup.select_one(self.date_detail_selector)
            published = normalize_space(node.get_text(" ", strip=True)) if node else ""
        return published

    def _detail_source(self, soup: BeautifulSoup) -> str | None:
        source = _meta(soup, "ContentSource")
        if not source and self.source_selector:
            node = soup.select_one(self.source_selector)
            raw = normalize_space(node.get_text(" ", strip=True)) if node else ""
            match = re.search(
                r"(?:来源|发文单位)\s*[：:]\s*(.*?)"
                r"(?=\s+(?:所属机构|主题分类|公文种类|成文日期|发布日期|索引号|发文字号)\s*[：:]|$)",
                raw,
            )
            source = normalize_space(match.group(1)) if match else ""
        return source or None

    def parse_detail(self, html: str, url: str) -> CandidateArticle:
        self.guard_url(url, detail=True)
        soup = BeautifulSoup(html, "html.parser")
        if self.site_marker:
            marker = _meta(soup, "SiteName")
            if self.site_marker not in marker:
                raise ContractViolation(f"{self.source_id} SiteName marker missing")
        bodies = soup.select(self.body_selector)
        body = max(bodies, key=lambda node: len(node.get_text(" ", strip=True)), default=None)
        title, published = self._detail_title(soup), self._detail_date(soup)
        if body is None or not title or not published:
            raise ContractViolation(f"missing {self.source_id} detail selector")
        return self._article(
            title=title,
            url=url,
            published=parse_platform_date(published),
            content=_text_only(body),
            source=self._detail_source(soup),
        )


class MostNoticesScraper(StaticMinistryScraper):
    source_id = "most_notices_candidate"
    source_name = "科学技术部—通知通告（候选）"
    allowed_host = "www.most.gov.cn"
    listing_url = "https://www.most.gov.cn/tztg/"
    row_selector = "ul.info_list2 > li"
    date_selector = "span.date.mhide"
    detail_path_re = re.compile(r"/tztg/20\d{4}/t20\d{6}_\d+\.html")
    body_selector = "div.text.wide"
    title_selector = "div.title_wide"
    date_detail_selector = "div.notes"
    source_selector = "div.notes"
    site_marker = "科学技术部"
    max_items = 20


class MnrNoticesScraper(StaticMinistryScraper):
    source_id = "mnr_notices_candidate"
    source_name = "自然资源部—通知公告（候选）"
    allowed_host = "www.mnr.gov.cn"
    additional_allowed_hosts = ("gi.mnr.gov.cn",)
    listing_url = "https://www.mnr.gov.cn/gk/tzgg/"
    row_selector = "ul.ky_open_list > li"
    date_selector = "span"
    detail_path_re = re.compile(r"(?:/gk/tzgg)?/20\d{4}/t20\d{6}_\d+\.html")
    body_selector = "#content1, #doccon"
    title_selector = "#doctitle"
    site_marker = "自然资源"
    max_items = 25
    fetch_detail = False

    def _detail_source(self, soup: BeautifulSoup) -> str | None:
        return _meta(soup, "ContentSource") or _meta(soup, "ContenSource") or None


class MotPolicyDocumentsScraper(StaticMinistryScraper):
    source_id = "mot_policy_documents_candidate"
    source_name = "交通运输部—其他政策性文件（候选）"
    allowed_host = "xxgk.mot.gov.cn"
    listing_url = "https://xxgk.mot.gov.cn/2020/zhengce/qtwjlist.html"
    row_selector = "tbody#xxgkzn_list_tbody_ID > tr"
    date_selector = "td:last-child"
    detail_path_re = re.compile(r"/2020/jigou/[a-z0-9]+/20\d{4}/t20\d{6}_\d+\.html")
    body_selector = "#Zoom"
    site_marker = "交通运输部"
    max_items = 10


class MofcomPolicyReleasesScraper(StaticMinistryScraper):
    source_id = "mofcom_policy_releases_candidate"
    source_name = "商务部—政策发布（候选）"
    allowed_host = "www.mofcom.gov.cn"
    listing_url = "https://www.mofcom.gov.cn/zcfb/index.html"
    row_selector = "ul.policy-list.f-mt20 > li"
    date_selector = "span"
    detail_path_re = re.compile(r"/zcfb/[a-z0-9]+/art/20\d{2}/art_[0-9a-f]{32}\.html")
    body_selector = "div.art-con.art-con-bottonmLine"
    site_marker = "商务部"
    max_items = 20

    def _detail_date(self, soup: BeautifulSoup) -> str:
        metadata = soup.select_one("div.art-con.art-con-bottonmLine")
        raw = normalize_space(metadata.get_text(" ", strip=True)) if metadata else ""
        match = re.search(r"发文日期\s*[：:]\s*(20\d{2}年\d{1,2}月\d{1,2}日)", raw)
        return match.group(1) if match else super()._detail_date(soup)


class MemNoticesScraper(StaticMinistryScraper):
    source_id = "mem_notices_candidate"
    source_name = "应急管理部—通知公告（候选）"
    allowed_host = "www.mem.gov.cn"
    listing_url = "https://www.mem.gov.cn/gk/tzgg/"
    row_selector = "div.tonglan_list li"
    date_selector = "a"
    detail_path_re = re.compile(r"/gk/zfxxgkpt/fdzdgknr/20\d{4}/t20\d{6}_\d+\.shtml")
    body_selector = "#content"
    title_selector = "title"
    date_detail_selector = "div.scy_detail_top"
    source_selector = "div.scy_detail_top"
    max_items = 30

    def _detail_date(self, soup: BeautifulSoup) -> str:
        node = soup.select_one("div.scy_detail_top")
        raw = normalize_space(node.get_text(" ", strip=True)) if node else ""
        match = re.search(r"发布日期\s*[：:]\s*(20\d{2}年\d{1,2}月\d{1,2}日)", raw)
        return match.group(1) if match else super()._detail_date(soup)


class NdaPolicyReleasesScraper(StaticMinistryScraper):
    source_id = "nda_policy_releases_candidate"
    source_name = "国家数据局—政策发布（候选）"
    allowed_host = "www.nda.gov.cn"
    listing_url = "https://www.nda.gov.cn/sjj/zwgk/zcfb/list/index_pc_1.html"
    row_selector = "ul.u-list > li"
    anchor_selector = ":scope > a[href*='/zcfb/']"
    date_selector = ":scope > span"
    detail_path_re = re.compile(r"/sjj/zwgk/zcfb/\d{4}/20\d{15,}_pc\.html")
    body_selector = "div.article"
    title_selector = "h1"
    source_selector = "li.source"
    site_marker = "国家数据局"
    max_items = 20


class SamrAntitrustNoticesScraper(StaticMinistryScraper):
    source_id = "samr_antitrust_notices_candidate"
    source_name = "市场监管总局—反垄断通知公告（候选）"
    allowed_host = "www.samr.gov.cn"
    listing_url = "https://www.samr.gov.cn/jzxts/tzgg/index.html"
    row_selector = "div.gts_contentLeftListbox > ul"
    date_selector = "li.gts_contentLeftList01time"
    detail_path_re = re.compile(r"/jzxts/tzgg/[a-z0-9]+/art/20\d{2}/art_[0-9a-f]{32}\.html")
    body_selector = "div.zt_xilan_07"
    title_selector = "li.zt_xilan_03"
    date_detail_selector = "li.zt_xilan_04"
    site_marker = "国家市场监督管理总局"
    max_items = 40


SCRAPERS: dict[str, GovernmentDocumentScraper] = {
    "nea_notices": NeaNoticesScraper(),
    "nea_announcements": NeaAnnouncementsScraper(),
    "miit_public_notices": MiitPublicNoticesScraper(),
    "most_notices": MostNoticesScraper(),
    "mnr_notices": MnrNoticesScraper(),
    "mot_policy_documents": MotPolicyDocumentsScraper(),
    "mofcom_policy_releases": MofcomPolicyReleasesScraper(),
    "mem_notices": MemNoticesScraper(),
    "nda_policy_releases": NdaPolicyReleasesScraper(),
    "samr_antitrust_notices": SamrAntitrustNoticesScraper(),
}
