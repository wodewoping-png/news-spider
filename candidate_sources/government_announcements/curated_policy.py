"""Conservative, dated listing parser for individually verified official columns.

These columns archive metadata until a per-site detail body contract is reviewed.
The source table lives in central_policy_channels.json and is the sole allowlist.
"""
from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from .base import ContractViolation, ListingItem, normalize_space, parse_platform_date
from .scrapers import GovernmentDocumentScraper

CHANNELS_PATH = Path(__file__).with_name("central_policy_channels.json")
URL_DATE = re.compile(r"/(20\d{2})/(\d{1,2})/(\d{1,2})/")
MONTH_DATE = re.compile(r"/(20\d{2})(\d{2})/t20\d{6}_")
SKIP_TITLE = re.compile(r"(一图读懂|图解|图片解读|领导活动|时政要闻|公务员|招聘|招录|表彰|评选|获奖名单|比赛|大赛|人事任免)")
SCRIPT_TITLE = re.compile(r"\bvar\s+_docTitle\s*=\s*(['\"])(.*?)\1\s*;", re.S)


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
        soup = BeautifulSoup(html, "html.parser")
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


def curated_scrapers() -> dict[str, type[CuratedPolicyListingScraper]]:
    classes = {}
    for site in load_policy_sites():
        for column in site["columns"]:
            if column["status"] != "active":
                continue
            url = column["url"]
            if not url.startswith("https://") or not column.get("detail_path_re"):
                raise ValueError(f"active policy column missing URL contract: {site['agency']}")
            name = f"{site['agency']}—{column['label']}"
            if name in classes:
                raise ValueError(f"duplicate curated policy channel: {name}")
            parser = type(
                "Curated_" + str(len(classes)),
                (CuratedPolicyListingScraper,),
                {"source_id": "curated_" + str(len(classes)), "source_name": name,
                 "allowed_host": urlparse(url).netloc, "listing_url": url,
                 "additional_allowed_hosts": tuple(column.get("additional_allowed_hosts", [])),
                 "detail_path_re": re.compile(column["detail_path_re"]),
                 "title_pattern": re.compile(column["title_pattern"]) if column.get("title_pattern") else None},
            )
            classes[name] = parser
    return classes
