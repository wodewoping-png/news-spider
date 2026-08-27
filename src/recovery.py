from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Callable, Iterable
from zoneinfo import ZoneInfo

from .content_quality import FULL_CONTENT_STATUS, assess_content
from .date_utils import DEFAULT_TIMEZONE, article_date


QUEUE_VERSION = 1
OPEN_STATUSES = {"pending_confirmation", "confirmed", "recovering", "recovery_failed"}
RECOVERABLE_CRAWL_STATUSES = {"zero", "failed", "degraded"}


def _now(timezone_name: str = DEFAULT_TIMEZONE) -> str:
    return datetime.now(ZoneInfo(timezone_name)).isoformat()


def _incident_id(source: str, day: str) -> str:
    return f"{day}::{source}"


def load_queue(path: Path) -> dict:
    if not path.exists():
        return {"version": QUEUE_VERSION, "updated_at": "", "incidents": []}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise ValueError(f"恢复队列无法读取，已停止以避免覆盖：{path}") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("incidents"), list):
        raise ValueError(f"恢复队列结构无效，已停止以避免覆盖：{path}")
    payload.setdefault("version", QUEUE_VERSION)
    payload.setdefault("updated_at", "")
    return payload


def save_queue(path: Path, payload: dict, *, updated_at: str | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload["version"] = QUEUE_VERSION
    payload["updated_at"] = updated_at or _now()
    payload["incidents"] = sorted(
        payload.get("incidents", []),
        key=lambda item: (str(item.get("date")), str(item.get("source"))),
    )
    temporary_path = path.with_suffix(path.suffix + ".tmp")
    temporary_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary_path.replace(path)


def diagnose_incident(row: dict, health: dict | None = None) -> tuple[str, str]:
    health = health or {}
    crawl_status = str(row.get("crawl_status") or health.get("status") or "")
    technical_reason = str(health.get("reason") or row.get("anomaly_reason") or "")
    lowered = technical_reason.lower()
    candidates = _as_int(row.get("candidates_seen", health.get("candidates_seen")))
    pages = _as_int(row.get("pages_fetched", health.get("pages_fetched")))
    date_filtered = _as_int(
        row.get(
            "date_filtered_candidates",
            health.get("date_filtered_candidates"),
        )
    )
    undated = _as_int(
        row.get("undated_candidates", health.get("undated_candidates"))
    )
    candidate_date_min = str(
        row.get("candidate_date_min") or health.get("candidate_date_min") or ""
    )
    candidate_date_max = str(
        row.get("candidate_date_max") or health.get("candidate_date_max") or ""
    )

    if crawl_status == "degraded":
        incomplete = _as_int(
            row.get("incomplete_articles", health.get("incomplete_articles"))
        )
        issues = str(health.get("content_issues") or "").strip()
        detail = f"；类型：{issues}" if issues else ""
        return (
            "content_quality_degraded",
            f"检测到 {incomplete or 1} 篇正文不完整或混入页面模板/导航内容{detail}，"
            "请检查正文选择器和内容质量规则",
        )

    if crawl_status == "failed":
        patterns = (
            (
                ("missing run record",),
                "missing_run_record",
                "该日期没有渠道抓取记录，检查工作流延迟、取消或进程级失败",
            ),
            (
                ("401", "unauthorized", "authentication", "authenticated subscriber"),
                "authentication_failed",
                "认证失败或订阅 Feed 不可用，检查账号权限和 GitHub Actions Secrets",
            ),
            (("403", "forbidden"), "access_denied", "站点拒绝访问（HTTP 403），检查反爬、请求头或访问权限"),
            (("404", "not found"), "entry_not_found", "抓取入口返回 HTTP 404，检查渠道 URL 或 RSS 地址"),
            (("429", "too many requests"), "rate_limited", "请求频率受限（HTTP 429），降低频率或增加重试退避"),
            (
                ("500", "502", "503", "504", "service unavailable", "bad gateway"),
                "upstream_unavailable",
                "站点服务暂时不可用（HTTP 5xx），保留缺口并在站点恢复后验证",
            ),
            (("timeout", "timed out"), "timeout", "站点请求超时，检查可用性并调整超时/重试策略"),
            (("ssl", "certificate"), "tls_error", "TLS/证书校验失败，检查站点证书或网络链路"),
            (("robots",), "robots_blocked", "robots.txt 禁止抓取，需确认合规抓取入口"),
            (("name resolution", "dns"), "dns_error", "域名解析失败，检查域名是否失效或网络 DNS"),
            (("parse", "selector"), "parser_error", "页面解析失败，检查列表或正文选择器是否已变更"),
        )
        for needles, code, diagnosis in patterns:
            if any(needle in lowered for needle in needles):
                return code, diagnosis
        return "fetch_failed", f"抓取任务异常退出：{technical_reason or '未记录底层错误'}"

    if candidates == 0:
        return (
            "no_candidates",
            "未发现任何候选文章，优先检查列表/RSS 地址、页面结构、选择器或站点可达性",
        )
    if pages == 0:
        if date_filtered and date_filtered + undated >= candidates and not undated:
            date_range = candidate_date_max
            if candidate_date_min and candidate_date_min != candidate_date_max:
                date_range = f"{candidate_date_min} 至 {candidate_date_max}"
            return (
                "non_target_date_candidates",
                f"候选发布日期均为 {date_range or '其他日期'}，"
                "与目标日期不符，已在抓取正文前正确过滤；站点当日可能无更新",
            )
        return (
            "candidates_filtered",
            "发现候选但未抓取正文，可能全部被日期过滤、URL 去重或候选日期解析错误",
        )
    return (
        "no_target_articles",
        "已访问候选正文但目标日期仍为零，检查发布日期解析、正文解析及站点是否确实无更新",
    )


def sync_recovery_queue(
    path: Path,
    current_rows: Iterable[dict],
    health_records: Iterable[dict],
    *,
    generated_at: str | None = None,
) -> dict:
    timestamp = generated_at or _now()
    payload = load_queue(path)
    incidents = {
        str(item.get("id") or _incident_id(str(item.get("source")), str(item.get("date")))): item
        for item in payload["incidents"]
    }
    health_by_source = {
        str(record.get("source") or ""): record for record in health_records
    }

    for row in current_rows:
        source = str(row.get("source") or "")
        day = str(row.get("date") or "")
        if not source or not day:
            continue
        incident_id = _incident_id(source, day)
        count = _as_int(row.get("article_count"))
        expected_daily = str(row.get("expected_daily")).lower() == "true"
        crawl_status = str(row.get("crawl_status") or "")
        existing = incidents.get(incident_id)

        if count > 0 and crawl_status != "degraded":
            if existing and existing.get("status") in OPEN_STATUSES:
                existing.update(
                    {
                        "status": "recovered",
                        "recovered_articles": count,
                        "recovered_at": timestamp,
                        "updated_at": timestamp,
                    }
                )
            continue
        if crawl_status == "idle":
            if existing and existing.get("status") in OPEN_STATUSES:
                health = health_by_source.get(source, {})
                existing.update(
                    {
                        "status": "ignored",
                        "confirmation_note": str(
                            health.get("reason")
                            or "候选发布日期均不属于目标日期，确认当日无新闻"
                        ),
                        "ignored_at": timestamp,
                        "updated_at": timestamp,
                    }
                )
            continue
        if crawl_status not in RECOVERABLE_CRAWL_STATUSES:
            continue
        if crawl_status != "degraded" and not expected_daily:
            continue

        health = health_by_source.get(source, {})
        diagnosis_code, diagnosis = diagnose_incident(row, health)
        if existing is None:
            existing = {
                "id": incident_id,
                "source": source,
                "date": day,
                "frequency": str(row.get("frequency") or ""),
                "status": "pending_confirmation",
                "detected_at": timestamp,
                "confirmed_at": "",
                "confirmation_note": "",
                "attempts": 0,
                "last_attempt_at": "",
                "recovered_articles": 0,
                "recovered_at": "",
            }
            incidents[incident_id] = existing
        existing.update(
            {
                "anomaly_level": str(row.get("anomaly_level") or "warning"),
                "anomaly_codes": str(row.get("anomaly_codes") or ""),
                "crawl_status": crawl_status,
                "crawl_mode": str(health.get("crawl_mode") or ""),
                "candidates_seen": _as_int(
                    row.get("candidates_seen", health.get("candidates_seen"))
                ),
                "pages_fetched": _as_int(
                    row.get("pages_fetched", health.get("pages_fetched"))
                ),
                "date_filtered_candidates": _as_int(
                    row.get(
                        "date_filtered_candidates",
                        health.get("date_filtered_candidates"),
                    )
                ),
                "undated_candidates": _as_int(
                    row.get(
                        "undated_candidates",
                        health.get("undated_candidates"),
                    )
                ),
                "candidate_date_min": str(
                    row.get("candidate_date_min")
                    or health.get("candidate_date_min")
                    or ""
                ),
                "candidate_date_max": str(
                    row.get("candidate_date_max")
                    or health.get("candidate_date_max")
                    or ""
                ),
                "diagnosis_code": diagnosis_code,
                "diagnosis": diagnosis,
                "technical_reason": str(
                    health.get("reason") or row.get("anomaly_reason") or ""
                ),
                "incomplete_articles": _as_int(
                    row.get(
                        "incomplete_articles",
                        health.get("incomplete_articles"),
                    )
                ),
                "content_issues": str(health.get("content_issues") or ""),
                "error_type": str(health.get("error_type") or ""),
                "failed_at": str(health.get("failed_at") or ""),
                "updated_at": timestamp,
            }
        )

    payload["incidents"] = list(incidents.values())
    save_queue(path, payload, updated_at=timestamp)
    return payload


def update_incidents(
    path: Path,
    source: str,
    action: str,
    *,
    dates: set[str] | None = None,
    note: str = "",
    timestamp: str | None = None,
) -> list[dict]:
    payload = load_queue(path)
    changed: list[dict] = []
    now = timestamp or _now()
    for incident in payload["incidents"]:
        if str(incident.get("source")) != source:
            continue
        if dates and str(incident.get("date")) not in dates:
            continue
        status = str(incident.get("status"))
        if action == "confirm" and status in {"pending_confirmation", "recovery_failed"}:
            incident.update(
                {
                    "status": "confirmed",
                    "confirmed_at": now,
                    "confirmation_note": note,
                    "updated_at": now,
                }
            )
            changed.append(incident)
        elif action == "ignore" and status in OPEN_STATUSES:
            incident.update(
                {
                    "status": "ignored",
                    "confirmation_note": note,
                    "updated_at": now,
                }
            )
            changed.append(incident)
    save_queue(path, payload, updated_at=now)
    return changed


def auto_confirm_missing_run_incidents(
    path: Path,
    *,
    timestamp: str | None = None,
) -> list[dict]:
    """Confirm only system-detected missing-run gaps for automatic backfill."""
    payload = load_queue(path)
    now = timestamp or _now()
    changed: list[dict] = []
    for incident in payload["incidents"]:
        if (
            incident.get("status") == "pending_confirmation"
            and incident.get("diagnosis_code") == "missing_run_record"
        ):
            incident.update(
                {
                    "status": "confirmed",
                    "confirmed_at": now,
                    "confirmation_note": "系统检测到整日运行记录缺失，自动确认补抓",
                    "updated_at": now,
                }
            )
            changed.append(incident)
    if changed:
        save_queue(path, payload, updated_at=now)
    return changed


def count_articles(jsonl_path: Path, source: str, day: str) -> int:
    if not jsonl_path.exists():
        return 0
    count = 0
    with jsonl_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            published = article_date(item, DEFAULT_TIMEZONE)
            if (
                str(item.get("source_name") or "") == source
                and published
                and published.isoformat() == day
            ):
                count += 1
    return count


def count_usable_articles(jsonl_path: Path, source: str, day: str) -> int:
    if not jsonl_path.exists():
        return 0
    count = 0
    with jsonl_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            published = article_date(item, DEFAULT_TIMEZONE)
            if (
                str(item.get("source_name") or "") != source
                or not published
                or published.isoformat() != day
            ):
                continue
            status, _issue = assess_content(
                str(item.get("content") or ""),
                extraction_method=str(item.get("content_extraction") or ""),
            )
            if status == FULL_CONTENT_STATUS:
                count += 1
    return count


CommandRunner = Callable[[list[str]], int]


def _default_command_runner(command: list[str]) -> int:
    return subprocess.run(command, check=False).returncode


def run_confirmed_recoveries(
    queue_path: Path,
    *,
    sources_path: Path,
    output_path: Path,
    logs_dir: Path,
    limit_per_source: int = 100,
    candidate_limit: int = 500,
    command_runner: CommandRunner = _default_command_runner,
    timestamp: str | None = None,
) -> list[dict]:
    payload = load_queue(queue_path)
    now = timestamp or _now()
    processed: list[dict] = []
    for incident in payload["incidents"]:
        if incident.get("status") not in {"confirmed", "recovering"}:
            continue
        source = str(incident.get("source") or "")
        day = str(incident.get("date") or "")
        incident.update(
            {
                "status": "recovering",
                "attempts": _as_int(incident.get("attempts")) + 1,
                "last_attempt_at": now,
                "updated_at": now,
            }
        )
        save_queue(queue_path, payload, updated_at=now)
        command = [
            sys.executable,
            "-m",
            "src.main",
            "--sources",
            str(sources_path),
            "--output",
            str(output_path),
            "--logs",
            str(logs_dir),
            "--target-date",
            day,
            "--only-source",
            source,
            "--limit-per-source",
            str(limit_per_source),
            "--candidate-limit",
            str(candidate_limit),
            "--skip-audit",
        ]
        return_code = command_runner(command)
        recovered = count_articles(output_path, source, day)
        quality_recovery = (
            str(incident.get("diagnosis_code") or "")
            == "content_quality_degraded"
        )
        usable_recovered = count_usable_articles(output_path, source, day)
        recovery_count = usable_recovered if quality_recovery else recovered
        if return_code == 0 and recovery_count > 0:
            incident.update(
                {
                    "status": "recovered",
                    "recovered_articles": recovery_count,
                    "recovered_at": now,
                    "last_error": "",
                    "updated_at": now,
                }
            )
        else:
            reason = (
                _latest_health_reason(logs_dir / "channel-health.json", source)
                if return_code == 0
                else ""
            )
            incident.update(
                {
                    "status": "recovery_failed",
                    "last_error": reason
                    or (
                        f"补抓命令退出码为 {return_code}"
                        if return_code
                        else (
                            "补抓完成但正文仍不完整或包含页面模板噪声"
                            if quality_recovery
                            else "补抓完成但目标日期仍无文章"
                        )
                    ),
                    "updated_at": now,
                }
            )
        processed.append(incident)
        save_queue(queue_path, payload, updated_at=now)
    return processed


def _latest_health_reason(path: Path, source: str) -> str:
    if not path.exists():
        return ""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return ""
    for record in payload.get("sources", []):
        if str(record.get("source") or "") == source:
            return str(record.get("reason") or "")
    return ""


def _as_int(value: object) -> int:
    try:
        return int(float(str(value or 0)))
    except (TypeError, ValueError):
        return 0


def _print_incidents(incidents: Iterable[dict]) -> None:
    rows = list(incidents)
    if not rows:
        print("没有匹配的渠道恢复条目。")
        return
    for item in rows:
        print(
            f"[{item.get('status')}] {item.get('date')} | {item.get('source')} | "
            f"{item.get('diagnosis') or item.get('last_error') or '-'}"
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="渠道异常确认与历史缺口自动补抓")
    parser.add_argument(
        "--queue", type=Path, default=Path("logs/recovery-queue.json")
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="列出恢复队列")
    list_parser.add_argument(
        "--status",
        action="append",
        help="只显示指定状态，可重复；默认显示全部",
    )

    for action in ("confirm", "ignore"):
        action_parser = subparsers.add_parser(
            action, help="确认修复并允许补抓" if action == "confirm" else "确认无需补抓"
        )
        action_parser.add_argument("--source", required=True)
        action_parser.add_argument("--date", action="append")
        action_parser.add_argument("--note", default="")

    run_parser = subparsers.add_parser("run", help="执行所有已确认的补抓任务")
    run_parser.add_argument("--sources", type=Path, default=Path("sources.xlsx"))
    run_parser.add_argument("--output", type=Path, default=Path("data/articles.jsonl"))
    run_parser.add_argument("--logs", type=Path, default=Path("logs"))
    run_parser.add_argument("--limit-per-source", type=int, default=100)
    run_parser.add_argument("--candidate-limit", type=int, default=500)

    check_parser = subparsers.add_parser(
        "check", help="存在未确认或补抓失败条目时返回非零状态"
    )
    check_parser.add_argument(
        "--status",
        action="append",
        default=["pending_confirmation", "recovery_failed"],
    )
    check_parser.add_argument(
        "--warn-only",
        action="store_true",
        help="将待处理条目标记为 GitHub Actions warning，并始终返回成功",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.command == "list":
        payload = load_queue(args.queue)
        statuses = set(args.status or [])
        incidents = [
            item
            for item in payload["incidents"]
            if not statuses or item.get("status") in statuses
        ]
        _print_incidents(incidents)
        return 0
    if args.command in {"confirm", "ignore"}:
        changed = update_incidents(
            args.queue,
            args.source,
            args.command,
            dates=set(args.date or []),
            note=args.note,
        )
        _print_incidents(changed)
        return 0 if changed else 1
    if args.command == "run":
        processed = run_confirmed_recoveries(
            args.queue,
            sources_path=args.sources,
            output_path=args.output,
            logs_dir=args.logs,
            limit_per_source=args.limit_per_source,
            candidate_limit=args.candidate_limit,
        )
        _print_incidents(processed)
        return 1 if any(item.get("status") == "recovery_failed" for item in processed) else 0
    if args.command == "check":
        payload = load_queue(args.queue)
        statuses = set(args.status)
        incidents = [
            item for item in payload["incidents"] if item.get("status") in statuses
        ]
        for item in incidents:
            message = (
                f"{item.get('date')} {item.get('source')}: "
                f"{item.get('diagnosis') or item.get('last_error') or '渠道未抓取'}"
            )
            annotation = "warning" if args.warn_only else "error"
            print(f"::{annotation} title=渠道抓取异常::{message}")
        return 0 if args.warn_only else (1 if incidents else 0)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
