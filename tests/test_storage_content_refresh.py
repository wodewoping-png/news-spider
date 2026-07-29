from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from src.storage import load_existing_content_lengths, upsert_jsonl


def article(url: str, content: str) -> dict:
    return {
        "title": url,
        "published_at": "2026-07-28T12:00:00+08:00",
        "content": content,
        "url": url,
        "source_name": "Example",
        "domain": "",
        "sub_domain": "",
        "crawled_at": "2026-07-29T00:00:00+00:00",
    }


class StorageContentRefreshTests(unittest.TestCase):
    def test_existing_content_is_replaced_only_when_longer(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "articles.jsonl"
            original = article("https://example.com/story", "short body")
            path.write_text(
                json.dumps(original, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )

            added, updated = upsert_jsonl(
                path,
                [article("https://example.com/story", "x" * 800)],
            )

            self.assertEqual((added, updated), (0, 1))
            saved = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(len(saved["content"]), 800)
            self.assertEqual(
                load_existing_content_lengths(path),
                {"https://example.com/story": 800},
            )

            added, updated = upsert_jsonl(
                path,
                [article("https://example.com/story", "tiny")],
            )
            self.assertEqual((added, updated), (0, 0))
            saved = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(len(saved["content"]), 800)

    def test_verified_full_content_replaces_longer_incomplete_excerpt(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "articles.jsonl"
            original = article("https://example.com/story", "x" * 1200)
            original["content_status"] = "incomplete"
            original["content_issue"] = "rss_excerpt_only"
            path.write_text(
                json.dumps(original, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            replacement = article("https://example.com/story", "y" * 900)
            replacement["content_status"] = "full"
            replacement["content_issue"] = ""

            added, updated = upsert_jsonl(path, [replacement])
            saved = json.loads(path.read_text(encoding="utf-8"))

            self.assertEqual((added, updated), (0, 1))
            self.assertEqual(saved["content_status"], "full")
            self.assertEqual(len(saved["content"]), 900)

    def test_short_incomplete_result_does_not_replace_long_legacy_record(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "articles.jsonl"
            original = article("https://example.com/story", "x" * 1200)
            path.write_text(
                json.dumps(original, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            replacement = article(
                "https://example.com/story",
                "Subscribe to unlock",
            )
            replacement["content_status"] = "incomplete"
            replacement["content_issue"] = "paywall_or_login_wall"

            added, updated = upsert_jsonl(path, [replacement])
            saved = json.loads(path.read_text(encoding="utf-8"))

            self.assertEqual((added, updated), (0, 0))
            self.assertEqual(len(saved["content"]), 1200)

    def test_new_url_is_appended_without_duplicate(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "articles.jsonl"

            first = upsert_jsonl(
                path,
                [article("https://example.com/new", "complete body")],
            )
            second = upsert_jsonl(
                path,
                [article("http://www.example.com/new/", "complete body")],
            )

            self.assertEqual(first, (1, 0))
            self.assertEqual(second, (0, 0))
            self.assertEqual(
                len(path.read_text(encoding="utf-8").splitlines()),
                1,
            )


if __name__ == "__main__":
    unittest.main()
