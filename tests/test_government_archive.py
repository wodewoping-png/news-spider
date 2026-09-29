from __future__ import annotations

import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from candidate_sources.government_announcements.scrapers import NeaNoticesScraper
from src.government_archive import archive_source, attachment_links, main, safe_name
from src.http_client import FetchResult
from src.load_sources import Source


class FakeClient:
    def __init__(self, pages):
        self.pages = pages
        self.requested = []
        self.last_failure_reason = ""

    def get(self, url, **kwargs):
        self.requested.append(url)
        text = self.pages.get(url)
        if text is None:
            self.last_failure_reason = "HTTP 404"
            return None
        return FetchResult(url, text, 200, "text/html")


def source():
    return Source("国家能源局—通知", "政府机构", "能源", "政策", "工作日", "", "", "https://www.nea.gov.cn/policy/tz.htm")


class GovernmentArchiveTests(unittest.TestCase):
    def test_command_writes_csv_and_index(self):
        notice = {"title": "储能公告", "published_at": "2026-09-09", "url": "https://www.nea.gov.cn/a",
                  "content_status": "full_text", "folder": "国家能源局—通知/储能公告_123",
                  "attachments": [{"status": "downloaded", "file": "附件/储能公告_附件1.pdf"}], "errors": []}
        with tempfile.TemporaryDirectory() as temp, \
             patch("src.government_archive.load_sources", return_value=[source()]), \
             patch("src.government_archive.archive_source", return_value=({"source": source().name, "status": "ok", "notices": [notice]}, 123)):
            status = main(["--target-date", "2026-09-09", "--output-dir", temp])
            root = Path(temp) / "2026-09-09"
            self.assertEqual(status, 0)
            self.assertEqual(json.loads((root / "索引.json").read_text())["attachment_bytes"], 123)
            self.assertIn("储能公告_附件1.pdf", (root / "公告清单.csv").read_text(encoding="utf-8-sig"))

    def test_attachment_links_are_limited_to_official_body(self):
        parser = NeaNoticesScraper()
        url = "https://www.nea.gov.cn/20260909/22d62e1a042a420c846f7598589136e2/c.html"
        html = '''<nav><a href="/nav.pdf">导航附件</a></nav><span id="detailContent">
        <a href="a.pdf">附件</a><a href="http://www.nea.gov.cn/docs/b.docx">附件二</a>
        <a href="https://evil.example/x.pdf">外链</a><a href="javascript:alert(1)">错误</a>
        <a href="a.pdf">重复</a></span>'''
        links = attachment_links(parser, html, url)
        self.assertEqual([x["url"] for x in links], [
            "https://www.nea.gov.cn/20260909/22d62e1a042a420c846f7598589136e2/a.pdf",
            "https://www.nea.gov.cn/docs/b.docx",
        ])
        self.assertEqual(safe_name('测试/公告:甲'), '测试_公告_甲')

    def test_archive_writes_separate_notice_and_records_attachment_failure(self):
        parser = NeaNoticesScraper()
        detail = "https://www.nea.gov.cn/20260909/22d62e1a042a420c846f7598589136e2/c.html"
        listing = json.dumps({"datasource": [{"showTitle": "储能/通知", "publishUrl": detail, "publishTime": "2026-09-09"}]})
        html = '''<meta name="SiteName" content="国家能源局"><meta name="ArticleTitle" content="储能/通知">
        <meta name="PubDate" content="2026-09-09"><span id="detailContent"><p>通知正文</p>
        <a href="file.pdf">附件清单</a></span>'''
        client = FakeClient({parser.data_url: listing, detail: html})
        with tempfile.TemporaryDirectory() as temp, patch("src.government_archive.fetch_attachment", side_effect=ValueError("robots 未许可")):
            report, used = archive_source(source(), client, date(2026, 9, 9), Path(temp), 10_000)
            self.assertEqual(report["status"], "partial")
            self.assertEqual(used, 0)
            folders = list((Path(temp) / "国家能源局—通知").iterdir())
            self.assertEqual(len(folders), 1)
            self.assertTrue((folders[0] / "正文.txt").exists())
            notice = json.loads((folders[0] / "公告.json").read_text())
            self.assertEqual(notice["attachments"][0]["status"], "skipped")
            self.assertIn("robots", notice["attachments"][0]["reason"])
            self.assertNotIn("附件清单", (folders[0] / "正文.txt").read_text())


if __name__ == "__main__":
    unittest.main()
