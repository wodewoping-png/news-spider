from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Callable, Iterable
from zoneinfo import ZoneInfo

from .date_utils import DEFAULT_TIMEZONE
from .load_sources import expects_output_on_date
from .notifications import NotificationError, notify_dingtalk_changes
from .recovery import (
    OPEN_STATUSES,
    auto_confirm_missing_run_incidents,
    load_queue,
    run_confirmed_recoveries,
    sync_recovery_queue,
    update_incidents,
)


STATE_VERSION = 1
EVENT_VERSION = 1
UNHEALTHY_STATUSES = {"failed", "zero", "degraded"}
SUCCESS_STATUSES = {
    "healthy",
    "already_collected",
    "idle",
    "recovered",
    "verified_no_news",
}
OPS_FIELDS = (
    "source",
    "frequency",
    "last_target_date",
    "last_status",
    "previous_status",
    "last_attempt_at",
    "last_success_at",
    "last_success_date",
    "consecutive_unhealthy",
    "open_incidents",
    "next_action",
    "last_error_type",
    "last_error",
    "crawl_mode",
    "candidates_seen",
    "pages_fetched",
    "new_articles",
    "refreshed_articles",
    "usable_articles",
    "incomplete_articles",
    "short_articles",
    "min_content_chars",
    "content_chars_min",
    "content_chars_median",
    "content_chars_max",
    "updated_at",
)
_SECRET_PATTERN = re.compile(
    r"(?i)((?:access[_-]?token|api[_-]?key|password|secret|authorization)"
    r"(?:%3[dD]|=|:)\s*)[^&\s,;]+"
)


def _now() -> str:
    return datetime.now(ZoneInfo(DEFAULT_TIMEZONE)).isoformat()


def _safe_text(value: object) -> str:
    text = str(value or "")
    return _SECRET_PATTERN.sub(r"\1[REDACTED]", text)[:2000]


def _as_int(value: object) -> int:
    try:
        return int(float(str(value or 0)))
    except (TypeError, ValueError):
        return 0


def _read_json(path: Path, default: dict) -> dict:
    if not path.exists():
        return default
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise ValueError(f"渠道运维文件无法读取，已停止以避免覆盖：{path}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"渠道运维文件结构无效，已停止以避免覆盖：{path}")
    return payload


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _append_events(path: Path, events: Iterable[dict]) -> None:
    rows = list(events)
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _attempt_id(generated_at: str, target_date: str, record: dict) -> str:
    material = "\n".join(
        (
            generated_at,
            target_date,
            str(record.get("source") or ""),
            str(record.get("status") or ""),
            str(record.get("reason") or ""),
            str(record.get("new_articles") or 0),
        )
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()[:24]


def _incident_summary(queue: dict) -> dict[str, list[dict]]:
    by_source: dict[str, list[dict]] = {}
    for incident in queue.get("incidents", []):
        if str(incident.get("status") or "") not in OPEN_STATUSES:
            continue
        source = str(incident.get("source") or "")
        if source:
            by_source.setdefault(source, []).append(incident)
    return by_source


def _incident_by_key(queue: dict) -> dict[tuple[str, str], dict]:
    return {
        (str(item.get("source") or ""), str(item.get("date") or "")): item
        for item in queue.get("incidents", [])
        if item.get("source") and item.get("date")
    }


def _next_action(status: str, incidents: list[dict]) -> str:
    incident_statuses = {str(item.get("status") or "") for item in incidents}
    if "recovery_failed" in incident_statuses:
        return "repair_then_reconfirm"
    if incident_statuses & {"confirmed", "recovering"}:
        return "automatic_backfill"
    if "pending_confirmation" in incident_statuses:
        return "repair_then_confirm"
    if status in UNHEALTHY_STATUSES:
        return "investigate"
    return "none"


def _write_csv(path: Path, channels: dict[str, dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=OPS_FIELDS)
        writer.writeheader()
        for source in sorted(channels, key=str.casefold):
            row = channels[source]
            writer.writerow({field: row.get(field, "") for field in OPS_FIELDS})
    temporary.replace(path)


def detect_missing_run_incidents(
    logs_dir: Path,
    latest_target_date: str,
    *,
    generated_at: str,
    lookback_days: int = 31,
) -> list[dict]:
    """Create recovery incidents for expected dates with no crawl record at all."""
    stats_path = logs_dir / "channel-daily-stats.csv"
    summary_path = logs_dir / "daily-collection-summary.csv"
    if not stats_path.exists() or not summary_path.exists() or not latest_target_date:
        return []
    try:
        latest = date.fromisoformat(latest_target_date)
    except ValueError:
        return []
    with stats_path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    with summary_path.open("r", encoding="utf-8-sig", newline="") as handle:
        summary_rows = list(csv.DictReader(handle))
    audited_dates: set[date] = set()
    for row in summary_rows:
        if _as_int(row.get("sources_configured")) <= 0:
            continue
        try:
            audited_day = date.fromisoformat(str(row.get("date") or ""))
        except ValueError:
            continue
        if audited_day <= latest:
            audited_dates.add(audited_day)
    if latest not in audited_dates:
        return []

    first_active: dict[str, date] = {}
    latest_profile: dict[str, tuple[date, str, str]] = {}
    inventory_counts: dict[tuple[str, str], int] = {}
    for row in rows:
        source = str(row.get("source") or "")
        day_text = str(row.get("date") or "")
        if not source or not day_text:
            continue
        try:
            day = date.fromisoformat(day_text)
        except ValueError:
            continue
        if day > latest:
            continue
        inventory_counts[(source, day_text)] = max(
            inventory_counts.get((source, day_text), 0),
            _as_int(row.get("article_count")),
        )
        frequency = str(row.get("frequency") or "")
        status = str(row.get("crawl_status") or "")
        if status != "historical":
            first_active[source] = min(first_active.get(source, day), day)
        if source not in latest_profile or day >= latest_profile[source][0]:
            latest_profile[source] = (day, frequency, status)

    gap_rows: list[dict] = []
    gap_health: list[dict] = []
    earliest_allowed = latest - timedelta(days=max(1, lookback_days))
    audited_start = max(min(audited_dates), earliest_allowed)
    missing_dates: list[date] = []
    cursor = audited_start
    while cursor < latest:
        if cursor not in audited_dates:
            missing_dates.append(cursor)
        cursor += timedelta(days=1)

    for source, profile in latest_profile.items():
        _profile_day, frequency, status = profile
        if status == "skipped" or source not in first_active:
            continue
        for missing_day in missing_dates:
            if missing_day < first_active[source]:
                continue
            if inventory_counts.get((source, missing_day.isoformat()), 0) > 0:
                continue
            if not expects_output_on_date(frequency, missing_day):
                continue
            day_text = missing_day.isoformat()
            reason = (
                "missing run record: 该日期没有渠道抓取记录，"
                "可能是工作流延迟、取消或进程级失败"
            )
            gap_rows.append(
                {
                    "date": day_text,
                    "source": source,
                    "frequency": frequency,
                    "expected_daily": "true",
                    "crawl_status": "failed",
                    "article_count": 0,
                    "anomaly_level": "critical",
                    "anomaly_codes": "missing_run_record",
                    "anomaly_reason": reason,
                    "candidates_seen": 0,
                    "pages_fetched": 0,
                }
            )
            gap_health.append(
                {
                    "source": source,
                    "frequency": frequency,
                    "status": "failed",
                    "reason": reason,
                    "error_type": "MissingRunRecord",
                    "crawl_mode": "scheduled",
                    "candidates_seen": 0,
                    "pages_fetched": 0,
                }
            )
    if gap_rows:
        sync_recovery_queue(
            logs_dir / "recovery-queue.json",
            gap_rows,
            gap_health,
            generated_at=generated_at,
        )
    return gap_rows


def _build_report(state: dict, queue: dict, *, generated_at: str) -> dict:
    channels = list(state.get("channels", {}).values())
    active_incidents = [
        item
        for item in queue.get("incidents", [])
        if str(item.get("status") or "") in OPEN_STATUSES
    ]
    status_counts: dict[str, int] = {}
    for row in channels:
        status = str(row.get("last_status") or "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1
    return {
        "generated_at": generated_at,
        "summary": {
            "channels": len(channels),
            "healthy": sum(
                str(row.get("last_status") or "") in SUCCESS_STATUSES
                for row in channels
            ),
            "unhealthy": sum(
                str(row.get("last_status") or "") in UNHEALTHY_STATUSES
                for row in channels
            ),
            "open_incidents": len(active_incidents),
            "pending_confirmation": sum(
                item.get("status") == "pending_confirmation"
                for item in active_incidents
            ),
            "recovery_failed": sum(
                item.get("status") == "recovery_failed"
                for item in active_incidents
            ),
            "status_counts": status_counts,
        },
        "channels": sorted(
            channels,
            key=lambda row: (
                str(row.get("next_action") or "") == "none",
                str(row.get("source") or "").casefold(),
            ),
        ),
        "incidents": sorted(
            active_incidents,
            key=lambda item: (str(item.get("date")), str(item.get("source"))),
        ),
    }


def _report_markdown(report: dict) -> str:
    summary = report["summary"]
    rows = [
        "# 渠道运维总览",
        "",
        f"- 生成时间：{report['generated_at']}",
        f"- 渠道数：{summary['channels']}",
        f"- 健康/正常空闲：{summary['healthy']}",
        f"- 异常渠道：{summary['unhealthy']}",
        f"- 待处理缺口：{summary['open_incidents']}",
        "",
        "## 需要处理的渠道",
        "",
        "| 渠道 | 最近目标日期 | 状态 | 正文中位字符 | 不完整正文 | 短正文 | 连续异常 | 待补日期数 | 原因 | 下一步 |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |",
    ]
    actionable = [
        row for row in report["channels"] if str(row.get("next_action")) != "none"
    ]
    if actionable:
        for row in actionable:
            reason = _safe_text(row.get("last_error")).replace("|", "\\|")
            rows.append(
                "| {source} | {date} | {status} | {median_chars} | {incomplete} | {short} | "
                "{streak} | {incidents} | "
                "{reason} | {action} |".format(
                    source=str(row.get("source") or "").replace("|", "\\|"),
                    date=row.get("last_target_date") or "-",
                    status=row.get("last_status") or "-",
                    median_chars=row.get("content_chars_median") or 0,
                    incomplete=row.get("incomplete_articles") or 0,
                    short=row.get("short_articles") or 0,
                    streak=row.get("consecutive_unhealthy") or 0,
                    incidents=row.get("open_incidents") or 0,
                    reason=reason or "-",
                    action=row.get("next_action") or "-",
                )
            )
    else:
        rows.append("| - | - | healthy | 0 | 0 | 0 | 0 | 0 | 无待处理异常 | none |")
    rows.extend(
        [
            "",
            "## 运维闭环",
            "",
            "异常会先进入待确认队列；修复后确认，系统只补抓对应渠道和缺失日期；"
            "补抓有文章则标记 recovered，当日确无新闻可人工标记 ignored。",
            "",
        ]
    )
    return "\n".join(rows)


def reconcile(
    logs_dir: Path = Path("logs"),
    *,
    health_path: Path | None = None,
    timestamp: str | None = None,
) -> dict:
    generated_at = timestamp or _now()
    health_path = health_path or logs_dir / "channel-health.json"
    state_path = logs_dir / "channel-ops-state.json"
    event_path = logs_dir / "channel-operations.jsonl"
    queue_path = logs_dir / "recovery-queue.json"
    health = _read_json(
        health_path,
        {"generated_at": "", "target_date": "", "sources": []},
    )
    state = _read_json(
        state_path,
        {
            "version": STATE_VERSION,
            "updated_at": "",
            "last_health_generated_at": "",
            "ingested_attempt_ids": [],
            "channels": {},
        },
    )
    if not isinstance(state.get("channels"), dict):
        raise ValueError(f"渠道运维状态结构无效，已停止以避免覆盖：{state_path}")
    missing_run_rows = detect_missing_run_incidents(
        logs_dir,
        str(health.get("target_date") or ""),
        generated_at=generated_at,
    )
    queue = load_queue(queue_path)
    incidents_by_source = _incident_summary(queue)
    incidents_by_key = _incident_by_key(queue)
    channels = state["channels"]
    seen_ordered = [
        str(item) for item in state.get("ingested_attempt_ids", []) if item
    ]
    seen = set(seen_ordered)
    new_events: list[dict] = []
    health_generated_at = str(health.get("generated_at") or generated_at)
    target_date = str(health.get("target_date") or "")

    for gap in missing_run_rows:
        gap_id = hashlib.sha256(
            f"missing_run\n{gap.get('date')}\n{gap.get('source')}".encode("utf-8")
        ).hexdigest()[:24]
        if gap_id in seen:
            continue
        new_events.append(
            {
                "version": EVENT_VERSION,
                "id": gap_id,
                "recorded_at": generated_at,
                "attempted_at": "",
                "target_date": str(gap.get("date") or ""),
                "source": str(gap.get("source") or ""),
                "status": "missing_run",
                "previous_status": "",
                "reason": _safe_text(gap.get("anomaly_reason")),
                "error_type": "MissingRunRecord",
                "crawl_mode": "scheduled",
                "candidates_seen": 0,
                "pages_fetched": 0,
                "new_articles": 0,
                "usable_articles": 0,
            }
        )
        seen.add(gap_id)
        seen_ordered.append(gap_id)

    for record in health.get("sources", []):
        source = str(record.get("source") or "")
        if not source:
            continue
        status = str(record.get("status") or "unknown")
        reason = _safe_text(record.get("reason"))
        resolved_incident = incidents_by_key.get((source, target_date), {})
        if status in UNHEALTHY_STATUSES and resolved_incident.get("status") == "recovered":
            status = "recovered"
            reason = "历史缺口补抓已验证成功"
        elif (
            status in UNHEALTHY_STATUSES
            and resolved_incident.get("status") == "ignored"
        ):
            status = "verified_no_news"
            reason = "人工确认目标日期无新闻"
        normalized_record = dict(record)
        normalized_record.update({"status": status, "reason": reason})
        attempt_id = _attempt_id(
            health_generated_at,
            target_date,
            normalized_record,
        )
        current = dict(channels.get(source, {}))
        previous_status = str(current.get("last_status") or "")
        source_incidents = incidents_by_source.get(source, [])
        if attempt_id not in seen:
            streak = _as_int(current.get("consecutive_unhealthy"))
            if status in UNHEALTHY_STATUSES:
                streak = streak + 1 if previous_status in UNHEALTHY_STATUSES else 1
            else:
                streak = 0
            current.update(
                {
                    "source": source,
                    "frequency": str(
                        record.get("frequency") or current.get("frequency") or ""
                    ),
                    "last_target_date": target_date,
                    "last_status": status,
                    "previous_status": previous_status,
                    "last_attempt_at": health_generated_at,
                    "consecutive_unhealthy": streak,
                    "open_incidents": len(source_incidents),
                    "next_action": _next_action(status, source_incidents),
                    "last_error_type": _safe_text(record.get("error_type")),
                    "last_error": reason,
                    "crawl_mode": str(record.get("crawl_mode") or ""),
                    "candidates_seen": _as_int(record.get("candidates_seen")),
                    "pages_fetched": _as_int(record.get("pages_fetched")),
                    "new_articles": _as_int(record.get("new_articles")),
                    "refreshed_articles": _as_int(
                        record.get("refreshed_articles")
                    ),
                    "usable_articles": _as_int(record.get("usable_articles")),
                    "incomplete_articles": _as_int(
                        record.get("incomplete_articles")
                    ),
                    "short_articles": _as_int(record.get("short_articles")),
                    "min_content_chars": _as_int(record.get("min_content_chars")),
                    "content_chars_min": _as_int(record.get("content_chars_min")),
                    "content_chars_median": _as_int(
                        record.get("content_chars_median")
                    ),
                    "content_chars_max": _as_int(record.get("content_chars_max")),
                    "updated_at": generated_at,
                }
            )
            if status in SUCCESS_STATUSES:
                current["last_success_at"] = health_generated_at
                current["last_success_date"] = target_date
            new_events.append(
                {
                    "version": EVENT_VERSION,
                    "id": attempt_id,
                    "recorded_at": generated_at,
                    "attempted_at": health_generated_at,
                    "target_date": target_date,
                    "source": source,
                    "status": status,
                    "previous_status": previous_status,
                    "reason": reason,
                    "error_type": _safe_text(record.get("error_type")),
                    "crawl_mode": str(record.get("crawl_mode") or ""),
                    "candidates_seen": _as_int(record.get("candidates_seen")),
                    "pages_fetched": _as_int(record.get("pages_fetched")),
                    "new_articles": _as_int(record.get("new_articles")),
                    "refreshed_articles": _as_int(
                        record.get("refreshed_articles")
                    ),
                    "usable_articles": _as_int(record.get("usable_articles")),
                    "incomplete_articles": _as_int(
                        record.get("incomplete_articles")
                    ),
                    "short_articles": _as_int(record.get("short_articles")),
                    "min_content_chars": _as_int(record.get("min_content_chars")),
                    "content_chars_min": _as_int(record.get("content_chars_min")),
                    "content_chars_median": _as_int(
                        record.get("content_chars_median")
                    ),
                    "content_chars_max": _as_int(record.get("content_chars_max")),
                }
            )
            seen.add(attempt_id)
            seen_ordered.append(attempt_id)
        channels[source] = current

    for source, current in channels.items():
        source_incidents = incidents_by_source.get(source, [])
        current["open_incidents"] = len(source_incidents)
        current["next_action"] = _next_action(
            str(current.get("last_status") or ""),
            source_incidents,
        )
        current["updated_at"] = generated_at

    state.update(
        {
            "version": STATE_VERSION,
            "updated_at": generated_at,
            "last_health_generated_at": health_generated_at,
            "ingested_attempt_ids": seen_ordered[-10000:],
            "channels": channels,
        }
    )
    _append_events(event_path, new_events)
    _write_json(state_path, state)
    _write_csv(logs_dir / "channel-operations.csv", channels)
    report = _build_report(state, queue, generated_at=generated_at)
    _write_json(logs_dir / "channel-ops-report.json", report)
    (logs_dir / "channel-ops-report.md").write_text(
        _report_markdown(report),
        encoding="utf-8",
    )
    return report


def _notify(logs_dir: Path) -> list[dict]:
    webhook = os.environ.get("DINGTALK_WEBHOOK", "").strip()
    if not webhook:
        print("未配置 DINGTALK_WEBHOOK，跳过钉钉推送。")
        return []
    return notify_dingtalk_changes(
        logs_dir / "recovery-queue.json",
        logs_dir / "notification-state.json",
        webhook=webhook,
        secret=os.environ.get("DINGTALK_SECRET", "").strip(),
        keyword=os.environ.get("DINGTALK_KEYWORD", "").strip() or "渠道抓取告警",
        run_url=os.environ.get("ALERT_RUN_URL", "").strip(),
    )


CommandRunner = Callable[[list[str]], int]


def _run_command(command: list[str]) -> int:
    return subprocess.run(command, check=False).returncode


def _file_digest(path: Path) -> str:
    if not path.exists():
        return ""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_cycle(
    *,
    sources_path: Path,
    output_path: Path,
    logs_dir: Path,
    target_date: str = "",
    limit_per_source: int = 20,
    candidate_limit: int = 100,
    command_runner: CommandRunner = _run_command,
    send_notifications: bool = True,
    auto_backfill_missing_runs: bool = True,
) -> int:
    if auto_backfill_missing_runs:
        auto_confirm_missing_run_incidents(logs_dir / "recovery-queue.json")
    run_confirmed_recoveries(
        logs_dir / "recovery-queue.json",
        sources_path=sources_path,
        output_path=output_path,
        logs_dir=logs_dir,
        command_runner=command_runner,
    )
    health_path = logs_dir / "channel-health.json"
    previous_health_digest = _file_digest(health_path)
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
        "--limit-per-source",
        str(limit_per_source),
        "--candidate-limit",
        str(candidate_limit),
    ]
    if target_date:
        command.extend(["--target-date", target_date])
    return_code = command_runner(command)
    current_health_digest = _file_digest(health_path)
    if current_health_digest and current_health_digest != previous_health_digest:
        reconcile(logs_dir)
        if auto_backfill_missing_runs and auto_confirm_missing_run_incidents(
            logs_dir / "recovery-queue.json"
        ):
            run_confirmed_recoveries(
                logs_dir / "recovery-queue.json",
                sources_path=sources_path,
                output_path=output_path,
                logs_dir=logs_dir,
                command_runner=command_runner,
            )
            reconcile(logs_dir)
    elif return_code:
        recorded_at = _now()
        failure = {
            "version": EVENT_VERSION,
            "id": hashlib.sha256(
                f"{recorded_at}\n{target_date}\n{str(return_code)}".encode("utf-8")
            ).hexdigest()[:24],
            "recorded_at": recorded_at,
            "attempted_at": recorded_at,
            "target_date": target_date,
            "source": "__system__",
            "status": "failed",
            "previous_status": "",
            "reason": f"统一抓取进程退出码为 {return_code}，未生成新的渠道健康报告",
            "error_type": "CrawlerProcessError",
            "crawl_mode": "cycle",
            "candidates_seen": 0,
            "pages_fetched": 0,
            "new_articles": 0,
            "usable_articles": 0,
        }
        _append_events(logs_dir / "channel-operations.jsonl", [failure])
        print(f"::error title=统一抓取进程失败::{failure['reason']}")
    if send_notifications:
        try:
            _notify(logs_dir)
        except (NotificationError, ValueError) as exc:
            print(f"::warning title=钉钉推送失败::{_safe_text(exc)}")
    return return_code


def _print_summary(report: dict) -> None:
    summary = report["summary"]
    print(
        "渠道运维："
        f"{summary['channels']} 个渠道，"
        f"{summary['unhealthy']} 个异常，"
        f"{summary['open_incidents']} 个待处理缺口。"
    )
    for row in report["channels"]:
        if row.get("next_action") == "none":
            continue
        print(
            f"[{row.get('last_status')}] {row.get('source')} | "
            f"{row.get('last_target_date')} | "
            f"{row.get('last_error') or '-'} | {row.get('next_action')}"
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="统一渠道抓取运维管理")
    parser.add_argument("--logs", type=Path, default=Path("logs"))
    subparsers = parser.add_subparsers(dest="command", required=True)

    cycle = subparsers.add_parser("cycle", help="运行补抓、每日抓取、状态归并和告警")
    cycle.add_argument("--sources", type=Path, default=Path("sources.xlsx"))
    cycle.add_argument("--output", type=Path, default=Path("data/articles.jsonl"))
    cycle.add_argument("--target-date", default="")
    cycle.add_argument("--limit-per-source", type=int, default=20)
    cycle.add_argument("--candidate-limit", type=int, default=100)
    cycle.add_argument("--no-notify", action="store_true")
    cycle.add_argument(
        "--no-auto-backfill",
        action="store_true",
        help="不自动确认并补抓整日运行缺失产生的渠道缺口",
    )

    reconcile_parser = subparsers.add_parser(
        "reconcile", help="归并最新抓取结果并刷新运维报表"
    )
    reconcile_parser.add_argument("--health", type=Path)

    subparsers.add_parser("status", help="显示当前渠道运维状态")
    subparsers.add_parser("notify", help="推送新的渠道状态变化")

    resolve = subparsers.add_parser(
        "resolve", help="记录修复确认/无新闻决定，并按需立即补抓"
    )
    resolve.add_argument("action", choices=("confirm", "ignore"))
    resolve.add_argument("--source", required=True)
    resolve.add_argument("--date", action="append")
    resolve.add_argument("--note", required=True)
    resolve.add_argument("--sources", type=Path, default=Path("sources.xlsx"))
    resolve.add_argument("--output", type=Path, default=Path("data/articles.jsonl"))
    resolve.add_argument("--run", action="store_true")
    resolve.add_argument("--notify", action="store_true")

    check = subparsers.add_parser("check", help="输出当前待处理渠道")
    check.add_argument("--warn-only", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.command == "cycle":
        return run_cycle(
            sources_path=args.sources,
            output_path=args.output,
            logs_dir=args.logs,
            target_date=args.target_date,
            limit_per_source=args.limit_per_source,
            candidate_limit=args.candidate_limit,
            send_notifications=not args.no_notify,
            auto_backfill_missing_runs=not args.no_auto_backfill,
        )
    if args.command == "reconcile":
        report = reconcile(args.logs, health_path=args.health)
        _print_summary(report)
        return 0
    if args.command == "status":
        state = _read_json(
            args.logs / "channel-ops-state.json",
            {"version": STATE_VERSION, "channels": {}},
        )
        report = _build_report(
            state,
            load_queue(args.logs / "recovery-queue.json"),
            generated_at=_now(),
        )
        _print_summary(report)
        return 0
    if args.command == "notify":
        try:
            changes = _notify(args.logs)
        except (NotificationError, ValueError) as exc:
            print(f"钉钉推送失败：{_safe_text(exc)}")
            return 1
        print(f"钉钉状态变化推送完成：{len(changes)} 条。")
        return 0
    if args.command == "resolve":
        changed = update_incidents(
            args.logs / "recovery-queue.json",
            args.source,
            args.action,
            dates=set(args.date or []),
            note=args.note,
        )
        if not changed:
            print("没有匹配的待处理渠道条目。")
            return 1
        if args.action == "confirm" and args.run:
            run_confirmed_recoveries(
                args.logs / "recovery-queue.json",
                sources_path=args.sources,
                output_path=args.output,
                logs_dir=args.logs,
            )
        report = reconcile(args.logs)
        _print_summary(report)
        if args.notify:
            try:
                _notify(args.logs)
            except (NotificationError, ValueError) as exc:
                print(f"::warning title=钉钉推送失败::{_safe_text(exc)}")
        return 0
    if args.command == "check":
        queue = load_queue(args.logs / "recovery-queue.json")
        incidents = [
            item
            for item in queue.get("incidents", [])
            if str(item.get("status") or "") in {"pending_confirmation", "recovery_failed"}
        ]
        for item in incidents:
            annotation = "warning" if args.warn_only else "error"
            message = _safe_text(
                item.get("diagnosis") or item.get("last_error") or "渠道未抓取"
            )
            print(
                f"::{annotation} title=渠道抓取异常::"
                f"{item.get('date')} {item.get('source')}: {message}"
            )
        return 0 if args.warn_only else (1 if incidents else 0)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
