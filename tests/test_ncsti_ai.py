from __future__ import annotations

import unittest
from datetime import date
from pathlib import Path

from src.article_parser import parse_article_html
from src.http_client import FetchResult
from src.load_sources import Source, load_sources
from src.scrapers import get_scraper_class
from src.scrapers.ncsti_ai import NCSTIArtificialIntelligenceScraper


URL = "https://www.ncsti.gov.cn/kjdt/kjrd/rgzn_kjrd/"


class StaticClient:
    def __init__(self, pages: dict[str, str]):
        self.pages = pages
        self.calls: list[str] = []

    def get(self, url: str, **kwargs):
        self.calls.append(url)
        page = self.pages.get(url)
        return FetchResult(url, page, 200, "text/html") if page is not None else None


class NCSTIChannelTests(unittest.TestCase):
    @staticmethod
    def source():
        return Source("北京国际科技创新中心—人工智能热点", "政府科技资讯平台", "AI与智能科技", "人工智能科技热点", "工作日", "", "", URL)

    def test_workbook_and_registry(self):
        sources = [source for source in load_sources(Path("sources.xlsx")) if source.name == self.source().name]
        self.assertEqual(len(sources), 1)
        self.assertEqual(sources[0].url, URL)
        self.assertIs(get_scraper_class(sources[0].name), NCSTIArtificialIntelligenceScraper)

    def test_listing_is_restricted_to_its_dated_articles_and_pages(self):
        first = """<a href='./202610/t20261029_259934.html'><h2><span class='i-time'>2026-10-29</span>全国首个城市级算电协同平台投运</h2></a>
        <a href='../yyjk_kjrd/202610/t20261029_259000.html'>医药健康栏目</a>
        <a href='https://other.example/kjdt/kjrd/rgzn_kjrd/202610/t20261029_259001.html'>外站</a>"""
        second = """<a href='./202610/t20261028_259662.html'><h2><span class='i-time'>2026-10-28</span>光子技术突破</h2></a>
        <a href='./202610/t20261027_259123.html'><h2>旧闻</h2></a>"""
        client = StaticClient({URL + "index.html": first, URL + "index_1.html": second})
        scraper = NCSTIArtificialIntelligenceScraper(client, self.source())
        scraper._requested_target_date = date(2026, 10, 28)
        urls = scraper.discover_article_urls(20)
        self.assertEqual(len(urls), 3)
        self.assertEqual(scraper.listing_candidate_titles[urls[0]], "全国首个城市级算电协同平台投运")
        self.assertEqual(client.calls, [URL + "index.html", URL + "index_1.html"])

    def test_body_and_date_use_official_article_not_page_navigation(self):
        url = URL + "202610/t20261029_259934.html"
        html = """<h1>全国首个城市级算电协同平台投运</h1><div class='nav'>栏目导航</div>
            <div class='trs_editor_view TRS_UEDITOR'><p>扬州城市级算电协同平台正式投运，接入多个算力资源池。</p><p>平台把算力需求与绿电供应联动。</p></div>
            <div class='recommend'><p>站点推荐内容不得进入正文。</p></div>"""
        article = parse_article_html(html, url, self.source())
        self.assertEqual(article["published_at"], "2026-10-29")
        self.assertIn("绿电供应", article["content"])
        self.assertNotIn("栏目导航", article["content"])
        self.assertNotIn("站点推荐", article["content"])


if __name__ == "__main__":
    unittest.main()
