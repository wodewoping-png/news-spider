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
import shutil
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse
from urllib.robotparser import RobotFileParser
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

from candidate_sources.government_announcements.base import ContractViolation
from candidate_sources.government_announcements.curated_policy import CuratedPolicyListingScraper, load_policy_sites
from candidate_sources.government_announcements.gov_cn import (
    GovCnPolicyDocumentsScraper,
    GovCnPolicyInterpretationsScraper,
)
from candidate_sources.government_announcements.scrapers import (
    GovernmentDocumentScraper,
    MiitPublicNoticesScraper,
    NeaDocumentScraper,
    StaticMinistryScraper,
)
from .date_utils import DEFAULT_TIMEZONE
from .http_client import BROWSER_USER_AGENT, HttpClient, valid_robots_text
from .load_sources import Source, load_sources
from .scrapers.government_announcements import GovernmentAnnouncementScraper
from .scrapers import get_scraper_class

EXTENSIONS = frozenset({".pdf", ".doc", ".docx", ".xls", ".xlsx", ".wps", ".zip", ".rar"})
# Government standards and consultation files can exceed 8 MiB. Keep a
# per-file ceiling below GitHub's individual-file limit while retaining the
# separate 50 MiB cap for the whole daily run.
MAX_ATTACHMENT_BYTES = 16 * 1024 * 1024
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
        else (parser.body_selector,) if isinstance(parser, GovCnPolicyDocumentsScraper)
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


def cleanup_legacy_notice(root: Path, relative_notice: Path) -> None:
    """Remove an old layout copy only when the new layout retains its contents."""
    old = root / relative_notice
    current = root / "政策正文" / relative_notice
    if not old.is_dir() or old.is_symlink():
        return
    for path in old.rglob("*"):
        if path.is_symlink():
            return
        if not path.is_file():
            continue
        relative = path.relative_to(old)
        if relative == Path("公告.json"):
            if not (current / relative).is_file():
                return
        elif relative == Path("正文.txt"):
            counterpart = current / relative
            if not counterpart.is_file() or path.read_bytes() != counterpart.read_bytes():
                return
        elif relative.parts[0] == "附件":
            counterpart = root / "附件" / relative_notice / Path(*relative.parts[1:])
            if not counterpart.is_file() or path.read_bytes() != counterpart.read_bytes():
                return
        else:
            return
    shutil.rmtree(old)
    try:
        old.parent.rmdir()
    except OSError:
        pass


def cleanup_legacy_csv(root: Path) -> None:
    old = root / "公告清单.csv"
    new = root / "国内政策清单.csv"
    if not old.is_file():
        return
    def entries(path: Path) -> set[tuple[str, str, str]]:
        with path.open(encoding="utf-8-sig", newline="") as handle:
            return {(row["渠道"], row["发布日期"], row["原文链接"])
                    for row in csv.DictReader(handle)}
    try:
        if entries(old) <= entries(new):
            old.unlink()
    except (KeyError, UnicodeError, csv.Error):
        pass


def check_pending_policy_sites(sites: list[dict]) -> dict[str, dict]:
    """Daily robots health check only; never promote an unreviewed column."""
    candidates = [site for site in sites if site["status"] in {"pending", "hold"}]

    def check(site: dict) -> tuple[str, dict]:
        domain = site["official_domain"]
        target = next((c["url"] for c in site["columns"] if c["url"]), f"https://www.{domain}/")
        host = urlparse(target).hostname or ""
        if host != domain and not host.endswith(f".{domain}"):
            return site["agency"], {"robots_http": None, "check": "unverified_host"}
        url = f"https://{host}/robots.txt"
        try:
            response = requests.get(url, headers={"User-Agent": BROWSER_USER_AGENT}, timeout=6)
            status = response.status_code
            if status not in {200, 404}:
                state = "robots_unavailable"
            else:
                parser = RobotFileParser()
                if status == 200 and not valid_robots_text(response):
                    state = "robots_unavailable"
                else:
                    parser.parse(response.text.splitlines() if status == 200 else [])
                    state = "allowed_needs_column_review" if parser.can_fetch(BROWSER_USER_AGENT, target) else "robots_disallowed"
            return site["agency"], {"robots_http": status, "check": state}
        except requests.RequestException as exc:
            return site["agency"], {"robots_http": None, "check": type(exc).__name__}

    with ThreadPoolExecutor(max_workers=6) as pool:
        return dict(pool.map(check, candidates))


def archive_bucket(source_name: str) -> tuple[str, str]:
    """Keep statistical releases and accident reports out of the policy list."""
    if source_name.startswith("国家统计局—"):
        return "统计数据清单.csv", "统计数据"
    if source_name == "国家矿山安全监察局—事故查处":
        return "事故通报清单.csv", "事故通报"
    return "国内政策清单.csv", "政策正文"


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
        report["status"] = ("robots_hold" if reason == "blocked by robots.txt" else
                            "listing_failed" if reason else "listing_empty")
        if reason:
            report["errors"].append(reason)
    selected = [item for item in items if item.platform_published_at == target]
    for item in selected[:20]:
        digest = hashlib.sha256(item.url.encode()).hexdigest()[:10]
        relative_notice = Path(safe_name(source.name)) / f"{safe_name(item.title)}_{digest}"
        folder = root / archive_bucket(source.name)[1] / relative_notice
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
            if not isinstance(parser, (GovCnPolicyInterpretationsScraper, CuratedPolicyListingScraper)):
                notice["errors"].append("此渠道详情尚未通过生产校验，仅归档标题、日期和原文链接")
        (folder / "公告.json").write_text(json.dumps(notice, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        report["notices"].append(notice)
        cleanup_legacy_notice(root, relative_notice)
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
    parser.add_argument("--check-pending", action="store_true", help="复查待验证机构的 robots 状态")
    args = parser.parse_args(argv)
    root = args.output_dir / args.target_date.isoformat()
    selected = [s for s in load_sources(args.sources)
                if issubclass(get_scraper_class(s.name), GovernmentAnnouncementScraper)
                and (not args.only_source or s.name in args.only_source)]
    existing = {source.name for source in selected}
    policy_sites = load_policy_sites()
    for site in policy_sites:
        for column in site["columns"]:
            if column["status"] != "active":
                continue
            name = f"{site['agency']}—{column['label']}"
            if name in existing or (args.only_source and name not in args.only_source):
                continue
            selected.append(Source(name, "官方政策", "政策", column["category"], "不定期",
                                   "官方栏目发布日期及原文链接", "列表已核验，正文待核验", column["url"]))
            existing.add(name)
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
    attachment_root = root / "附件"
    attachment_root.mkdir(exist_ok=True)
    (attachment_root / "说明.txt").write_text(
        "附件按渠道/公告名称_哈希存放；当天没有下载成功的附件时，此目录仅有本说明。\n",
        encoding="utf-8",
    )
    pending_health = check_pending_policy_sites(policy_sites) if args.check_pending else {}
    index = {"target_date": args.target_date.isoformat(), "generated_at": datetime.now(ZoneInfo(DEFAULT_TIMEZONE)).isoformat(),
             "attachment_bytes": total, "sources": reports,
             "policy_site_coverage": [{"agency": site["agency"], "status": site["status"],
                                       "reason": site["reason"],
                                       "last_robots_check": pending_health.get(site["agency"]),
                                       "channels": [{"label": c["label"], "url": c["url"], "status": c["status"]}
                                                    for c in site["columns"]]}
                                      for site in policy_sites]}
    (root / "索引.json").write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    fields = ("渠道", "发布日期", "公告名称", "原文链接", "正文状态", "公告文件夹", "附件文件夹", "附件下载", "附件状态")
    for filename in ("国内政策清单.csv", "统计数据清单.csv", "事故通报清单.csv"):
        with (root / filename).open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            for report in reports:
                if archive_bucket(report["source"])[0] != filename:
                    continue
                for notice in report.get("notices", []):
                    downloaded = [item["file"] for item in notice["attachments"] if item["status"] == "downloaded"]
                    writer.writerow({"渠道": report["source"], "发布日期": notice["published_at"],
                                     "公告名称": notice["title"], "原文链接": notice["url"],
                                     "正文状态": notice["content_status"], "公告文件夹": notice["folder"],
                                     "附件文件夹": notice["attachment_folder"],
                                     "附件下载": "; ".join(downloaded),
                                     "附件状态": "; ".join(item["status"] for item in notice["attachments"])})
    cleanup_legacy_csv(root)
    print(root / "索引.json")
    return 0 if all(r["status"] in {"ok", "robots_hold"} for r in reports) else 1


if __name__ == "__main__":
    raise SystemExit(main())
