from __future__ import annotations

import csv
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from src.audit import run_daily_audit
from src.recovery import load_queue


class RecoveryAuditIntegrationTests(unittest.TestCase):
    def test_audit_opens_incident_and_refreshes_recovered_history(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            data = root / "articles.jsonl"
            logs = root / "logs"
            data.write_text("", encoding="utf-8")
            health = [
                {
                    "source": "Daily",
                    "frequency": "每日",
                    "status": "zero",
                    "reason": "no target-date articles were collected",
                    "candidates_seen": 0,
                    "pages_fetched": 0,
                }
            ]

            report = run_daily_audit(data, logs, date(2026, 7, 22), health)
            self.assertEqual(report["recovery"]["pending_confirmation"], 1)
            incident = load_queue(logs / "recovery-queue.json")["incidents"][0]
            self.assertEqual(incident["date"], "2026-07-22")

            article = {
                "title": "Backfilled",
                "published_at": "2026-07-22T12:00:00+08:00",
                "content": "x" * 250,
                "url": "https://example.com/backfilled",
                "source_name": "Daily",
            }
            data.write_text(
                json.dumps(article, ensure_ascii=False) + "\n", encoding="utf-8"
            )
            run_daily_audit(data, logs, date(2026, 7, 23), health)

            incidents = load_queue(logs / "recovery-queue.json")["incidents"]
            recovered = next(item for item in incidents if item["date"] == "2026-07-22")
            self.assertEqual(recovered["status"], "recovered")
            with (logs / "channel-daily-stats.csv").open(
                "r", encoding="utf-8-sig", newline=""
            ) as handle:
                rows = list(csv.DictReader(handle))
            old_row = next(
                row
                for row in rows
                if row["date"] == "2026-07-22" and row["source"] == "Daily"
            )
            self.assertEqual(old_row["article_count"], "1")
            self.assertEqual(old_row["crawl_status"], "recovered")


if __name__ == "__main__":
    unittest.main()
