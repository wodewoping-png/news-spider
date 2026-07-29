from __future__ import annotations

import csv
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from src.audit import run_daily_audit


def article(day: str, source: str, index: int) -> dict:
    return {
        "title": f"{source}-{day}-{index}",
        "published_at": f"{day}T12:00:00+08:00",
        "content": "x" * 250,
        "url": f"https://example.com/{source}/{day}/{index}",
        "source_name": source,
    }


def health(source: str, status: str, frequency: str = "每日") -> dict:
    return {
        "source": source,
        "frequency": frequency,
        "status": status,
        "candidates_seen": 10,
        "pages_fetched": 5,
    }


class DailyAuditTests(unittest.TestCase):
    def write_articles(self, path: Path, rows: list[dict]) -> None:
        path.write_text(
            "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
            encoding="utf-8",
        )

    def test_zero_alert_is_idempotent_and_escalates_after_two_days(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            data = root / "articles.jsonl"
            logs = root / "logs"
            rows = [
                *(article("2026-07-20", "Daily", index) for index in range(3)),
                *(article("2026-07-21", "Daily", index) for index in range(4)),
            ]
            self.write_articles(data, rows)

            first = run_daily_audit(
                data,
                logs,
                date(2026, 7, 22),
                [health("Daily", "zero")],
            )
            self.assertIn("sudden_zero", first["anomalies"][0]["anomaly_codes"])
            self.assertEqual(first["anomalies"][0]["zero_streak_days"], 1)

            run_daily_audit(
                data,
                logs,
                date(2026, 7, 22),
                [health("Daily", "zero")],
            )
            with (logs / "channel-daily-stats.csv").open(
                "r", encoding="utf-8-sig", newline=""
            ) as handle:
                saved = list(csv.DictReader(handle))
            current = [
                row
                for row in saved
                if row["date"] == "2026-07-22" and row["source"] == "Daily"
            ]
            self.assertEqual(len(current), 1)

            second = run_daily_audit(
                data,
                logs,
                date(2026, 7, 23),
                [health("Daily", "zero")],
            )
            self.assertIn("zero_2d", second["anomalies"][0]["anomaly_codes"])
            self.assertEqual(second["anomalies"][0]["zero_streak_days"], 2)

    def test_channel_surge_and_low_frequency_idle(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            data = root / "articles.jsonl"
            logs = root / "logs"
            rows = [
                *(article("2026-07-20", "Daily", index) for index in range(3)),
                *(article("2026-07-21", "Daily", index) for index in range(3)),
                *(article("2026-07-22", "Daily", index) for index in range(8)),
                *(article("2026-07-21", "Weekly", index) for index in range(2)),
            ]
            self.write_articles(data, rows)

            report = run_daily_audit(
                data,
                logs,
                date(2026, 7, 22),
                [
                    health("Daily", "healthy"),
                    health("Weekly", "idle", "每周"),
                ],
            )
            by_source = {row["source"]: row for row in report["anomalies"]}
            self.assertIn("surge_2x", by_source["Daily"]["anomaly_codes"])
            self.assertNotIn("Weekly", by_source)
            self.assertTrue((logs / "daily-collection-summary.csv").exists())
            self.assertTrue((logs / "channel-daily-volume.csv").exists())
            self.assertTrue((logs / "audit-report.md").exists())

            rerun = run_daily_audit(
                data,
                logs,
                date(2026, 7, 22),
                [
                    health("Daily", "zero"),
                    health("Weekly", "idle", "每周"),
                ],
            )
            self.assertEqual(rerun["overall"]["zero_sources"], 0)
            with (logs / "channel-daily-stats.csv").open(
                "r", encoding="utf-8-sig", newline=""
            ) as handle:
                saved = list(csv.DictReader(handle))
            daily = next(
                row
                for row in saved
                if row["date"] == "2026-07-22" and row["source"] == "Daily"
            )
            self.assertEqual(daily["crawl_status"], "already_collected")

    def test_workday_source_is_not_zero_anomaly_on_weekend(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            data = root / "articles.jsonl"
            logs = root / "logs"
            rows = [
                *(article("2026-07-23", "Weekday", index) for index in range(2)),
                *(article("2026-07-24", "Weekday", index) for index in range(3)),
            ]
            self.write_articles(data, rows)

            report = run_daily_audit(
                data,
                logs,
                date(2026, 7, 25),
                [health("Weekday", "idle", "工作日")],
            )

            by_source = {row["source"]: row for row in report["anomalies"]}
            self.assertNotIn("Weekday", by_source)
            self.assertEqual(report["overall"]["zero_sources"], 0)

    def test_content_character_distribution_is_recorded(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            data = root / "articles.jsonl"
            logs = root / "logs"
            rows = [
                {
                    **article("2026-07-28", "Daily", 1),
                    "content": "x" * 120,
                    "content_status": "full",
                },
                {
                    **article("2026-07-28", "Daily", 2),
                    "content": "x" * 800,
                    "content_status": "full",
                },
            ]
            self.write_articles(data, rows)

            run_daily_audit(
                data,
                logs,
                date(2026, 7, 28),
                [health("Daily", "degraded")],
                min_content_chars=500,
            )

            with (logs / "channel-daily-stats.csv").open(
                "r", encoding="utf-8-sig", newline=""
            ) as handle:
                saved = list(csv.DictReader(handle))
            daily = next(
                row
                for row in saved
                if row["date"] == "2026-07-28" and row["source"] == "Daily"
            )
            self.assertEqual(daily["usable_articles"], "2")
            self.assertEqual(daily["incomplete_articles"], "0")
            self.assertEqual(daily["short_articles"], "1")
            self.assertEqual(daily["content_chars_min"], "120")
            self.assertEqual(daily["content_chars_median"], "460")
            self.assertEqual(daily["content_chars_max"], "800")


if __name__ == "__main__":
    unittest.main()
