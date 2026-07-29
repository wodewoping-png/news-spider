from __future__ import annotations

import json
import csv
import tempfile
import unittest
from pathlib import Path

from src.channel_ops import reconcile, run_cycle
from src.recovery import save_queue


def write_health(
    path: Path,
    *,
    generated_at: str,
    target_date: str,
    status: str,
    reason: str = "",
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "generated_at": generated_at,
                "target_date": target_date,
                "sources": [
                    {
                        "source": "Daily",
                        "frequency": "每日",
                        "status": status,
                        "reason": reason,
                        "error_type": "TimeoutError" if status == "failed" else "",
                        "crawl_mode": "rss",
                        "candidates_seen": 5,
                        "pages_fetched": 2,
                        "new_articles": 1 if status == "healthy" else 0,
                        "usable_articles": 1 if status == "healthy" else 0,
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


class ChannelOperationsTests(unittest.TestCase):
    def test_reconcile_creates_idempotent_sanitized_operations_ledger(self):
        with tempfile.TemporaryDirectory() as temp:
            logs = Path(temp) / "logs"
            write_health(
                logs / "channel-health.json",
                generated_at="2026-07-29T06:00:00+08:00",
                target_date="2026-07-28",
                status="failed",
                reason="HTTP 401 password=should-not-be-stored",
            )
            save_queue(
                logs / "recovery-queue.json",
                {
                    "incidents": [
                        {
                            "id": "2026-07-28::Daily",
                            "date": "2026-07-28",
                            "source": "Daily",
                            "status": "pending_confirmation",
                            "diagnosis": "认证失败",
                        }
                    ]
                },
            )

            first = reconcile(
                logs,
                timestamp="2026-07-29T06:01:00+08:00",
            )
            second = reconcile(
                logs,
                timestamp="2026-07-29T06:02:00+08:00",
            )

            self.assertEqual(first["summary"]["unhealthy"], 1)
            self.assertEqual(second["summary"]["open_incidents"], 1)
            state = json.loads(
                (logs / "channel-ops-state.json").read_text(encoding="utf-8")
            )
            channel = state["channels"]["Daily"]
            self.assertEqual(channel["next_action"], "repair_then_confirm")
            self.assertEqual(channel["consecutive_unhealthy"], 1)
            self.assertNotIn("should-not-be-stored", channel["last_error"])
            events = (logs / "channel-operations.jsonl").read_text(
                encoding="utf-8"
            ).splitlines()
            self.assertEqual(len(events), 1)
            self.assertTrue((logs / "channel-operations.csv").exists())
            self.assertTrue((logs / "channel-ops-report.md").exists())

    def test_reconcile_records_recovery_and_resets_unhealthy_streak(self):
        with tempfile.TemporaryDirectory() as temp:
            logs = Path(temp) / "logs"
            write_health(
                logs / "channel-health.json",
                generated_at="2026-07-29T06:00:00+08:00",
                target_date="2026-07-28",
                status="failed",
                reason="timed out",
            )
            reconcile(logs, timestamp="2026-07-29T06:01:00+08:00")
            write_health(
                logs / "channel-health.json",
                generated_at="2026-07-29T07:00:00+08:00",
                target_date="2026-07-28",
                status="healthy",
            )

            report = reconcile(
                logs,
                timestamp="2026-07-29T07:01:00+08:00",
            )

            channel = report["channels"][0]
            self.assertEqual(channel["previous_status"], "failed")
            self.assertEqual(channel["last_status"], "healthy")
            self.assertEqual(channel["consecutive_unhealthy"], 0)
            self.assertEqual(channel["last_success_date"], "2026-07-28")
            self.assertEqual(channel["next_action"], "none")
            events = (logs / "channel-operations.jsonl").read_text(
                encoding="utf-8"
            ).splitlines()
            self.assertEqual(len(events), 2)

    def test_human_verified_no_news_closes_action_without_false_failure(self):
        with tempfile.TemporaryDirectory() as temp:
            logs = Path(temp) / "logs"
            write_health(
                logs / "channel-health.json",
                generated_at="2026-07-29T06:00:00+08:00",
                target_date="2026-07-28",
                status="zero",
                reason="no target-date articles were collected",
            )
            save_queue(
                logs / "recovery-queue.json",
                {
                    "incidents": [
                        {
                            "id": "2026-07-28::Daily",
                            "date": "2026-07-28",
                            "source": "Daily",
                            "status": "ignored",
                            "confirmation_note": "官网当天无新闻",
                        }
                    ]
                },
            )

            report = reconcile(logs)

            channel = report["channels"][0]
            self.assertEqual(channel["last_status"], "verified_no_news")
            self.assertEqual(channel["next_action"], "none")
            self.assertEqual(report["summary"]["unhealthy"], 0)

    def test_missing_scheduled_run_date_creates_recovery_incident(self):
        with tempfile.TemporaryDirectory() as temp:
            logs = Path(temp) / "logs"
            logs.mkdir(parents=True)
            with (logs / "channel-daily-stats.csv").open(
                "w", encoding="utf-8-sig", newline=""
            ) as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=("date", "source", "frequency", "crawl_status"),
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "date": "2026-07-26",
                        "source": "Daily",
                        "frequency": "每日",
                        "crawl_status": "healthy",
                    }
                )
                writer.writerow(
                    {
                        "date": "2026-07-28",
                        "source": "Daily",
                        "frequency": "每日",
                        "crawl_status": "healthy",
                    }
                )
            with (logs / "daily-collection-summary.csv").open(
                "w", encoding="utf-8-sig", newline=""
            ) as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=("date", "sources_configured"),
                )
                writer.writeheader()
                writer.writerow(
                    {"date": "2026-07-26", "sources_configured": 1}
                )
                writer.writerow(
                    {"date": "2026-07-28", "sources_configured": 1}
                )
            write_health(
                logs / "channel-health.json",
                generated_at="2026-07-29T06:00:00+08:00",
                target_date="2026-07-28",
                status="healthy",
            )

            report = reconcile(logs)

            incidents = json.loads(
                (logs / "recovery-queue.json").read_text(encoding="utf-8")
            )["incidents"]
            gap = next(item for item in incidents if item["date"] == "2026-07-27")
            self.assertEqual(gap["diagnosis_code"], "missing_run_record")
            self.assertEqual(gap["status"], "pending_confirmation")
            self.assertEqual(report["summary"]["open_incidents"], 1)
            events = [
                json.loads(line)
                for line in (logs / "channel-operations.jsonl")
                .read_text(encoding="utf-8")
                .splitlines()
            ]
            self.assertEqual(
                len([event for event in events if event["status"] == "missing_run"]),
                1,
            )

    def test_historical_inventory_dates_do_not_create_false_run_gaps(self):
        with tempfile.TemporaryDirectory() as temp:
            logs = Path(temp) / "logs"
            logs.mkdir(parents=True)
            with (logs / "channel-daily-stats.csv").open(
                "w", encoding="utf-8-sig", newline=""
            ) as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=("date", "source", "frequency", "crawl_status"),
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "date": "2026-06-01",
                        "source": "Daily",
                        "frequency": "每日",
                        "crawl_status": "historical",
                    }
                )
                writer.writerow(
                    {
                        "date": "2026-07-28",
                        "source": "Daily",
                        "frequency": "每日",
                        "crawl_status": "healthy",
                    }
                )
            with (logs / "daily-collection-summary.csv").open(
                "w", encoding="utf-8-sig", newline=""
            ) as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=("date", "sources_configured"),
                )
                writer.writeheader()
                writer.writerow(
                    {"date": "2026-06-01", "sources_configured": ""}
                )
                writer.writerow(
                    {"date": "2026-07-28", "sources_configured": 1}
                )
            write_health(
                logs / "channel-health.json",
                generated_at="2026-07-29T06:00:00+08:00",
                target_date="2026-07-28",
                status="healthy",
            )

            report = reconcile(logs)

            self.assertEqual(report["summary"]["open_incidents"], 0)
            self.assertFalse((logs / "recovery-queue.json").exists())

    def test_cycle_runs_crawler_then_reconciles_even_with_no_notifications(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            logs = root / "logs"
            commands: list[list[str]] = []

            def runner(command: list[str]) -> int:
                commands.append(command)
                write_health(
                    logs / "channel-health.json",
                    generated_at="2026-07-29T06:00:00+08:00",
                    target_date="2026-07-28",
                    status="healthy",
                )
                return 0

            result = run_cycle(
                sources_path=root / "sources.xlsx",
                output_path=root / "data" / "articles.jsonl",
                logs_dir=logs,
                target_date="2026-07-28",
                command_runner=runner,
                send_notifications=False,
            )

            self.assertEqual(result, 0)
            self.assertEqual(len(commands), 1)
            self.assertIn("--target-date", commands[0])
            self.assertTrue((logs / "channel-ops-report.json").exists())


if __name__ == "__main__":
    unittest.main()
