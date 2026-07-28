from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from src.load_sources import Source
from src.main import main


def make_source(name: str) -> Source:
    return Source(
        name=name,
        media_type="",
        domain="technology",
        sub_domain="",
        frequency="daily",
        description="",
        note="",
        url=f"https://{name}.example.com/news",
    )


class SourceFailureContinuityTests(unittest.TestCase):
    def test_one_source_failure_is_recorded_and_next_source_completes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            output = root / "data" / "articles.jsonl"
            csv_path = root / "data" / "articles-2026-07-28.csv"
            logs = root / "logs"
            sources = [make_source("broken"), make_source("healthy")]

            class FakeScraper:
                def __init__(self, _client, source):
                    self.source = source

                def scrape(self, *_args, **_kwargs):
                    if self.source.name == "broken":
                        raise TimeoutError("listing request timed out")
                    return [
                        {
                            "title": "Healthy source article",
                            "published_at": "2026-07-27T10:00:00+08:00",
                            "content": "x" * 250,
                            "url": "https://healthy.example.com/news/article",
                            "source_name": self.source.name,
                            "domain": self.source.domain,
                            "sub_domain": self.source.sub_domain,
                            "crawled_at": "2026-07-28T07:00:00+08:00",
                        }
                    ]

            args = SimpleNamespace(
                sources=root / "sources.xlsx",
                output=output,
                csv=csv_path,
                logs=logs,
                limit_per_source=20,
                candidate_limit=100,
                sleep=0,
                timeout=1,
                user_agent="test",
                ignore_robots=True,
                rollover_hour=6,
                min_content_chars=200,
                target_date="2026-07-27",
                date_filter="today",
                only_source=None,
                skip_audit=False,
            )
            audit_result = {
                "overall": {"anomaly_level": "normal", "anomaly_reason": ""},
                "anomalies": [],
            }

            def fake_setup_logging(log_dir: Path) -> Path:
                log_dir.mkdir(parents=True, exist_ok=True)
                return log_dir / "daily-news.log"

            with (
                patch("src.main.parse_args", return_value=args),
                patch("src.main.setup_logging", side_effect=fake_setup_logging),
                patch("src.main.load_sources", return_value=sources),
                patch("src.main.load_existing_urls", return_value=set()),
                patch("src.main.HttpClient", return_value=object()),
                patch("src.main.discover_feed", return_value=None),
                patch("src.main.get_scraper_class", return_value=FakeScraper),
                patch("src.main.run_daily_audit", return_value=audit_result),
            ):
                result = main()

            self.assertEqual(result, 0)
            articles = [
                json.loads(line)
                for line in output.read_text(encoding="utf-8").splitlines()
            ]
            self.assertEqual([item["source_name"] for item in articles], ["healthy"])
            self.assertTrue(csv_path.exists())

            failures = [
                json.loads(line)
                for line in (logs / "source-errors.jsonl")
                .read_text(encoding="utf-8")
                .splitlines()
            ]
            self.assertEqual(len(failures), 1)
            self.assertEqual(failures[0]["source"], "broken")
            self.assertEqual(failures[0]["target_date"], "2026-07-27")
            self.assertEqual(failures[0]["url"], sources[0].url)
            self.assertEqual(failures[0]["error_type"], "TimeoutError")
            self.assertIn("timed out", failures[0]["error"])
            occurred_at = datetime.fromisoformat(failures[0]["occurred_at"])
            self.assertIsNotNone(occurred_at.utcoffset())

            health = json.loads(
                (logs / "channel-health.json").read_text(encoding="utf-8")
            )
            statuses = {
                record["source"]: record["status"] for record in health["sources"]
            }
            self.assertEqual(statuses, {"broken": "failed", "healthy": "healthy"})
            failed_health = next(
                record for record in health["sources"] if record["source"] == "broken"
            )
            self.assertEqual(failed_health["failed_at"], failures[0]["occurred_at"])


if __name__ == "__main__":
    unittest.main()
