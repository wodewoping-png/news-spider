from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

import requests

from src.article_parser import parse_article_html
from src.http_client import FetchResult, HttpClient
from src.load_sources import Source, load_sources
from src.scrapers import get_scraper_class
from src.scrapers.cnpc_news import CNPCRefiningNewsScraper
from src.scrapers.ieee_spectrum import IEEESpectrumScraper


def source(name: str, url: str) -> Source:
    return Source(name, "行业媒体", "综合科技", "", "每日", "", "", url)


class StaticClient:
    def __init__(self, html: str, url: str):
        self.html, self.url = html, url

    def get(self, url: str, **kwargs):
        return FetchResult(self.url, self.html, 200, "text/html")


class CNPCIEEEChannelTests(unittest.TestCase):
    def test_source_registry_and_official_feed(self):
        sources = {item.name: item for item in load_sources(Path("sources.xlsx"))}
        self.assertIs(get_scraper_class("中国石油新闻中心—炼化新材料"), CNPCRefiningNewsScraper)
        self.assertIs(get_scraper_class("IEEE Spectrum"), IEEESpectrumScraper)
        self.assertEqual(sources["IEEE Spectrum"].configured_rss_url, "https://spectrum.ieee.org/feeds/feed.rss")

    def test_cnpc_listing_only_uses_dated_articles_on_own_host(self):
        listing = """<a href='http://news.cnpc.com.cn/system/2026/10/21/030205424.shtml'>零碳工厂</a>
            <a href='https://news.cnpc.com.cn/zongh/index.shtml'>集团要闻</a>
            <a href='https://unrelated.example/system/2026/10/21/123.shtml'>站外稿件</a>"""
        url = "https://news.cnpc.com.cn/cnpcnews/lyhg/index.shtml"
        scraper = CNPCRefiningNewsScraper(StaticClient(listing, url), source("中国石油新闻中心—炼化新材料", url))
        self.assertEqual(scraper.discover_article_urls(10), ["https://news.cnpc.com.cn/system/2026/10/21/030205424.shtml"])

    def test_cnpc_html_without_mime_type_is_read_and_body_is_bounded(self):
        response = requests.Response()
        response.status_code = 200
        response.url = "https://news.cnpc.com.cn/system/2026/10/21/030205424.shtml"
        response._content = b"<!doctype html><html><body><p>text</p></body></html>"
        client = HttpClient(sleep_seconds=0, respect_robots=False)
        with patch.object(client.session, "get", return_value=response):
            self.assertIsNotNone(client.get(response.url, allow_non_html=False))
        html = """<title>零碳工厂-中国石油新闻中心-中国石油新闻中心</title>
            <div class='sj-main'><div class='as04'><p>炼化与新材料建设取得进展。</p></div></div>
            <div class='n_side'>站点热门与推荐内容</div>"""
        article = parse_article_html(html, response.url, source("中国石油新闻中心—炼化新材料", ""))
        self.assertEqual(article["title"], "零碳工厂")
        self.assertNotIn("站点热门", article["content"])

    def test_ieee_rss_excludes_promotional_external_links(self):
        Entry = lambda url: type("Entry", (), {"url": url})()
        self.assertTrue(IEEESpectrumScraper.accepts_rss_entry(Entry("https://spectrum.ieee.org/robotics-article")))
        self.assertFalse(IEEESpectrumScraper.accepts_rss_entry(Entry("https://content.knowledgehub.wiley.com/sponsored")))


if __name__ == "__main__":
    unittest.main()
