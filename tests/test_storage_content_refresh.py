from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from src.storage import (
    is_better_article,
    load_existing_content_lengths,
    load_existing_content_quality,
    upsert_jsonl,
)


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
    def test_ne_time_real_headline_replaces_site_name_title(self):
        existing = article("https://www.ne-time.cn/web/article/123", "same content")
        existing["title"] = "NE时代"
        existing["source_name"] = "NE时代"
        existing["content_status"] = "full"
        candidate = dict(existing)
        candidate["title"] = "空中客车与 MTU 合作开发氢燃料电池发动机"

        self.assertTrue(is_better_article(candidate, existing))

    def test_legacy_waf_record_is_not_treated_as_verified_full_content(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "articles.jsonl"
            blocked = article(
                "https://news.bjx.com.cn/html/20260812/1.shtml",
                'appkey: "CF_APP_WAF"; var requestInfo = {"token":"redacted"};',
            )
            blocked["content_status"] = "full"
            blocked["content_extraction"] = "dom_or_structured_full_text"
            path.write_text(json.dumps(blocked) + "\n", encoding="utf-8")

            quality = load_existing_content_quality(path)
            saved = next(iter(quality.values()))
            self.assertEqual(saved["content_status"], "missing")
            self.assertEqual(saved["content_issue"], "access_challenge")

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

    def test_verified_full_content_replaces_legacy_template_noise_marked_full(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "articles.jsonl"
            original = article(
                "https://renewablesnow.com/news/example/",
                "\n".join(
                    [
                        "about 13 hours ago",
                        "about 16 hours ago",
                        "Loading...",
                        "Loading...",
                        "MESIA Business Breakfast on Smart Cities",
                        "Sep 17, 2026",
                        "Abu Dhabi",
                        "Horizons Clean Energy Expansion India Conference",
                    ]
                ),
            )
            original["content_status"] = "full"
            path.write_text(
                json.dumps(original, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            replacement = article(
                "https://renewablesnow.com/news/example/",
                "This is the verified article body. " * 25,
            )
            replacement["content_status"] = "full"
            replacement["content_issue"] = ""

            added, updated = upsert_jsonl(path, [replacement])
            saved = json.loads(path.read_text(encoding="utf-8"))

            self.assertEqual((added, updated), (0, 1))
            self.assertEqual(saved["content_status"], "full")
            self.assertNotIn("Loading", saved["content"])

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
