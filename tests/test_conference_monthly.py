from __future__ import annotations

import csv
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from src.conference_monthly import CALLBACK, NCSTI_URL, collect, ncsti_conferences
from src.http_client import FetchResult
from src.load_sources import Source, load_sources
from src.scrapers import get_scraper_class
from src.scrapers.inew_frontier import INEWFrontierScraper


class Client:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []
        self.last_failure_reason = "timeout"

    def get(self, url, **kwargs):
        self.calls.append(url)
        body = self.responses.get(url)
        return FetchResult(url, body, 200, "text/html") if body is not None else None


def jsonp(value):
    return CALLBACK + "(" + json.dumps(value, ensure_ascii=False) + ")"


class ConferenceMonthlyTests(unittest.TestCase):
    def test_frontier_source_and_scoped_links(self):
        source = next(s for s in load_sources(Path("sources.xlsx")) if s.name == "mtl.inew.cn—学术前沿")
        self.assertIs(get_scraper_class(source.name), INEWFrontierScraper)
        client = Client({source.url: """<a href='/academic-news/detail/123?lang=zh'>研究者开发新型电池材料</a>
            <a href='/academic/conferences/123'>会议</a><a href='https://other.example/academic-news/detail/456'>站外新闻</a>"""})
        spider = INEWFrontierScraper(client, source)
        self.assertEqual(spider.discover_article_urls(10), ["https://mtl.inew.cn/academic-news/detail/123?lang=zh"])

    def test_ncsti_calendar_filters_meetings_and_deduplicates_days(self):
        base = NCSTI_URL.replace("/kjdt/", "")
        def cale(month):
            return f"{base}/kw/meeting/cale?year=2026&month={month}&callback={CALLBACK}"
        def query(day):
            return f"{base}/kw/meeting/query?channelId=79&datetime={day}&marktime=&order=&curpage=1&callback={CALLBACK}"
        event_url = f"{base}/kcfw/hy/202610/t20261010_258045.html"
        responses = {
            cale(10): jsonp([{"datetime": "2026-10-30", "ChannelId": "79"}, {"datetime": "2026-10-30", "ChannelId": "79"}, {"datetime": "2026-10-29", "ChannelId": "80"}]),
            cale(11): jsonp([]),
            query("2026-10-30"): jsonp({"curpage": 1, "pageCount": 1, "resultList": [
                {"ChannelId": "79", "datetime": "2026-10-30", "doctitle": "能源工程国际会议", "place": "深圳", "DOCPUBURL": event_url, "content": "<p>会议简介</p>"},
                {"ChannelId": "80", "datetime": "2026-10-30", "doctitle": "非会议活动", "DOCPUBURL": f"{base}/other"},
            ]}),
        }
        client = Client(responses)
        rows = ncsti_conferences(client, date(2026, 10, 1))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["会议名称"], "能源工程国际会议")
        self.assertEqual(rows[0]["会议简介"], "会议简介")
        self.assertEqual(client.calls.count(query("2026-10-30")), 1)

    def test_snapshot_reports_unavailable_source_instead_of_zero_events(self):
        base = NCSTI_URL.replace("/kjdt/", "")
        client = Client({
            f"{base}/kw/meeting/cale?year=2026&month=10&callback={CALLBACK}": jsonp([]),
            f"{base}/kw/meeting/cale?year=2026&month=11&callback={CALLBACK}": jsonp([]),
        })
        with tempfile.TemporaryDirectory() as temp:
            index = collect(date(2026, 10, 1), Path(temp), client)
            self.assertEqual(index["sources"][0]["status"], "failed")
            self.assertEqual(index["sources"][1]["status"], "ok")
            destination = Path(temp) / "2026-10"
            self.assertEqual(json.loads((destination / "索引.json").read_text())["sources"][0]["status"], "failed")
            with (destination / "会议清单.csv").open(encoding="utf-8-sig") as handle:
                self.assertEqual(len(list(csv.DictReader(handle))), 0)


if __name__ == "__main__":
    unittest.main()
