from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import date, datetime, timedelta
from pathlib import Path
from statistics import median
from zoneinfo import ZoneInfo

from .audit import run_daily_audit
from .channel_ops import reconcile
from .content_quality import PUBLIC_RSS_SUMMARY_POLICY, is_usable_article
from .date_utils import DEFAULT_TIMEZONE, article_date
from .industry_classifier import ZAIIndustryClassifier, classify_jsonl
from .notifications import NotificationError, send_dingtalk
from .storage import export_csv, upsert_jsonl


SOURCE_NAME = "the information"
MANIFEST_VERSION = 2
SUPPORTED_MANIFEST_VERSIONS = {1, MANIFEST_VERSION}
PUBLIC_CAPTURE_MODES = {
    "rss_public",
    "rss_public_fallback",
    "rss_public_reader",
}


class LocalCaptureError(RuntimeError):
    pass


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    records: list[dict] = []
    for line_number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError as exc:
            raise LocalCaptureError(
                f"invalid JSONL at {path}:{line_number}"
            ) from exc
        if not isinstance(item, dict):
            raise LocalCaptureError(f"non-object JSONL record at {path}:{line_number}")
        records.append(item)
    return records


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _write_jsonl(path: Path, records: list[dict]) -> bytes:
    payload = "".join(
        json.dumps(item, ensure_ascii=False, separators=(",", ":")) + "\n"
        for item in records
    ).encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(payload)
    temporary.replace(path)
    return payload


def _validate_records(
    records: list[dict],
    target_date: date,
    *,
    require_full_text: bool,
    require_public_summary: bool = False,
) -> None:
    for index, item in enumerate(records, start=1):
        source = str(item.get("source_name") or "").strip().lower()
        if source != SOURCE_NAME:
            raise LocalCaptureError(
                f"record {index} belongs to {source or 'an empty source'}, not {SOURCE_NAME}"
            )
        if article_date(item, DEFAULT_TIMEZONE) != target_date:
            raise LocalCaptureError(
                f"record {index} is not published on {target_date.isoformat()}"
            )
        if not str(item.get("url") or "").strip():
            raise LocalCaptureError(f"record {index} has no URL")
        if require_full_text and str(item.get("content_status") or "").lower() != "full":
            raise LocalCaptureError(f"record {index} is not verified as full text")
        if require_public_summary and (
            str(item.get("content_policy") or "").strip().lower()
            != PUBLIC_RSS_SUMMARY_POLICY
            or not is_usable_article(item)
        ):
            raise LocalCaptureError(
                f"record {index} is not a valid public RSS summary"
            )


def package_capture(
    articles_path: Path,
    health_path: Path,
    output_dir: Path,
    target_date: date,
) -> tuple[Path, Path, dict]:
    records = _read_jsonl(articles_path)
    try:
        health = json.loads(health_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise LocalCaptureError(f"unable to read capture health: {health_path}") from exc
    if str(health.get("target_date") or "") != target_date.isoformat():
        raise LocalCaptureError("capture health target date does not match requested date")
    source_health = next(
        (
            row
            for row in health.get("sources", [])
            if str(row.get("source") or "").strip().lower() == SOURCE_NAME
        ),
        None,
    )
    if source_health is None:
        raise LocalCaptureError("capture health has no The Information record")
    crawl_mode = str(source_health.get("crawl_mode") or "").lower()
    status = str(source_health.get("status") or "").lower()
    is_authenticated = crawl_mode == "rss_authenticated"
    is_public = crawl_mode in PUBLIC_CAPTURE_MODES
    if not (is_authenticated or is_public) or status == "failed":
        raise LocalCaptureError(
            "local capture did not use a supported The Information feed: "
            f"status={status or '-'}, crawl_mode={crawl_mode or '-'}"
        )
    _validate_records(
        records,
        target_date,
        require_full_text=is_authenticated,
        require_public_summary=is_public,
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    fragment_path = output_dir / f"{target_date.isoformat()}.jsonl"
    manifest_path = output_dir / f"{target_date.isoformat()}.manifest.json"
    fragment_payload = _write_jsonl(fragment_path, records)
    manifest = {
        "version": MANIFEST_VERSION,
        "source": SOURCE_NAME,
        "target_date": target_date.isoformat(),
        "generated_at": datetime.now(ZoneInfo(DEFAULT_TIMEZONE)).isoformat(),
        "fetch_succeeded": True,
        "crawl_mode": crawl_mode,
        "content_policy": (
            "subscriber_full_text" if is_authenticated else PUBLIC_RSS_SUMMARY_POLICY
        ),
        "capture_status": status,
        "article_count": len(records),
        "candidates_seen": int(source_health.get("candidates_seen", len(records))),
        "usable_articles": sum(is_usable_article(item) for item in records),
        "full_articles": sum(
            str(item.get("content_status") or "").lower() == "full" for item in records
        ),
        "public_summary_articles": sum(
            str(item.get("content_policy") or "").lower()
            == PUBLIC_RSS_SUMMARY_POLICY
            for item in records
        ),
        "fragment_sha256": hashlib.sha256(fragment_payload).hexdigest(),
    }
    _write_json(manifest_path, manifest)
    return fragment_path, manifest_path, manifest


def load_verified_fragment(
    fragment_path: Path,
    manifest_path: Path,
    target_date: date,
) -> tuple[list[dict], dict]:
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise LocalCaptureError(f"unable to read manifest: {manifest_path}") from exc
    version = manifest.get("version")
    if version not in SUPPORTED_MANIFEST_VERSIONS:
        raise LocalCaptureError("unsupported local capture manifest version")
    if str(manifest.get("source") or "").strip().lower() != SOURCE_NAME:
        raise LocalCaptureError("manifest source is not The Information")
    if str(manifest.get("target_date") or "") != target_date.isoformat():
        raise LocalCaptureError("manifest target date does not match requested date")
    if manifest.get("fetch_succeeded") is not True:
        raise LocalCaptureError("manifest reports an unsuccessful local capture")
    crawl_mode = str(manifest.get("crawl_mode") or "").lower()
    is_authenticated = crawl_mode == "rss_authenticated"
    is_public = version >= 2 and crawl_mode in PUBLIC_CAPTURE_MODES
    if not (is_authenticated or is_public):
        raise LocalCaptureError("manifest was not produced from a supported feed")

    try:
        fragment_payload = fragment_path.read_bytes()
    except OSError as exc:
        raise LocalCaptureError(f"unable to read fragment: {fragment_path}") from exc
    actual_hash = hashlib.sha256(fragment_payload).hexdigest()
    if actual_hash != str(manifest.get("fragment_sha256") or ""):
        raise LocalCaptureError("fragment checksum does not match manifest")
    records = _read_jsonl(fragment_path)
    _validate_records(
        records,
        target_date,
        require_full_text=is_authenticated,
        require_public_summary=is_public,
    )
    if int(manifest.get("article_count", -1)) != len(records):
        raise LocalCaptureError("fragment article count does not match manifest")
    return records, manifest


def ingest_capture(
    fragment_path: Path,
    manifest_path: Path,
    output_path: Path,
    csv_path: Path,
    logs_dir: Path,
    target_date: date,
    *,
    classify: bool = True,
) -> dict:
    records, manifest = load_verified_fragment(
        fragment_path, manifest_path, target_date
    )
    added, refreshed = upsert_jsonl(output_path, records)
    classified = 0
    if classify:
        classifier = ZAIIndustryClassifier.from_environment()
        if classifier is not None:
            classification = classify_jsonl(
                classifier,
                output_path,
                target_date=target_date,
                timezone_name=DEFAULT_TIMEZONE,
            )
            classified = int(classification.get("classified", 0))
    export_csv(output_path, csv_path, target_date, DEFAULT_TIMEZONE)

    content_lengths = [len(str(item.get("content") or "").strip()) for item in records]
    public_capture = str(manifest.get("crawl_mode") or "").lower() in PUBLIC_CAPTURE_MODES
    health_record = {
        "source": SOURCE_NAME,
        "frequency": "实时",
        "status": "healthy" if records else "idle",
        "reason": "" if records else "local feed had no target-date entries",
        "crawl_mode": (
            "local_public_rss_ingest" if public_capture else "local_authenticated_ingest"
        ),
        "content_policy": manifest.get("content_policy", "subscriber_full_text"),
        "candidates_seen": int(manifest.get("candidates_seen", len(records))),
        "pages_fetched": len(records),
        "date_filtered_candidates": 0,
        "undated_candidates": 0,
        "new_articles": added,
        "refreshed_articles": refreshed,
        "usable_articles": len(records),
        "incomplete_articles": 0,
        "content_issues": "",
        "short_articles": sum(length < 500 for length in content_lengths),
        "min_content_chars": 500,
        "content_chars_min": min(content_lengths, default=0),
        "content_chars_median": (
            int(median(content_lengths)) if content_lengths else 0
        ),
        "content_chars_max": max(content_lengths, default=0),
    }
    health_payload = {
        "generated_at": datetime.now(ZoneInfo(DEFAULT_TIMEZONE)).isoformat(),
        "target_date": target_date.isoformat(),
        "sources": [health_record],
    }
    health_path = logs_dir / "local-the-information-health.json"
    _write_json(health_path, health_payload)
    run_daily_audit(
        output_path,
        logs_dir,
        target_date,
        [health_record],
        timezone_name=DEFAULT_TIMEZONE,
    )
    reconcile(logs_dir, health_path=health_path)
    receipt = {
        "source": SOURCE_NAME,
        "target_date": target_date.isoformat(),
        "content_policy": manifest.get("content_policy", "subscriber_full_text"),
        "fragment_sha256": manifest["fragment_sha256"],
        "article_count": len(records),
        "added": added,
        "refreshed": refreshed,
        "classified": classified,
        "csv": str(csv_path),
        "ingested_at": datetime.now(ZoneInfo(DEFAULT_TIMEZONE)).isoformat(),
    }
    _write_json(logs_dir / "local-the-information-ingest.json", receipt)
    return receipt


def default_target_date() -> date:
    return datetime.now(ZoneInfo(DEFAULT_TIMEZONE)).date() - timedelta(days=1)


def notify_capture_problem(target_date: date, kind: str) -> bool:
    webhook = os.environ.get("DINGTALK_WEBHOOK", "").strip()
    if not webhook:
        return False
    keyword = (
        os.environ.get("DINGTALK_KEYWORD", "").strip() or "渠道抓取告警"
    )
    reason = {
        "missing": "截止时间仍未收到本地日分片",
        "invalid": "本地日分片校验或汇总失败",
        "online_recovery_failed": "普通 GitHub Runner 和 macOS 备用 Runner 均未取得鉴权订阅源全文",
    }.get(kind, "The Information 抓取处理失败")
    online_failure = kind == "online_recovery_failed"
    heading = "在线全文抓取异常" if online_failure else "本地抓取异常"
    suggestion = (
        "检查订阅账号权限、GitHub Actions Secrets、订阅 Feed 可用性和运行日志；其他渠道无需停止。"
        if online_failure
        else "检查本地计划任务、订阅 RSS 访问及 inbox 分支推送。"
    )
    run_url = os.environ.get("ALERT_RUN_URL", "").strip()
    markdown = "\n".join(
        [
            f"## {keyword}",
            "",
            f"### {heading}｜The Information",
            f"- 缺失日期：{target_date.isoformat()}",
            f"- 诊断：{reason}",
            f"- 处理建议：{suggestion}",
            "",
            f"[查看 GitHub Actions 运行详情]({run_url})" if run_url else "",
        ]
    )
    send_dingtalk(
        webhook,
        secret=os.environ.get("DINGTALK_SECRET", "").strip(),
        title=f"{keyword}：The Information {heading}",
        markdown=markdown,
    )
    return True


def _target(value: str) -> date:
    return date.fromisoformat(value) if value else default_target_date()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Package and ingest local The Information feed captures"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    package = subparsers.add_parser("package")
    package.add_argument("--articles", type=Path, required=True)
    package.add_argument("--health", type=Path, required=True)
    package.add_argument("--output-dir", type=Path, required=True)
    package.add_argument("--target-date", default="")

    ingest = subparsers.add_parser("ingest")
    ingest.add_argument("--fragment", type=Path, required=True)
    ingest.add_argument("--manifest", type=Path, required=True)
    ingest.add_argument("--output", type=Path, default=Path("data/articles.jsonl"))
    ingest.add_argument("--csv", type=Path)
    ingest.add_argument("--logs", type=Path, default=Path("logs"))
    ingest.add_argument("--target-date", default="")
    ingest.add_argument("--skip-industry-classification", action="store_true")

    notify = subparsers.add_parser("notify")
    notify.add_argument("--target-date", default="")
    notify.add_argument(
        "--kind",
        choices=("missing", "invalid", "online_recovery_failed"),
        required=True,
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    target_date = _target(args.target_date)
    try:
        if args.command == "package":
            fragment, manifest, payload = package_capture(
                args.articles,
                args.health,
                args.output_dir,
                target_date,
            )
            print(
                json.dumps(
                    {
                        "fragment": str(fragment),
                        "manifest": str(manifest),
                        **payload,
                    },
                    ensure_ascii=False,
                )
            )
            return 0
        if args.command == "ingest":
            csv_path = args.csv or Path("data") / (
                f"articles-{(target_date + timedelta(days=1)).isoformat()}.csv"
            )
            receipt = ingest_capture(
                args.fragment,
                args.manifest,
                args.output,
                csv_path,
                args.logs,
                target_date,
                classify=not args.skip_industry_classification,
            )
            print(json.dumps(receipt, ensure_ascii=False))
            return 0
        sent = notify_capture_problem(target_date, args.kind)
        print("DingTalk notification sent." if sent else "DingTalk webhook is not configured.")
        return 0
    except (LocalCaptureError, NotificationError, ValueError, OSError) as exc:
        print(f"The Information local ingest failed: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
