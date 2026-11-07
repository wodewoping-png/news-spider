"""Readable, gap-aware daily count ledger for monitored news sources."""

from __future__ import annotations

import argparse
import csv
from datetime import date, timedelta
from pathlib import Path

from .load_sources import expects_output_on_date


FIELDS = (
    "date",
    "weekday",
    "source",
    "tracked_from",
    "frequency",
    "expected_to_publish",
    "article_count",
    "unique_articles",
    "usable_articles",
    "crawl_status",
    "monitoring_state",
    "candidates_seen",
    "pages_fetched",
    "zero_streak_days",
    "anomaly_codes",
    "anomaly_reason",
)
WEEKDAYS = ("周一", "周二", "周三", "周四", "周五", "周六", "周日")


def build_rows(stats: list[dict[str, str]]) -> list[dict[str, str]]:
    """Include every monitored day; never turn a missing run into a zero."""
    by_source: dict[str, dict[date, dict[str, str]]] = {}
    for row in stats:
        source = (row.get("source") or "").strip()
        try:
            day = date.fromisoformat(row.get("date") or "")
        except ValueError:
            continue
        if source:
            by_source.setdefault(source, {})[day] = row

    result: list[dict[str, str]] = []
    for source, dates in by_source.items():
        attempts = sorted(
            day for day, row in dates.items()
            if row.get("crawl_status") not in {"", "historical"}
        )
        if not attempts:
            continue
        first, last = attempts[0], attempts[-1]
        frequency = ""
        for day in attempts:
            if dates[day].get("frequency"):
                frequency = dates[day]["frequency"]
                break
        day = first
        while day <= last:
            row = dates.get(day, {})
            status = row.get("crawl_status") or "not_run"
            if status == "historical":
                state = "partial_archive"
            elif status == "not_run":
                state = "unverified"
            elif status == "skipped":
                state = "skipped"
            elif status in {"failed", "degraded", "zero"}:
                state = status
            elif status == "idle":
                state = "idle"
            else:
                state = "collected" if int(row.get("article_count") or 0) else "idle"
            effective_frequency = row.get("frequency") or frequency
            result.append({
                "date": day.isoformat(),
                "weekday": WEEKDAYS[day.weekday()],
                "source": source,
                "tracked_from": first.isoformat(),
                "frequency": effective_frequency,
                "expected_to_publish": str(expects_output_on_date(effective_frequency, day)).lower(),
                "article_count": row.get("article_count", ""),
                "unique_articles": row.get("unique_articles", ""),
                "usable_articles": row.get("usable_articles", ""),
                "crawl_status": status,
                "monitoring_state": state,
                "candidates_seen": row.get("candidates_seen", ""),
                "pages_fetched": row.get("pages_fetched", ""),
                "zero_streak_days": row.get("zero_streak_days", ""),
                "anomaly_codes": row.get("anomaly_codes", ""),
                "anomaly_reason": row.get("anomaly_reason", ""),
            })
            day += timedelta(days=1)
    return sorted(result, key=lambda row: (row["date"], row["source"]))


def write_counts(stats_path: Path, output_path: Path) -> int:
    with stats_path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = build_rows(list(csv.DictReader(handle)))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stats", type=Path, default=Path("logs/channel-daily-stats.csv"))
    parser.add_argument("--output", type=Path, default=Path("logs/source-daily-counts.csv"))
    args = parser.parse_args()
    print(f"Wrote {write_counts(args.stats, args.output)} source/day rows to {args.output}")


if __name__ == "__main__":
    main()
