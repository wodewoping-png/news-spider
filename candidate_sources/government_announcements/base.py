from __future__ import annotations

import posixpath
import re
from dataclasses import asdict, dataclass
from datetime import date
from typing import ClassVar
from urllib.parse import urlparse, urlunparse

from bs4 import BeautifulSoup, Tag


DATE_RE = re.compile(r"(?P<year>20\d{2})[年/\-.](?P<month>\d{1,2})[月/\-.](?P<day>\d{1,2})日?")
SPACE_RE = re.compile(r"\s+")


class ContractViolation(ValueError):
    """The response falls outside a verified candidate contract."""


def normalize_space(value: str) -> str:
    return SPACE_RE.sub(" ", value).strip()


def parse_platform_date(value: str) -> date:
    match = DATE_RE.search(value)
    if not match:
        raise ContractViolation(f"unparseable platform date: {value!r}")
    return date(*(int(match.group(name)) for name in ("year", "month", "day")))


def canonical_url(value: str) -> str:
    parsed = urlparse(value)
    raw_path = re.sub(r"/{2,}", "/", parsed.path or "/")
    path = posixpath.normpath(raw_path)
    if not path.startswith("/"):
        path = f"/{path}"
    if raw_path.endswith("/") and not path.endswith("/"):
        path += "/"
    return urlunparse((parsed.scheme.lower(), parsed.netloc.lower(), path, "", parsed.query, ""))


def cleaned_html_text(node: Tag) -> str:
    return normalize_space(BeautifulSoup(str(node), "html.parser").get_text("\n", strip=True))


@dataclass(frozen=True)
class ListingItem:
    title: str
    url: str
    platform_published_at: date | None
    list_summary: str | None = None

    def to_dict(self) -> dict[str, str | None]:
        result = asdict(self)
        result["platform_published_at"] = (
            self.platform_published_at.isoformat() if self.platform_published_at else None
        )
        return result


@dataclass(frozen=True)
class CandidateArticle:
    source_id: str
    source_name: str
    title: str
    platform_url: str
    platform_published_at: date
    content: str
    source: str | None = None
    timezone: str = "Asia/Shanghai"
    production_enabled: bool = False


class CandidateScraper:
    source_id: ClassVar[str]
    source_name: ClassVar[str]
    allowed_host: ClassVar[str]
    additional_allowed_hosts: ClassVar[tuple[str, ...]] = ()

    @property
    def allowed_hosts(self) -> tuple[str, ...]:
        return (self.allowed_host,) + self.additional_allowed_hosts

    def guard_url(self, url: str, *, detail: bool = False) -> str:
        normalized = canonical_url(url)
        parsed = urlparse(normalized)
        if parsed.scheme != "https" or parsed.netloc.lower() not in self.allowed_hosts:
            raise ContractViolation(f"off-contract origin: {url}")
        self._guard_path(parsed.path, detail=detail)
        return normalized

    def _guard_path(self, path: str, *, detail: bool) -> None:
        raise NotImplementedError

    def parse_listing(self, html: str, page_url: str) -> list[ListingItem]:
        raise NotImplementedError

    def parse_detail(self, html: str, url: str) -> CandidateArticle:
        raise NotImplementedError

    def _article(
        self,
        *,
        title: str,
        url: str,
        published: date,
        content: str,
        source: str | None = None,
    ) -> CandidateArticle:
        if not title or not content:
            raise ContractViolation("detail title/content is empty")
        return CandidateArticle(
            source_id=self.source_id,
            source_name=self.source_name,
            title=title,
            platform_url=self.guard_url(url, detail=True),
            platform_published_at=published,
            content=content,
            source=source,
        )
