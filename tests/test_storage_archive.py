import json
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo

from src.date_utils import DEFAULT_TIMEZONE
from src.storage import article_lines, export_csv, upsert_jsonl
from src.recovery import run_confirmed_recoveries, save_queue


class WeeklyArchiveTest(unittest.TestCase):
    def test_rollover_keeps_old_article_readable_and_refreshable(self):
        old = (datetime.now(ZoneInfo(DEFAULT_TIMEZONE)).date() - timedelta(days=21)).isoformat()
        with tempfile.TemporaryDirectory() as directory:
            journal = Path(directory) / "articles.jsonl"
            old_article = {
                "title": "Old",
                "url": "https://example.org/old",
                "source_name": "Example",
                "published_at": old,
                "content": "short",
                "content_status": "full",
            }
            journal.write_text(json.dumps(old_article) + "\n", encoding="utf-8")
            with patch("src.storage.ARCHIVE_THRESHOLD_BYTES", 1):
                upsert_jsonl(journal, [{**old_article, "content": "A much longer full article"}])
            archived = list((journal.parent / "archive").glob("*.jsonl"))
            self.assertEqual(len(archived), 1)
            rows = [json.loads(line) for line in article_lines(journal)]
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["content"], "A much longer full article")
            csv_path = journal.parent / "daily.csv"
            export_csv(journal, csv_path)
            self.assertIn("A much longer full article", csv_path.read_text(encoding="utf-8-sig"))

    def test_empty_historical_day_is_ignored_without_overwriting_daily_health(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            logs = root / "logs"
            logs.mkdir()
            daily_health = logs / "channel-health.json"
            daily_health.write_text('{"sources": [{"source": "Daily"}]}', encoding="utf-8")
            queue = logs / "recovery-queue.json"
            save_queue(queue, {"incidents": [{
                "date": "2026-10-20", "source": "Example", "status": "confirmed"
            }]})

            def runner(command):
                attempt = Path(command[command.index("--logs") + 1])
                attempt.mkdir(parents=True, exist_ok=True)
                (attempt / "channel-health.json").write_text(json.dumps({
                    "sources": [{"source": "Example", "status": "idle",
                                 "reason": "all observed candidates were published outside the target date"}]
                }), encoding="utf-8")
                return 0

            rows = run_confirmed_recoveries(
                queue, sources_path=root / "sources.xlsx",
                output_path=root / "articles.jsonl", logs_dir=logs,
                command_runner=runner,
            )
            self.assertEqual(rows[0]["status"], "ignored")
            self.assertIn('"Daily"', daily_health.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
