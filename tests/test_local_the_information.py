from __future__ import annotations

import csv
import hashlib
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from src.local_the_information import (
    LocalCaptureError,
    ingest_capture,
    load_verified_fragment,
    package_capture,
)


TARGET_DATE = date(2026, 9, 4)


def article(*, content: str = "Subscriber full text " * 60) -> dict:
    return {
        "title": "Subscriber story",
        "published_at": TARGET_DATE.isoformat(),
        "content": content,
        "content_status": "full",
        "content_issue": "",
        "content_extraction": "rss_content",
        "url": "https://www.theinformation.com/articles/subscriber-story",
        "source_name": "the information",
        "domain": "综合科技",
        "sub_domain": "科技金融",
        "crawled_at": "2026-09-05T07:15:00+08:00",
    }


def public_article() -> dict:
    return {
        **article(content="Public RSS summary with useful context."),
        "content_status": "incomplete",
        "content_issue": "rss_excerpt_only",
        "content_extraction": "rss_excerpt",
        "content_policy": "public_rss_summary",
    }


def write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(item, ensure_ascii=False) + "\n" for item in records),
        encoding="utf-8",
    )


def write_health(path: Path, *, crawl_mode: str = "rss_authenticated") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "target_date": TARGET_DATE.isoformat(),
                "sources": [
                    {
                        "source": "the information",
                        "status": "healthy",
                        "crawl_mode": crawl_mode,
                        "candidates_seen": 3,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )


class LocalTheInformationTests(unittest.TestCase):
    def test_package_requires_authenticated_feed_and_writes_manifest(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            articles = root / "capture.jsonl"
            health = root / "health.json"
            write_jsonl(articles, [article()])
            write_health(health)

            fragment, manifest_path, manifest = package_capture(
                articles, health, root / "package", TARGET_DATE
            )

            self.assertTrue(fragment.exists())
            self.assertTrue(manifest_path.exists())
            self.assertEqual(manifest["article_count"], 1)
            self.assertEqual(manifest["candidates_seen"], 3)
            self.assertEqual(
                manifest["fragment_sha256"],
                hashlib.sha256(fragment.read_bytes()).hexdigest(),
            )

    def test_package_accepts_public_reader_summary_without_claiming_full_text(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            articles = root / "capture.jsonl"
            health = root / "health.json"
            write_jsonl(articles, [public_article()])
            write_health(health, crawl_mode="rss_public_reader")

            fragment, manifest_path, manifest = package_capture(
                articles, health, root / "package", TARGET_DATE
            )

            self.assertTrue(fragment.exists())
            self.assertTrue(manifest_path.exists())
            self.assertEqual(manifest["content_policy"], "public_rss_summary")
            self.assertEqual(manifest["public_summary_articles"], 1)
            self.assertEqual(manifest["full_articles"], 0)

    def test_package_rejects_public_reader_record_without_policy_marker(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            articles = root / "capture.jsonl"
            health = root / "health.json"
            write_jsonl(articles, [article()])
            write_health(health, crawl_mode="rss_public_reader")

            with self.assertRaises(LocalCaptureError):
                package_capture(articles, health, root / "package", TARGET_DATE)

    def test_verified_fragment_rejects_tampering(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            articles = root / "capture.jsonl"
            health = root / "health.json"
            write_jsonl(articles, [article()])
            write_health(health)
            fragment, manifest, _payload = package_capture(
                articles, health, root / "package", TARGET_DATE
            )
            fragment.write_text(fragment.read_text(encoding="utf-8") + "\n", encoding="utf-8")

            with self.assertRaises(LocalCaptureError):
                load_verified_fragment(fragment, manifest, TARGET_DATE)

    def test_ingest_is_idempotent_and_exports_target_daily_csv(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            articles = root / "capture.jsonl"
            health = root / "capture-health.json"
            write_jsonl(articles, [article()])
            write_health(health)
            fragment, manifest, _payload = package_capture(
                articles, health, root / "package", TARGET_DATE
            )
            output = root / "data" / "articles.jsonl"
            csv_path = root / "data" / "articles-2026-09-05.csv"
            logs = root / "logs"

            first = ingest_capture(
                fragment,
                manifest,
                output,
                csv_path,
                logs,
                TARGET_DATE,
                classify=False,
            )
            second = ingest_capture(
                fragment,
                manifest,
                output,
                csv_path,
                logs,
                TARGET_DATE,
                classify=False,
            )

            self.assertEqual(first["added"], 1)
            self.assertEqual(second["added"], 0)
            with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["source_name"], "the information")
            local_health = json.loads(
                (logs / "local-the-information-health.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(local_health["sources"][0]["status"], "healthy")


if __name__ == "__main__":
    unittest.main()
