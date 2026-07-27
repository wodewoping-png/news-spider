from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from src.recovery import (
    diagnose_incident,
    load_queue,
    run_confirmed_recoveries,
    sync_recovery_queue,
    update_incidents,
)


class RecoveryQueueTests(unittest.TestCase):
    def test_sync_creates_diagnosed_incident_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as temp:
            queue = Path(temp) / "recovery-queue.json"
            row = {
                "date": "2026-07-22",
                "source": "Daily",
                "frequency": "每日",
                "expected_daily": "true",
                "crawl_status": "zero",
                "article_count": 0,
                "anomaly_level": "critical",
                "anomaly_codes": "sudden_zero",
                "candidates_seen": 12,
                "pages_fetched": 0,
            }
            health = {
                "source": "Daily",
                "status": "zero",
                "candidates_seen": 12,
                "pages_fetched": 0,
                "reason": "no target-date articles were collected",
            }

            sync_recovery_queue(
                queue, [row], [health], generated_at="2026-07-23T06:00:00+08:00"
            )
            payload = sync_recovery_queue(
                queue, [row], [health], generated_at="2026-07-23T07:00:00+08:00"
            )

            self.assertEqual(len(payload["incidents"]), 1)
            incident = payload["incidents"][0]
            self.assertEqual(incident["status"], "pending_confirmation")
            self.assertEqual(incident["diagnosis_code"], "candidates_filtered")
            self.assertIn("日期过滤", incident["diagnosis"])

    def test_failure_reason_classification(self):
        code, reason = diagnose_incident(
            {"crawl_status": "failed"},
            {"reason": "HTTPSConnectionPool: Read timed out"},
        )
        self.assertEqual(code, "timeout")
        self.assertIn("超时", reason)

    def test_human_confirmation_and_successful_backfill(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            queue = root / "logs" / "recovery-queue.json"
            output = root / "data" / "articles.jsonl"
            logs = root / "logs"
            sync_recovery_queue(
                queue,
                [
                    {
                        "date": "2026-07-22",
                        "source": "Daily",
                        "frequency": "每日",
                        "expected_daily": "true",
                        "crawl_status": "zero",
                        "article_count": 0,
                        "candidates_seen": 0,
                        "pages_fetched": 0,
                    }
                ],
                [{"source": "Daily", "status": "zero"}],
            )
            changed = update_incidents(
                queue,
                "Daily",
                "confirm",
                note="已修复列表选择器",
                timestamp="2026-07-23T08:00:00+08:00",
            )
            self.assertEqual(changed[0]["status"], "confirmed")

            def fake_runner(command: list[str]) -> int:
                self.assertIn("--only-source", command)
                self.assertIn("2026-07-22", command)
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_text(
                    json.dumps(
                        {
                            "title": "recovered",
                            "published_at": "2026-07-22T12:00:00+08:00",
                            "content": "x" * 250,
                            "url": "https://example.com/recovered",
                            "source_name": "Daily",
                        }
                    )
                    + "\n",
                    encoding="utf-8",
                )
                return 0

            processed = run_confirmed_recoveries(
                queue,
                sources_path=root / "sources.xlsx",
                output_path=output,
                logs_dir=logs,
                command_runner=fake_runner,
                timestamp="2026-07-23T09:00:00+08:00",
            )

            self.assertEqual(processed[0]["status"], "recovered")
            self.assertEqual(processed[0]["recovered_articles"], 1)
            saved = load_queue(queue)["incidents"][0]
            self.assertEqual(saved["attempts"], 1)
            self.assertEqual(saved["confirmation_note"], "已修复列表选择器")

    def test_failed_backfill_requires_another_confirmation(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            queue = root / "logs" / "recovery-queue.json"
            sync_recovery_queue(
                queue,
                [
                    {
                        "date": "2026-07-22",
                        "source": "Daily",
                        "frequency": "每日",
                        "expected_daily": "true",
                        "crawl_status": "failed",
                        "article_count": 0,
                    }
                ],
                [{"source": "Daily", "status": "failed", "reason": "HTTP 403"}],
            )
            update_incidents(queue, "Daily", "confirm", note="已调整请求头")

            processed = run_confirmed_recoveries(
                queue,
                sources_path=root / "sources.xlsx",
                output_path=root / "data" / "articles.jsonl",
                logs_dir=root / "logs",
                command_runner=lambda _command: 1,
            )

            self.assertEqual(processed[0]["status"], "recovery_failed")
            self.assertIn("退出码", processed[0]["last_error"])


if __name__ == "__main__":
    unittest.main()
