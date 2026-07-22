from __future__ import annotations

import unittest
from datetime import date, datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

from src.article_parser import parse_article_html
from src.date_utils import date_from_url, default_target_date, parse_target_date
from src.http_client import FetchResult
from src.load_sources import Source
from src.main import default_csv_path, expects_daily_output
from src.scrapers.generic import GenericListingScraper
from src.scrapers.multi_page import H2ViewScraper
from src.scrapers.science_net import ScienceNetScraper
from src.scrapers.xinhua_tech import XinhuaTechScraper
from src.storage import canonicalize_url


def make_source(name: str, url: str) -> Source:
    return Source(
        name=name,
        media_type="",
        domain="",
        sub_domain="",
        frequency="real-time",
        description="",
        note="",
        url=url,
    )


class StaticClient:
    def __init__(self, pages: dict[str, str]) -> None:
        self.pages = pages

    def get(self, url: str, **_kwargs):
        html = self.pages.get(url)
        if html is None:
            return None
        return FetchResult(
            url=url,
            text=html,
            status_code=200,
            content_type="text/html",
        )


class DateAndUrlTests(unittest.TestCase):
    def test_delayed_run_before_rollover_keeps_nominal_run_day(self):
        now = datetime(2026, 7, 14, 0, 30, tzinfo=ZoneInfo("Asia/Shanghai"))
        self.assertEqual(default_target_date(now=now), date(2026, 7, 12))

    def test_normal_evening_run_uses_yesterday(self):
        now = datetime(2026, 7, 14, 22, 0, tzinfo=ZoneInfo("Asia/Shanghai"))
        self.assertEqual(default_target_date(now=now), date(2026, 7, 13))

    def test_explicit_target_date_is_unchanged(self):
        self.assertEqual(parse_target_date("2026-07-20"), date(2026, 7, 20))

    def test_default_csv_name_follows_nominal_run_day(self):
        path = default_csv_path(target_date=date(2026, 7, 12))
        self.assertEqual(str(path).replace("\\", "/"), "data/articles-2026-07-13.csv")

    def test_low_frequency_source_is_not_expected_daily(self):
        self.assertFalse(expects_daily_output("\u6bcf\u5468"))
        self.assertFalse(expects_daily_output("Monthly"))
        self.assertTrue(expects_daily_output("\u6bcf\u65e5"))

    def test_compact_xinhua_date_is_read_from_url(self):
        url = "https://www.news.cn/tech/20260720/abc/c.html"
        self.assertEqual(date_from_url(url), date(2026, 7, 20))

    def test_canonical_url_dedupes_scheme_www_slash_and_tracking(self):
        first = "http://www.example.com/a/?utm_source=x&b=2"
        second = "https://example.com/a?b=2"
        self.assertEqual(canonicalize_url(first), canonicalize_url(second))


class ListingScraperTests(unittest.TestCase):
    def test_same_site_accepts_sibling_subdomains(self):
        self.assertTrue(
            GenericListingScraper.same_site(
                "www.china-nengyuan.com",
                "wp.china-nengyuan.com",
            )
        )

    def test_sciencenet_discovers_shtm_articles(self):
        source = make_source(
            "科学网新闻",
            "https://news.sciencenet.cn/morenews-V-1.aspx",
        )
        html = """
        <a href="/htmlnews/2026/7/568485.shtm">第一篇科学新闻标题</a>
        <a href="/htmlnews/2026/7/568486.shtm">第二篇科学新闻标题</a>
        """
        client = StaticClient({source.url: html})
        urls = ScienceNetScraper(client, source).discover_article_urls(20)
        self.assertEqual(len(urls), 2)
        self.assertTrue(urls[0].endswith("/568485.shtm"))

    def test_sciencenet_labeled_publish_time_is_parsed(self):
        source = make_source("科学网新闻", "https://news.sciencenet.cn/")
        html = """
        <html><head><title>科学网测试文章</title></head>
        <body><div>作者：测试 来源：中国科学报 发布时间：2026/7/22 18:30:21</div>
        <div id="content"><p>这是一段用于验证科学网正文和发布日期解析的测试内容。</p></div>
        </body></html>
        """
        article = parse_article_html(
            html,
            "https://news.sciencenet.cn/htmlnews/2026/7/568672.shtm",
            source,
        )
        self.assertEqual(article["published_at"], "2026/7/22 18:30:21")

    def test_xinhua_prefers_chronological_content_list(self):
        source = make_source("新华网科技", "https://www.news.cn/tech/index.html")
        html = """
        <div class="focus"><div class="tit">
          <a href="/tech/20260701/old/c.html">长期焦点文章</a>
        </div></div>
        <div id="content-list">
          <div class="item"><div class="tit">
            <a href="/tech/20260720/new/c.html">目标日期最新文章</a>
          </div></div>
        </div>
        """
        client = StaticClient({source.url: html})
        urls = XinhuaTechScraper(client, source).discover_article_urls(20)
        self.assertTrue(urls[0].endswith("/20260720/new/c.html"))

    def test_date_filter_runs_before_final_article_limit(self):
        source = make_source("example", "https://example.com/list")
        html = """
        <a href="/20260721/a/c.html">今天文章一</a>
        <a href="/20260721/b/c.html">今天文章二</a>
        <a href="/20260720/c/c.html">昨天文章一</a>
        <a href="/20260720/d/c.html">昨天文章二</a>
        """
        client = StaticClient({source.url: html})

        def fake_parse(_client, url, _source):
            published = "2026-07-20" if "20260720" in url else "2026-07-21"
            return {
                "title": url,
                "published_at": published,
                "content": "x" * 300,
                "url": url,
            }

        scraper = GenericListingScraper(client, source)
        with patch("src.scrapers.generic.fetch_and_parse_article", side_effect=fake_parse):
            articles = scraper.scrape(
                2,
                target_date=date(2026, 7, 20),
                candidate_limit=10,
            )
        self.assertEqual(len(articles), 2)
        self.assertTrue(all("20260720" in item["url"] for item in articles))

    def test_consecutive_failed_pages_stop_early(self):
        source = make_source("example", "https://example.com/list")
        scraper = GenericListingScraper(StaticClient({}), source)
        urls = [f"https://example.com/news/{index}.html" for index in range(50)]
        with (
            patch.object(scraper, "discover_article_urls", return_value=urls),
            patch(
                "src.scrapers.generic.fetch_and_parse_article",
                return_value=None,
            ) as fetch,
        ):
            articles = scraper.scrape(
                20,
                target_date=date(2026, 7, 20),
                candidate_limit=50,
            )
        self.assertEqual(articles, [])
        self.assertEqual(fetch.call_count, 10)

    def test_embedded_mit_article_urls_are_discovered(self):
        source = make_source(
            "MIT Technology Review Climate",
            "https://www.technologyreview.com/topic/climate-change/",
        )
        html = r"""
        <script>{"url":"https:\/\/www.technologyreview.com\/2026\/05\/28\/1138067\/climate-tech-ipos\/"}</script>
        """
        client = StaticClient({source.url: html})
        urls = GenericListingScraper(client, source).discover_article_urls(20)
        self.assertEqual(
            urls,
            ["https://www.technologyreview.com/2026/05/28/1138067/climate-tech-ipos/"],
        )

    def test_h2_view_uses_new_gasworld_listing(self):
        source = make_source("H2 View", "https://www.h2-view.com/")
        listing = "https://www.gasworld.com/h2-view/latest-news/"
        html = """
        <article>
          <a href="/story/green-hydrogen-project/2250675.article/">
            Green hydrogen project reaches final investment decision
          </a>
        </article>
        """
        client = StaticClient({listing: html})
        urls = H2ViewScraper(client, source).discover_article_urls(20)
        self.assertEqual(len(urls), 1)
        self.assertIn("2250675.article", urls[0])


if __name__ == "__main__":
    unittest.main()
