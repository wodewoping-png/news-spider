from __future__ import annotations

import csv
import tempfile
import unittest
from datetime import date
from pathlib import Path

from src.audit import run_daily_audit
from src.source_daily_counts import build_rows


class SourceDailyCountTests(unittest.TestCase):
    def test_missing_run_is_distinct_from_zero_and_historical_backfill(self):
        rows = build_rows([
            {"date": "2026-10-19", "source": "A", "frequency": "工作日", "crawl_status": "healthy", "article_count": "2"},
            {"date": "2026-10-20", "source": "A", "frequency": "工作日", "crawl_status": "historical", "article_count": "1"},
            {"date": "2026-10-21", "source": "A", "frequency": "工作日", "crawl_status": "zero", "article_count": "0"},
            {"date": "2026-10-19", "source": "B", "frequency": "每日", "crawl_status": "idle", "article_count": "0"},
            {"date": "2026-10-21", "source": "B", "frequency": "每日", "crawl_status": "healthy", "article_count": "3"},
            {"date": "2026-10-18", "source": "C", "crawl_status": "historical", "article_count": "1"},
        ])
        by_key = {(row["date"], row["source"]): row for row in rows}
        self.assertEqual(len(rows), 6)
        self.assertEqual(by_key["2026-10-20", "A"]["monitoring_state"], "partial_archive")
        self.assertEqual(by_key["2026-10-20", "A"]["article_count"], "1")
        self.assertEqual(by_key["2026-10-20", "B"]["monitoring_state"], "unverified")
        self.assertEqual(by_key["2026-10-20", "B"]["article_count"], "")
        self.assertEqual(by_key["2026-10-21", "A"]["article_count"], "0")
        self.assertNotIn(("2026-10-18", "C"), by_key)

    def test_audit_updates_long_table_on_rerun(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            data = root / "articles.jsonl"
            data.write_text("", encoding="utf-8")
            logs = root / "logs"
            health = [{"source": "A", "status": "zero", "frequency": "每日"}]
            run_daily_audit(data, logs, date(2026, 10, 19), health)
            run_daily_audit(data, logs, date(2026, 10, 21), health)
            path = logs / "source-daily-counts.csv"
            with path.open(encoding="utf-8-sig", newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual([row["article_count"] for row in rows], ["0", "", "0"])
            self.assertEqual(rows[1]["crawl_status"], "not_run")
            self.assertEqual(rows[1]["monitoring_state"], "unverified")
            run_daily_audit(data, logs, date(2026, 10, 20), health)
            with path.open(encoding="utf-8-sig", newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(len(rows), 3)
            self.assertEqual(rows[1]["article_count"], "0")
            self.assertEqual(rows[1]["monitoring_state"], "zero")


if __name__ == "__main__":
    unittest.main()
