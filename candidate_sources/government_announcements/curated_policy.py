"""Conservative, dated listing parser for individually verified official columns.

These columns archive metadata until a per-site detail body contract is reviewed.
The source table lives in central_policy_channels.json and is the sole allowlist.
"""
from __future__ import annotations

import json
import re
from datetime import date
from html import escape
from pathlib import Path
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from src.http_client import is_access_challenge_html

from .base import ContractViolation, ListingItem, normalize_space, parse_platform_date
from .scrapers import GovernmentDocumentScraper

CHANNELS_PATH = Path(__file__).with_name("central_policy_channels.json")
URL_DATE = re.compile(r"/(20\d{2})/(\d{1,2})/(\d{1,2})/")
MONTH_DATE = re.compile(r"/(20\d{2})(\d{2})/t20\d{6}_")
SKIP_TITLE = re.compile(r"(一图读懂|图解|图片解读|领导活动|时政要闻|公务员|招聘|招录|表彰|评选|获奖名单|比赛|大赛|人事任免)")
SCRIPT_TITLE = re.compile(r"\bvar\s+_docTitle\s*=\s*(['\"])(.*?)\1\s*;", re.S)
CDATA_RECORD = re.compile(r"<record>\s*<!\[CDATA\[(.*?)\]\]>\s*</record>", re.I | re.S)
JSON_ITEMS = re.compile(r"\bvar\s+itemObj\s*=\s*")


def load_policy_sites() -> list[dict]:
    sites = json.loads(CHANNELS_PATH.read_text(encoding="utf-8"))
    if len(sites) != 57 or len({site["agency"] for site in sites}) != 57:
        raise ValueError("central policy agency registry must have 57 distinct entries")
    return sites


class CuratedPolicyListingScraper(GovernmentDocumentScraper):
    """Collect only dated same-origin article links from one fixed official column."""

    fetch_detail = False
    max_items = 40
    listing_url: str
    allowed_host: str
    additional_allowed_hosts: tuple[str, ...] = ()
    detail_path_re: re.Pattern[str]
    title_pattern: re.Pattern[str] | None = None
    embedded_records: bool = False
    embedded_json_items: bool = False

    def _guard_path(self, path: str, *, detail: bool) -> None:
        if not (self.detail_path_re.fullmatch(path) if detail else path == urlparse(self.listing_url).path):
            raise ContractViolation(f"unverified policy path: {path}")

    def parse_listing(self, html: str, page_url: str) -> list[ListingItem]:
        # Some official servers redirect their own HTTPS listing to HTTP.
        # Keep the configured origin/path contract for parsing; each article
        # link is separately normalized to the official HTTPS URL.
        if page_url.startswith("http://") and urlparse(page_url).netloc == self.allowed_host:
            page_url = "https://" + page_url.removeprefix("http://")
        self.guard_url(page_url)
        # Several official jpage templates keep their visible listing in
        # <record><![CDATA[...]]></record> within a script, then render it in
        # the browser. Parse only the bounded literal record fragments.
        records = CDATA_RECORD.findall(html)[:80] if self.embedded_records else []
        listing_html = "".join(records) if records else html
        if self.embedded_json_items:
            match = JSON_ITEMS.search(html)
            if not match:
                raise ContractViolation("verified policy JSON items missing")
            try:
                rows, _ = json.JSONDecoder().raw_decode(html[match.end():])
            except ValueError as exc:
                raise ContractViolation("invalid official policy JSON items") from exc
            if not isinstance(rows, list):
                raise ContractViolation("official policy JSON items are not a list")
            fragments = []
            for row in rows[:80]:
                if not isinstance(row, dict):
                    continue
                try:
                    path = json.loads(row.get("aU") or "{}").get("common", "")
                except (TypeError, ValueError, AttributeError):
                    continue
                if not isinstance(path, str) or not path.startswith("/"):
                    continue
                title = BeautifulSoup(str(row.get("aT") or ""), "html.parser").get_text(" ", strip=True)
                published = str(row.get("aPd") or "")
                fragments.append(f'<li><a href="{escape(path, quote=True)}">{escape(title)}</a>'
                                 f'<span>{escape(published)}</span></li>')
            listing_html = "".join(fragments)
        soup = BeautifulSoup(listing_html, "html.parser")
        items: list[ListingItem] = []
        seen = set()
        for anchor in soup.select("a[href]"):
            href = str(anchor.get("href") or "")
            raw = urljoin(page_url, href)
            if urlparse(raw).scheme == "http" and urlparse(raw).netloc in self.allowed_hosts:
                raw = "https://" + raw.removeprefix("http://")
            try:
                target = self.guard_url(raw, detail=True)
            except ContractViolation:
                continue
            if target in seen:
                continue
            title_node = anchor.select_one(".news-title, p")
            title = normalize_space(str(anchor.get("title") or (
                title_node.get_text(" ", strip=True) if title_node else anchor.get_text(" ", strip=True)
            )))
            # NPPA writes the title through a fixed inline document.write snippet.
            # Read only its literal assignment; never execute page JavaScript.
            if not title:
                script = anchor.select_one("script")
                match = SCRIPT_TITLE.search(script.string or "") if script else None
                if match:
                    title = normalize_space(match.group(2))
            title = re.sub(r"\s*20\d{2}[-./]\d{1,2}[-./]\d{1,2}$", "", title)
            title = re.sub(r"\s*[（(]20\d{2}[-./]\d{1,2}[-./]\d{1,2}[）)]$", "", title)
            if not 9 <= len(title) <= 180 or SKIP_TITLE.search(title):
                continue
            if self.title_pattern and not self.title_pattern.search(title):
                continue
            container = anchor.find_parent(["li", "tr"]) or anchor.parent
            stamp = normalize_space(container.get_text(" ", strip=True)) if container else ""
            try:
                published = parse_platform_date(stamp[:350])
            except (ContractViolation, ValueError):
                match = URL_DATE.search(urlparse(target).path)
                if not match:
                    continue
                try:
                    published = date(*map(int, match.groups()))
                except ValueError:
                    continue
            # Only recent listing entries. Old laws pinned to the top should not
            # consume the daily candidate cap or masquerade as new announcements.
            seen.add(target)
            items.append(ListingItem(title, target, published))
            if len(items) >= self.max_items:
                break
        return items

    def parse_detail(self, html: str, url: str):
        raise ContractViolation("curated column has metadata-only approval")


class DetailDatedPolicyListingScraper(CuratedPolicyListingScraper):
    """Keep an undated candidate only after checking the official detail publication field."""

    detail_date_kind: str

    def parse_listing(self, html: str, page_url: str) -> list[ListingItem]:
        self.guard_url(page_url)
        soup = BeautifulSoup(html, "html.parser")
        items: list[ListingItem] = []
        seen: set[str] = set()
        for anchor in soup.select("a[href]"):
            raw = urljoin(page_url, str(anchor.get("href") or ""))
            if self.detail_date_kind == "caac":
                # The CAAC search template points at a PHONE/ HTTP alias of
                # the same document; use its verified canonical HTTPS path.
                raw = raw.replace("http://www.caac.gov.cn/PHONE/XXGK_17/", "https://www.caac.gov.cn/XXGK/")
            try:
                target = self.guard_url(raw, detail=True)
            except ContractViolation:
                continue
            title = normalize_space(str(anchor.get("title") or anchor.get_text(" ", strip=True)))
            if target in seen or not 9 <= len(title) <= 180 or SKIP_TITLE.search(title):
                continue
            if self.title_pattern and not self.title_pattern.search(title):
                continue
            seen.add(target)
            items.append(ListingItem(title, target, None))
            if len(items) >= self.max_items:
                break
        return items

    def verified_date(self, html: str, url: str) -> date:
        self.guard_url(url, detail=True)
        if is_access_challenge_html(html):
            raise ContractViolation("detail access challenge")
        if self.detail_date_kind in {"audit", "sport"}:
            tag = BeautifulSoup(html, "html.parser").find("meta", attrs={"name": "PubDate"})
            value = str(tag.get("content") or "") if tag else ""
        elif self.detail_date_kind == "caac":
            match = re.search(r"\bvar\s+__\$pubtime\s*=\s*['\"](20\d{2}-\d{2}-\d{2}(?:\s+\d{2}:\d{2}:\d{2})?)['\"]", html)
            value = match.group(1) if match else ""
        else:
            raise ContractViolation("unverified detail date kind")
        return parse_platform_date(value)


class NfraPolicyApiListingScraper(CuratedPolicyListingScraper):
    """Read the NFRA's public document list, not its empty Angular page shell."""

    data_url: str
    item_id: int

    def _guard_path(self, path: str, *, detail: bool) -> None:
        expected = "/cn/view/pages/ItemDetail.html" if detail else "/cbircweb/DocInfo/SelectDocByItemIdAndChild"
        if path != expected:
            raise ContractViolation(f"unverified NFRA path: {path}")

    def parse_listing_json(self, value: str, page_url: str) -> list[ListingItem]:
        if self.guard_url(page_url) != self.data_url:
            raise ContractViolation("unverified NFRA list query")
        try:
            payload = json.loads(value)
        except ValueError as exc:
            raise ContractViolation("invalid NFRA document list") from exc
        if not isinstance(payload, dict) or payload.get("rptCode") != 200:
            raise ContractViolation("NFRA document list failed")
        data = payload.get("data")
        rows = data.get("rows") if isinstance(data, dict) else None
        if not isinstance(rows, list):
            raise ContractViolation("NFRA document rows missing")
        items = []
        for row in rows[:self.max_items]:
            if not isinstance(row, dict) or not isinstance(row.get("docId"), int):
                continue
            title = normalize_space(str(row.get("docTitle") or ""))
            if not 9 <= len(title) <= 180 or SKIP_TITLE.search(title):
                continue
            if self.title_pattern and not self.title_pattern.search(title):
                continue
            try:
                published = parse_platform_date(str(row.get("publishDate") or ""))
            except (ContractViolation, ValueError):
                continue
            detail_url = (f"https://www.nfra.gov.cn/cn/view/pages/ItemDetail.html"
                          f"?docId={row['docId']}&itemId={self.item_id}")
            items.append(ListingItem(title, self.guard_url(detail_url, detail=True), published))
        return items


def curated_scrapers() -> dict[str, type[CuratedPolicyListingScraper]]:
    classes = {}
    for site in load_policy_sites():
        for column in site["columns"]:
            if column["status"] != "active":
                continue
            url = column["url"]
            if not url.startswith("https://") or not (column.get("detail_path_re") or column.get("api_url")):
                raise ValueError(f"active policy column missing URL contract: {site['agency']}")
            name = f"{site['agency']}—{column['label']}"
            if name in classes:
                raise ValueError(f"duplicate curated policy channel: {name}")
            is_nfra = bool(column.get("api_url"))
            date_kind = column.get("detail_date_kind")
            if date_kind and date_kind not in {"audit", "caac", "sport"}:
                raise ValueError("unverified detail date kind")
            if is_nfra and (urlparse(url).netloc != "www.nfra.gov.cn" or
                            not column["api_url"].startswith("https://www.nfra.gov.cn/cbircweb/DocInfo/SelectDocByItemIdAndChild?")):
                raise ValueError("unverified NFRA API origin or path")
            attrs = {
                 "source_id": "curated_" + str(len(classes)), "source_name": name,
                 "allowed_host": urlparse(url).netloc, "listing_url": url,
                 "additional_allowed_hosts": tuple(column.get("additional_allowed_hosts", [])),
                 "detail_path_re": re.compile(column.get("detail_path_re") or r"/cn/view/pages/ItemDetail\.html"),
                 "embedded_records": bool(column.get("embedded_records", False)),
                 "embedded_json_items": bool(column.get("embedded_json_items", False)),
                 "title_pattern": re.compile(column["title_pattern"]) if column.get("title_pattern") else None,
                 "detail_date_kind": date_kind,
            }
            if is_nfra:
                attrs.update(data_url=column["api_url"], item_id=int(column["item_id"]))
            parser = type(
                "Curated_" + str(len(classes)),
                (NfraPolicyApiListingScraper if is_nfra else
                 DetailDatedPolicyListingScraper if date_kind else CuratedPolicyListingScraper,),
                attrs,
            )
            classes[name] = parser
    return classes
