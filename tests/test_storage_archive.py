import json
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo

from src.date_utils import DEFAULT_TIMEZONE
from src.storage import article_lines, export_csv, upsert_jsonl


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


if __name__ == "__main__":
    unittest.main()
