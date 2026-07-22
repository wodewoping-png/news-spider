from __future__ import annotations

import csv
import json
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from statistics import median
from zoneinfo import ZoneInfo

from .date_utils import DEFAULT_TIMEZONE, article_date
from .load_sources import expects_daily_output
from .storage import canonicalize_url


CHANNEL_FIELDS = (
    "date",
    "source",
    "frequency",
    "expected_daily",
    "crawl_status",
    "candidates_seen",
    "pages_fetched",
    "article_count",
    "unique_articles",
    "duplicate_articles",
    "usable_articles",
    "usable_rate",
    "previous_count",
    "baseline_median_7d",
    "ratio_to_baseline",
    "zero_streak_days",
    "anomaly_level",
    "anomaly_codes",
    "anomaly_reason",
    "updated_at",
)

SUMMARY_FIELDS = (
    "date",
    "total_articles",
    "unique_articles",
    "usable_articles",
    "usable_rate",
    "sources_configured",
    "sources_active",
    "sources_with_articles",
    "healthy_sources",
    "zero_sources",
    "idle_sources",
    "failed_sources",
    "baseline_median_7d",
    "ratio_to_baseline",
    "anomaly_level",
    "anomaly_codes",
    "anomaly_reason",
    "updated_at",
)

LEVEL_RANK = {"normal": 0, "warning": 1, "critical": 2}


def _as_int(value: object) -> int:
    try:
        return int(float(str(value or 0)))
    except (TypeError, ValueError):
        return 0


def _as_float(value: object) -> float:
    try:
        return float(str(value or 0))
    except (TypeError, ValueError):
        return 0.0


def _parse_date(value: object) -> date | None:
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, fields: tuple[str, ...], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def _write_volume_matrix(path: Path, rows: list[dict]) -> None:
    sources = sorted({str(row.get("source") or "") for row in rows if row.get("source")})
    dates = sorted({str(row.get("date") or "") for row in rows if row.get("date")})
    values = {
        (str(row.get("date")), str(row.get("source"))): row.get("article_count", "")
        for row in rows
    }
    matrix = [
        {
            "date": day,
            **{source: values.get((day, source), "") for source in sources},
        }
        for day in dates
    ]
    _write_csv(path, ("date", *sources), matrix)


def _ratio(value: int, baseline: float | None) -> float | None:
    if baseline is None or baseline <= 0:
        return None
    return round(value / baseline, 2)


def _rate(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 4) if denominator else 0.0


def _max_level(current: str, proposed: str) -> str:
    return proposed if LEVEL_RANK[proposed] > LEVEL_RANK[current] else current


def _inventory(
    jsonl_path: Path,
    min_content_chars: int,
    timezone_name: str,
) -> dict[tuple[str, str], dict[str, int]]:
    grouped: dict[tuple[str, str], dict] = defaultdict(
        lambda: {"article_count": 0, "usable_articles": 0, "urls": set()}
    )
    if not jsonl_path.exists():
        return {}
    with jsonl_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            published = article_date(item, timezone_name)
            source = str(item.get("source_name") or "").strip()
            if not published or not source:
                continue
            bucket = grouped[(published.isoformat(), source)]
            bucket["article_count"] += 1
            if len(str(item.get("content") or "").strip()) >= min_content_chars:
                bucket["usable_articles"] += 1
            url_key = canonicalize_url(str(item.get("url") or ""))
            if url_key:
                bucket["urls"].add(url_key)

    result: dict[tuple[str, str], dict[str, int]] = {}
    for key, value in grouped.items():
        total = value["article_count"]
        unique = len(value["urls"])
        result[key] = {
            "article_count": total,
            "unique_articles": unique,
            "duplicate_articles": max(total - unique, 0),
            "usable_articles": value["usable_articles"],
        }
    return result


def _prior_rows(
    rows: list[dict],
    target: date,
    *,
    source: str | None = None,
    days: int = 7,
) -> list[dict]:
    earliest = target - timedelta(days=days)
    selected = []
    for row in rows:
        row_date = _parse_date(row.get("date"))
        if not row_date or not earliest <= row_date < target:
            continue
        if source is not None and row.get("source") != source:
            continue
        selected.append(row)
    return sorted(selected, key=lambda row: str(row.get("date")))


def _zero_streak(current: dict, prior: list[dict], target: date) -> int:
    if _as_int(current.get("article_count")) != 0:
        return 0
    by_date = {
        row_date: row
        for row in prior
        if (row_date := _parse_date(row.get("date"))) is not None
    }
    streak = 1
    cursor = target - timedelta(days=1)
    while cursor in by_date and _as_int(by_date[cursor].get("article_count")) == 0:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


def _source_metrics(row: dict, all_rows: list[dict], target: date) -> dict:
    prior = _prior_rows(all_rows, target, source=str(row.get("source")), days=7)
    counts = [_as_int(item.get("article_count")) for item in prior]
    baseline = round(float(median(counts)), 2) if counts else None
    previous = _as_int(prior[-1].get("article_count")) if prior else None
    count = _as_int(row.get("article_count"))
    usable = _as_int(row.get("usable_articles"))
    usable_rate = _rate(usable, count)
    ratio = _ratio(count, baseline)
    expected_daily = str(row.get("expected_daily")).lower() == "true"
    crawl_status = str(row.get("crawl_status") or "")
    streak = _zero_streak(row, prior, target)

    level = "normal"
    codes: list[str] = []
    reasons: list[str] = []

    def add(code: str, reason: str, proposed: str = "warning") -> None:
        nonlocal level
        codes.append(code)
        reasons.append(reason)
        level = _max_level(level, proposed)

    if crawl_status == "failed":
        add("fetch_failed", "抓取任务失败", "critical")
    if crawl_status != "skipped" and expected_daily:
        if count == 0:
            if previous and previous > 0 or baseline and baseline > 0:
                add("sudden_zero", "日更渠道从有产出降为 0", "critical")
            else:
                add("no_output", "日更渠道当天没有收集到文章")
            if streak >= 2:
                add("zero_2d", f"已连续 {streak} 天为 0", "critical")
        elif baseline is not None and baseline > 0:
            difference = count - baseline
            if ratio is not None and ratio >= 2 and difference >= 5:
                severity = "critical" if ratio >= 4 else "warning"
                add("surge_2x", f"较 7 日中位数增至 {ratio:.2f} 倍", severity)
            if ratio is not None and ratio <= 0.35 and -difference >= 3:
                add("sharp_drop", f"仅为 7 日中位数的 {ratio:.2f} 倍")
    if count >= 2 and usable_rate < 0.7:
        add("low_usable_rate", f"正文可用率仅 {usable_rate:.0%}")
    duplicates = _as_int(row.get("duplicate_articles"))
    if count >= 3 and duplicates / count >= 0.2:
        add("duplicate_spike", f"重复文章占比 {duplicates / count:.0%}")

    row.update(
        {
            "usable_rate": f"{usable_rate:.4f}",
            "previous_count": "" if previous is None else previous,
            "baseline_median_7d": "" if baseline is None else f"{baseline:.2f}",
            "ratio_to_baseline": "" if ratio is None else f"{ratio:.2f}",
            "zero_streak_days": streak,
            "anomaly_level": level,
            "anomaly_codes": ",".join(codes),
            "anomaly_reason": "；".join(reasons),
        }
    )
    return row


def _summary_metrics(row: dict, all_rows: list[dict], target: date) -> dict:
    prior = _prior_rows(all_rows, target, days=7)
    totals = [_as_int(item.get("total_articles")) for item in prior]
    baseline = round(float(median(totals)), 2) if totals else None
    total = _as_int(row.get("total_articles"))
    ratio = _ratio(total, baseline)
    usable_rate = _rate(
        _as_int(row.get("usable_articles")),
        total,
    )
    level = "normal"
    codes: list[str] = []
    reasons: list[str] = []

    def add(code: str, reason: str, proposed: str = "warning") -> None:
        nonlocal level
        codes.append(code)
        reasons.append(reason)
        level = _max_level(level, proposed)

    if total == 0:
        add("overall_zero", "全部渠道总收集量为 0", "critical")
    elif baseline is not None and baseline > 0 and ratio is not None:
        difference = total - baseline
        if ratio >= 2 and difference >= 20:
            add(
                "overall_surge",
                f"总量较 7 日中位数增至 {ratio:.2f} 倍",
                "critical" if ratio >= 3 else "warning",
            )
        if ratio <= 0.5 and -difference >= 10:
            add(
                "overall_drop",
                f"总量仅为 7 日中位数的 {ratio:.2f} 倍",
                "critical" if ratio <= 0.2 else "warning",
            )
    active = _as_int(row.get("sources_active"))
    zero_sources = _as_int(row.get("zero_sources"))
    failed = _as_int(row.get("failed_sources"))
    if failed:
        add("source_failures", f"{failed} 个渠道抓取失败", "critical")
    if active and zero_sources / active >= 0.25:
        add("many_zero_sources", f"{zero_sources}/{active} 个活跃渠道当天为 0")
    if total >= 5 and usable_rate < 0.7:
        add("overall_low_quality", f"整体正文可用率仅 {usable_rate:.0%}")

    row.update(
        {
            "usable_rate": f"{usable_rate:.4f}",
            "baseline_median_7d": "" if baseline is None else f"{baseline:.2f}",
            "ratio_to_baseline": "" if ratio is None else f"{ratio:.2f}",
            "anomaly_level": level,
            "anomaly_codes": ",".join(codes),
            "anomaly_reason": "；".join(reasons),
        }
    )
    return row


def _markdown_report(
    target: date,
    summary: dict,
    current_rows: list[dict],
    min_content_chars: int,
) -> str:
    abnormal = [
        row for row in current_rows if row.get("anomaly_level") != "normal"
    ]
    abnormal.sort(
        key=lambda row: (
            -LEVEL_RANK.get(str(row.get("anomaly_level")), 0),
            str(row.get("source")),
        )
    )
    result = [
        "# 新闻渠道自主审查报告",
        "",
        f"- 审查日期：{target.isoformat()}",
        f"- 整体状态：{summary.get('anomaly_level', 'normal')}",
        f"- 收集总量：{summary.get('total_articles', 0)} 篇",
        f"- 正文可用：{summary.get('usable_articles', 0)} 篇（{_as_float(summary.get('usable_rate')):.0%}）",
        f"- 有产出渠道：{summary.get('sources_with_articles', 0)}/{summary.get('sources_active', 0)}",
        f"- 7 日总量中位数：{summary.get('baseline_median_7d') or '历史不足'}",
        "",
    ]
    if summary.get("anomaly_reason"):
        result.extend(["## 整体异常", "", str(summary["anomaly_reason"]), ""])
    result.extend(
        [
            "## 渠道异常",
            "",
            "| 级别 | 渠道 | 今日 | 前次 | 7日中位数 | 连续为0 | 异常说明 |",
            "|---|---|---:|---:|---:|---:|---|",
        ]
    )
    if abnormal:
        for row in abnormal:
            reason = str(row.get("anomaly_reason") or "").replace("|", "\\|")
            source = str(row.get("source") or "").replace("|", "\\|")
            result.append(
                f"| {row.get('anomaly_level')} | {source} | "
                f"{row.get('article_count', 0)} | {row.get('previous_count') or '-'} | "
                f"{row.get('baseline_median_7d') or '-'} | "
                f"{row.get('zero_streak_days', 0)} | {reason} |"
            )
    else:
        result.append("| normal | — | — | — | — | — | 本次未发现异常 |")
    result.extend(
        [
            "",
            "## 判定口径",
            "",
            "- 每次抓取后自动审查；连续 2 天为 0 会升级为严重异常。",
            "- 日更渠道从有产出降到 0 会立即报警；周刊、月刊无更新不报零产出异常。",
            "- 相对 7 日中位数达到 2 倍且至少增加 5 篇，判定渠道突增。",
            "- 整体总量达到 2 倍且至少增加 20 篇，判定整体突增。",
            f"- 正文少于 {min_content_chars} 字计为不可用；可用率低于 70% 会报警。",
            "- 历史不足 7 天时使用已有记录；首批记录主要用于积累基线。",
            "",
        ]
    )
    return "\n".join(result)


def run_daily_audit(
    jsonl_path: Path,
    logs_dir: Path,
    target_date: date,
    health_records: list[dict],
    *,
    min_content_chars: int = 200,
    timezone_name: str = DEFAULT_TIMEZONE,
) -> dict:
    logs_dir.mkdir(parents=True, exist_ok=True)
    channel_path = logs_dir / "channel-daily-stats.csv"
    volume_path = logs_dir / "channel-daily-volume.csv"
    summary_path = logs_dir / "daily-collection-summary.csv"
    json_path = logs_dir / "audit-report.json"
    markdown_path = logs_dir / "audit-report.md"
    generated_at = datetime.now(ZoneInfo(timezone_name)).isoformat()
    target_key = target_date.isoformat()
    inventory = _inventory(jsonl_path, min_content_chars, timezone_name)
    frequency_by_source = {
        str(record.get("source") or ""): str(record.get("frequency") or "")
        for record in health_records
    }

    existing = _read_csv(channel_path)
    by_key: dict[tuple[str, str], dict] = {
        (str(row.get("date")), str(row.get("source"))): row
        for row in existing
        if row.get("crawl_status") != "historical"
        or (str(row.get("date")), str(row.get("source"))) in inventory
    }
    for (day, source), counts in inventory.items():
        key = (day, source)
        if key in by_key and by_key[key].get("crawl_status") != "historical":
            continue
        frequency = frequency_by_source.get(source, "")
        by_key[key] = {
            "date": day,
            "source": source,
            "frequency": frequency,
            "expected_daily": str(expects_daily_output(frequency)).lower(),
            "crawl_status": "historical",
            **counts,
            "usable_rate": f"{_rate(counts['usable_articles'], counts['article_count']):.4f}",
            "updated_at": generated_at,
        }

    for record in health_records:
        source = str(record.get("source") or "")
        frequency = str(record.get("frequency") or "")
        counts = inventory.get(
            (target_key, source),
            {
                "article_count": 0,
                "unique_articles": 0,
                "duplicate_articles": 0,
                "usable_articles": 0,
            },
        )
        crawl_status = str(record.get("status") or "")
        if crawl_status == "zero" and counts["article_count"] > 0:
            crawl_status = "already_collected"
        by_key[(target_key, source)] = {
            "date": target_key,
            "source": source,
            "frequency": frequency,
            "expected_daily": str(expects_daily_output(frequency)).lower(),
            "crawl_status": crawl_status,
            "candidates_seen": record.get("candidates_seen", 0),
            "pages_fetched": record.get("pages_fetched", 0),
            **counts,
            "updated_at": generated_at,
        }

    channel_rows = sorted(
        by_key.values(),
        key=lambda row: (str(row.get("date")), str(row.get("source"))),
    )
    current_rows = [
        row for row in channel_rows if str(row.get("date")) == target_key
    ]
    for row in current_rows:
        _source_metrics(row, channel_rows, target_date)
    _write_csv(channel_path, CHANNEL_FIELDS, channel_rows)
    _write_volume_matrix(volume_path, channel_rows)

    summaries = _read_csv(summary_path)
    inventory_dates = {day for day, _source in inventory}
    summary_by_date = {
        str(row.get("date")): row
        for row in summaries
        if row.get("sources_configured") or str(row.get("date")) in inventory_dates
    }
    inventory_by_date: dict[str, dict[str, int]] = defaultdict(
        lambda: {
            "total_articles": 0,
            "unique_articles": 0,
            "usable_articles": 0,
        }
    )
    for (day, _source), counts in inventory.items():
        for field in ("article_count", "unique_articles", "usable_articles"):
            target_field = "total_articles" if field == "article_count" else field
            inventory_by_date[day][target_field] += counts[field]
    for day, counts in inventory_by_date.items():
        if day not in summary_by_date or not summary_by_date[day].get(
            "sources_configured"
        ):
            summary_by_date[day] = {
                "date": day,
                **counts,
                "usable_rate": f"{_rate(counts['usable_articles'], counts['total_articles']):.4f}",
                "updated_at": generated_at,
            }

    active_rows = [
        row for row in current_rows if row.get("crawl_status") != "skipped"
    ]
    current_counts = inventory_by_date.get(
        target_key,
        {"total_articles": 0, "unique_articles": 0, "usable_articles": 0},
    )
    current_summary = {
        "date": target_key,
        **current_counts,
        "sources_configured": len(current_rows),
        "sources_active": len(active_rows),
        "sources_with_articles": sum(
            _as_int(row.get("article_count")) > 0 for row in active_rows
        ),
        "healthy_sources": sum(
            row.get("crawl_status") in {"healthy", "already_collected"}
            for row in active_rows
        ),
        "zero_sources": sum(
            _as_int(row.get("article_count")) == 0
            and str(row.get("expected_daily")).lower() == "true"
            and row.get("crawl_status") != "failed"
            for row in active_rows
        ),
        "idle_sources": sum(
            row.get("crawl_status") == "idle" for row in active_rows
        ),
        "failed_sources": sum(
            row.get("crawl_status") == "failed" for row in active_rows
        ),
        "updated_at": generated_at,
    }
    summary_by_date[target_key] = current_summary
    summary_rows = sorted(
        summary_by_date.values(),
        key=lambda row: str(row.get("date")),
    )
    _summary_metrics(current_summary, summary_rows, target_date)
    _write_csv(summary_path, SUMMARY_FIELDS, summary_rows)

    report = {
        "generated_at": generated_at,
        "target_date": target_key,
        "overall": current_summary,
        "anomalies": [
            {field: row.get(field, "") for field in CHANNEL_FIELDS}
            for row in current_rows
            if row.get("anomaly_level") != "normal"
        ],
        "paths": {
            "channel_daily_stats": str(channel_path),
            "channel_daily_volume": str(volume_path),
            "daily_collection_summary": str(summary_path),
            "markdown_report": str(markdown_path),
        },
    }
    json_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    markdown_path.write_text(
        _markdown_report(
            target_date,
            current_summary,
            current_rows,
            min_content_chars,
        ),
        encoding="utf-8",
    )
    return report
