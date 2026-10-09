"""Archive verified government notices and their directly linked attachments.

Run independently of the general news CSV: python -m src.government_archive.
Every source and attachment failure is recorded in the archive index.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import logging
import re
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup

from candidate_sources.government_announcements.base import ContractViolation
from candidate_sources.government_announcements.scrapers import (
    GovernmentDocumentScraper,
    MiitPublicNoticesScraper,
    NeaDocumentScraper,
    StaticMinistryScraper,
)
from .date_utils import DEFAULT_TIMEZONE
from .http_client import HttpClient
from .load_sources import load_sources
from .scrapers.government_announcements import GovernmentAnnouncementScraper
from .scrapers import get_scraper_class

EXTENSIONS = frozenset({".pdf", ".doc", ".docx", ".xls", ".xlsx", ".wps", ".zip", ".rar"})
MAX_ATTACHMENT_BYTES = 8 * 1024 * 1024
MAX_RUN_BYTES = 50 * 1024 * 1024
MAX_ATTACHMENTS_PER_NOTICE = 12
SAFE_NAME = re.compile(r'[\\/:*?"<>|\x00-\x1f]+')


def safe_name(value: str, *, max_length: int = 100) -> str:
    return (SAFE_NAME.sub("_", value).strip(" ._") or "未命名")[:max_length].rstrip(" .")


def attachment_links(parser: GovernmentDocumentScraper, html: str, page_url: str) -> list[dict]:
    """Only file links in verified document bodies or labelled attachment sections."""
    soup = BeautifulSoup(html, "html.parser")
    selectors = (
        ("#detailContent",) if isinstance(parser, NeaDocumentScraper)
        else ("#con_con",) if isinstance(parser, MiitPublicNoticesScraper)
        else tuple(parser.body_selector.split(","))
        if isinstance(parser, StaticMinistryScraper) else ()
    )
    bodies = [node for selector in selectors for node in soup.select(selector.strip())]
    seen: set[str] = set()
    results = []
    for body in bodies:
        for anchor in body.select("a[href]"):
            raw = str(anchor.get("href") or "").strip()
            if not raw or raw.startswith(("javascript:", "data:", "#")):
                continue
            url = urljoin(page_url, raw)
            parsed = urlparse(url)
            if parsed.scheme == "http" and parsed.hostname in parser.allowed_hosts:
                url = parsed._replace(scheme="https").geturl()
                parsed = urlparse(url)
            ext = Path(unquote(parsed.path)).suffix.lower()
            label = anchor.get_text(" ", strip=True)
            if parsed.scheme not in {"http", "https"} or (ext not in EXTENSIONS and "附件" not in label):
                continue
            if url in seen:
                continue
            seen.add(url)
            results.append({"url": url, "label": label, "extension": ext})
    return results


def fetch_attachment(client: HttpClient, parser: GovernmentDocumentScraper, url: str,
                     destination: Path, remaining_bytes: int) -> int:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in parser.allowed_hosts:
        raise ValueError("附件不在已核验的官方域名")
    if Path(unquote(parsed.path)).suffix.lower() not in EXTENSIONS:
        raise ValueError("附件格式未核验")
    if not client.robots.can_fetch(url, fail_closed=True):
        raise ValueError("robots.txt 未许可附件请求")
    limit = min(MAX_ATTACHMENT_BYTES, remaining_bytes)
    if limit <= 0:
        raise ValueError("本次附件下载总量已达上限")
    time.sleep(client.sleep_seconds)
    response = client.session.get(url, timeout=client.timeout, stream=True, allow_redirects=False)
    try:
        if response.status_code in {301, 302, 303, 307, 308}:
            raise ValueError("附件重定向需人工核验")
        response.raise_for_status()
        content_type = response.headers.get("content-type", "").lower()
        if "text/html" in content_type or "application/json" in content_type:
            raise ValueError("附件返回的是网页或错误信息")
        if int(response.headers.get("content-length") or 0) > limit:
            raise ValueError("附件超过大小上限")
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_name(destination.name + ".part")
        size = 0
        try:
            with temporary.open("wb") as out:
                for chunk in response.iter_content(64 * 1024):
                    if not size and chunk.lstrip().lower().startswith((b"<!doctype html", b"<html", b"<?xml")):
                        raise ValueError("附件返回的是网页或访问挑战")
                    size += len(chunk)
                    if size > limit:
                        raise ValueError("附件超过大小上限")
                    out.write(chunk)
            if not size:
                raise ValueError("附件为空")
            temporary.replace(destination)
        finally:
            temporary.unlink(missing_ok=True)
        return size
    finally:
        response.close()


def archive_source(source, client: HttpClient, target: date, root: Path,
                   remaining_bytes: int) -> tuple[dict, int]:
    scraper_class = get_scraper_class(source.name)
    if not issubclass(scraper_class, GovernmentAnnouncementScraper):
        raise ValueError(f"非部委公告渠道: {source.name}")
    scraper = scraper_class(client, source)
    parser = scraper.parser_type()
    report = {"source": source.name, "status": "ok", "listing_count": 0, "notices": [], "errors": []}
    used = 0
    try:
        items = scraper._listing_items(parser)
    except (ContractViolation, ValueError) as exc:
        report["status"] = "listing_failed"
        report["errors"].append(str(exc))
        return report, 0
    report["listing_count"] = len(items)
    if not items:
        reason = getattr(client, "last_failure_reason", "")
        report["status"] = "listing_failed" if reason else "listing_empty"
        if reason:
            report["errors"].append(reason)
    selected = [item for item in items if item.platform_published_at == target]
    for item in selected[:20]:
        digest = hashlib.sha256(item.url.encode()).hexdigest()[:10]
        relative_notice = Path(safe_name(source.name)) / f"{safe_name(item.title)}_{digest}"
        folder = root / "政策正文" / relative_notice
        attachment_folder = Path("附件") / relative_notice
        folder.mkdir(parents=True, exist_ok=True)
        notice = {"title": item.title, "published_at": target.isoformat(), "url": item.url,
                  "folder": str(folder.relative_to(root)), "attachment_folder": str(attachment_folder),
                  "content_status": "metadata_only", "attachments": [], "errors": []}
        if parser.fetch_detail:
            result = client.get(item.url, allow_non_html=False, strict_robots=True)
            if result:
                try:
                    article = parser.parse_detail(result.text, result.url)
                    (folder / "正文.txt").write_text(article.content + "\n", encoding="utf-8")
                    notice["content_status"] = "full_text"
                    links = attachment_links(parser, result.text, result.url)
                    for index, link in enumerate(links):
                        record = dict(link)
                        record["status"] = "skipped"
                        if index >= MAX_ATTACHMENTS_PER_NOTICE:
                            record["reason"] = "超过单篇附件数量上限"
                        else:
                            filename = f"{safe_name(item.title, max_length=80)}_附件{index + 1}{link['extension']}"
                            relative = attachment_folder / filename
                            try:
                                size = fetch_attachment(client, parser, link["url"], root / relative,
                                                        remaining_bytes - used)
                                used += size
                                record.update(status="downloaded", file=str(relative), bytes=size)
                            except Exception as exc:  # Isolate one file from the notice.
                                record["reason"] = f"{type(exc).__name__}: {exc}"
                        notice["attachments"].append(record)
                except ContractViolation as exc:
                    notice["errors"].append(f"正文校验失败: {exc}")
            else:
                notice["errors"].append(f"详情请求失败: {client.last_failure_reason}")
        else:
            notice["errors"].append("此渠道详情尚未通过生产校验，仅归档标题、日期和原文链接")
        (folder / "公告.json").write_text(json.dumps(notice, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        report["notices"].append(notice)
    if any(notice["errors"] or any(item["status"] != "downloaded" for item in notice["attachments"])
           for notice in report["notices"]):
        report["status"] = "partial"
    return report, used


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="单独抓取并归档部委通知、公告及附件")
    parser.add_argument("--sources", type=Path, default=Path("sources.xlsx"))
    parser.add_argument("--target-date", type=date.fromisoformat,
                        default=datetime.now(ZoneInfo(DEFAULT_TIMEZONE)).date() - timedelta(days=1))
    parser.add_argument("--output-dir", type=Path, default=Path("data/government_announcements"))
    parser.add_argument("--only-source", action="append")
    args = parser.parse_args(argv)
    root = args.output_dir / args.target_date.isoformat()
    selected = [s for s in load_sources(args.sources)
                if issubclass(get_scraper_class(s.name), GovernmentAnnouncementScraper)
                and (not args.only_source or s.name in args.only_source)]
    client = HttpClient(sleep_seconds=1.5, respect_robots=True)
    reports, total = [], 0
    for source in selected:
        try:
            report, used = archive_source(source, client, args.target_date, root, MAX_RUN_BYTES - total)
            reports.append(report)
            total += used
        except Exception as exc:
            logging.exception("Government archive failed: %s", source.name)
            reports.append({"source": source.name, "status": "failed", "errors": [str(exc)], "notices": []})
    root.mkdir(parents=True, exist_ok=True)
    index = {"target_date": args.target_date.isoformat(), "generated_at": datetime.now(ZoneInfo(DEFAULT_TIMEZONE)).isoformat(),
             "attachment_bytes": total, "sources": reports}
    (root / "索引.json").write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with (root / "国内政策清单.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=("渠道", "发布日期", "公告名称", "原文链接", "正文状态", "公告文件夹", "附件文件夹", "附件下载", "附件状态"))
        writer.writeheader()
        for report in reports:
            for notice in report.get("notices", []):
                downloaded = [item["file"]
                              for item in notice["attachments"] if item["status"] == "downloaded"]
                writer.writerow({"渠道": report["source"], "发布日期": notice["published_at"],
                                 "公告名称": notice["title"], "原文链接": notice["url"],
                                 "正文状态": notice["content_status"], "公告文件夹": notice["folder"],
                                 "附件文件夹": notice["attachment_folder"],
                                 "附件下载": "; ".join(downloaded),
                                 "附件状态": "; ".join(item["status"] for item in notice["attachments"])})
    print(root / "索引.json")
    return 0 if all(r["status"] == "ok" for r in reports) else 1


if __name__ == "__main__":
    raise SystemExit(main())
