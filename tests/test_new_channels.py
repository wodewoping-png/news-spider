from __future__ import annotations

import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from src.http_client import FetchResult
from src.load_sources import Source
from src.scrapers import get_scraper_class
from src.scrapers.bjx_storage import BJXStorageScraper
from src.scrapers.batteries_news import BatteriesNewsScraper
from src.scrapers.datacenter_knowledge import DataCenterKnowledgeScraper
from src.scrapers.china_energy import ChinaEnergyScraper
from src.scrapers.energytrend import EnergyTrendScraper
from src.scrapers.insideevs import InsideEVsScraper
from src.scrapers.interesting_engineering import InterestingEngineeringScraper
from src.scrapers.international_energy import InternationalEnergyScraper
from src.scrapers.itdcw import ITDCWScraper
from src.scrapers.ne_time import NETimeScraper
from src.scrapers.pv_magazine import PVMagazineCIPVScraper
from src.scrapers.rionews import (
    RIONewsBatteryScraper,
    RIONewsChinaEnergyScraper,
    RIONewsInternationalEnergyScraper,
    RIONewsXEVCarScraper,
)
from src.scrapers.solarbe import SolarbeScraper
from src.scrapers.testpv import TestPVScraper
from src.scrapers.xevcar import XEVCarScraper
from src.scrapers.xmol import XMolScraper


def make_source(name: str, url: str) -> Source:
    return Source(
        name=name,
        media_type="垂直领域媒体",
        domain="新能源",
        sub_domain="",
        frequency="实时",
        description="",
        note="",
        url=url,
    )


class StaticClient:
    def __init__(self, pages: dict[str, str | tuple[str, str]]) -> None:
        self.pages = pages

    def get(self, url: str, **_kwargs):
        value = self.pages.get(url)
        if value is None:
            return None
        final_url, html = value if isinstance(value, tuple) else (url, value)
        return FetchResult(
            url=final_url,
            text=html,
            status_code=200,
            content_type="text/html",
        )


class NewChannelRegistryTests(unittest.TestCase):
    def test_every_spreadsheet_website_has_a_specific_scraper(self):
        expected = {
            "pv magazine C&I PV": PVMagazineCIPVScraper,
            "光伏测试网": TestPVScraper,
            "索比光伏": SolarbeScraper,
            "国际能源网": RIONewsInternationalEnergyScraper,
            "中国能源网": RIONewsChinaEnergyScraper,
            "我爱电车网": RIONewsXEVCarScraper,
            "北极星储能网": BJXStorageScraper,
            "INSIDEEVs": InsideEVsScraper,
            "interesting engineering": InterestingEngineeringScraper,
            "EnergyTrend储能": EnergyTrendScraper,
            "NE时代": NETimeScraper,
            "电池网": RIONewsBatteryScraper,
            "X-MOL": XMolScraper,
            "Batteries News": BatteriesNewsScraper,
            "Data Center Knowledge": DataCenterKnowledgeScraper,
        }
        for name, scraper_class in expected.items():
            with self.subTest(source=name):
                self.assertIs(get_scraper_class(name), scraper_class)

    def test_only_login_restricted_source_is_skipped(self):
        public_source = make_source("中国能源网", "https://www.china5e.com/news/")
        public_source = Source(
            **{
                **public_source.__dict__,
                "note": "定制读取无需登录的 energy-economy 公开栏目。",
            }
        )
        restricted_source = Source(
            **{
                **public_source.__dict__,
                "name": "X-MOL",
                "note": "需账号登录；未配置授权凭据时默认跳过。",
            }
        )
        self.assertIsNone(public_source.skip_reason)
        self.assertIn("需账号登录", restricted_source.skip_reason or "")

    def test_rionews_missing_workbook_uses_public_fallback(self):
        class FakePublicScraper:
            def __init__(self, client, source) -> None:
                self.client = client
                self.source = source
                self.last_candidate_count = 7
                self.last_fetched_count = 3

            def scrape(self, limit=20, *, target_date=None, candidate_limit=None):
                self.received = (limit, target_date, candidate_limit)
                return [{"url": "https://example.com/public-article"}]

        source = make_source("中国能源网", "https://www.china5e.com/news/")
        scraper = RIONewsChinaEnergyScraper(StaticClient({}), source)
        with (
            patch.object(
                RIONewsChinaEnergyScraper,
                "fallback_scraper_class",
                FakePublicScraper,
            ),
            patch.object(
                scraper,
                "_workbook_path",
                return_value=Path("missing-rionews-workbook.xlsx"),
            ),
        ):
            articles = scraper.scrape(
                5,
                target_date=date(2026, 8, 13),
                candidate_limit=25,
            )

        self.assertEqual(
            articles,
            [{"url": "https://example.com/public-article"}],
        )
        self.assertEqual(scraper.last_candidate_count, 7)
        self.assertEqual(scraper.last_fetched_count, 3)


class NewChannelDiscoveryTests(unittest.TestCase):
    def test_testpv_keeps_discuz_portal_articles(self):
        source = make_source(
            "光伏测试网",
            "http://www.testpv.com/portal.php?mod=list&catid=20",
        )
        html = """
        <a class="xi2" href="portal.php?mod=view&aid=31423">光伏一周产业新闻汇总</a>
        <a href="forum.php?mod=viewthread&tid=31423">论坛讨论不是新闻</a>
        """
        urls = TestPVScraper(StaticClient({source.url: html}), source).discover_article_urls(10)
        self.assertEqual(
            urls,
            ["http://www.testpv.com/portal.php?mod=view&aid=31423"],
        )

    def test_solarbe_keeps_yaowen_articles(self):
        source = make_source("索比光伏", "https://news.solarbe.com/yaowen")
        html = """
        <div class="recommend-content-right">
          <a class="title2" href="/202607/29/50026715.html">美国逆变器监管新动态</a>
          <a href="/tag/inverter">逆变器标签页</a>
        </div>
        """
        urls = SolarbeScraper(StaticClient({source.url: html}), source).discover_article_urls(10)
        self.assertEqual(urls, ["https://news.solarbe.com/202607/29/50026715.html"])

    def test_international_energy_uses_requested_sections(self):
        source = make_source("国际能源网", "https://www.in-en.com/article/")
        listing = InternationalEnergyScraper.additional_listing_urls[0]
        html = """
        <a href="/article/html/energy-2343180.shtml">浙江公布省级零碳园区项目</a>
        <a href="/article/policy/china/">国内政策栏目</a>
        """
        urls = InternationalEnergyScraper(
            StaticClient({listing: html}),
            source,
        ).discover_article_urls(10)
        self.assertEqual(
            urls,
            ["https://www.in-en.com/article/html/energy-2343180.shtml"],
        )

    def test_china_energy_uses_public_energy_economy_section(self):
        source = make_source("中国能源网", "https://www.china5e.com/news/")
        listing = ChinaEnergyScraper.additional_listing_urls[0]
        html = """
        <div class="list-item"><h2>
          <a href="/news/news-1207060-1.html">上半年能源经济运行数据发布</a>
        </h2></div>
        """
        urls = ChinaEnergyScraper(StaticClient({listing: html}), source).discover_article_urls(10)
        self.assertEqual(
            urls,
            ["https://www.china5e.com/news/news-1207060-1.html"],
        )

    def test_xevcar_keeps_homepage_article_cards(self):
        source = make_source("我爱电车网", "https://www.xevcar.com/")
        html = """
        <div class="entry-title">
          <a href="/gongsi/0HQ5E512026.html">新增产能，多氟多扩产锂电池</a>
        </div>
        """
        urls = XEVCarScraper(StaticClient({source.url: html}), source).discover_article_urls(10)
        self.assertEqual(
            urls,
            ["https://www.xevcar.com/gongsi/0HQ5E512026.html"],
        )

    def test_bjx_storage_accepts_news_subdomain_articles(self):
        source = make_source("北极星储能网", "https://chuneng.bjx.com.cn/")
        listing = BJXStorageScraper.additional_listing_urls[0]
        html = """
        <a href="https://news.bjx.com.cn/html/20260729/1506229.shtml">
          五省落地独立储能输配电价政策
        </a>
        """
        urls = BJXStorageScraper(StaticClient({listing: html}), source).discover_article_urls(10)
        self.assertEqual(
            urls,
            ["https://news.bjx.com.cn/html/20260729/1506229.shtml"],
        )

    def test_insideevs_fallback_keeps_article_urls(self):
        source = make_source("INSIDEEVs", "https://insideevs.com/news/")
        html = """
        <article><h2>
          <a href="/news/777001/new-battery-plant/">New battery plant starts production</a>
        </h2></article>
        """
        urls = InsideEVsScraper(StaticClient({source.url: html}), source).discover_article_urls(10)
        self.assertEqual(
            urls,
            ["https://insideevs.com/news/777001/new-battery-plant/"],
        )

    def test_energytrend_keeps_dated_news_urls(self):
        source = make_source("EnergyTrend储能", "https://www.energytrend.cn/news/")
        html = """
        <div class="entry-title">
          <a href="/news/20260728-148232.html">七个锂电储能项目迎来新进度</a>
        </div>
        """
        urls = EnergyTrendScraper(StaticClient({source.url: html}), source).discover_article_urls(10)
        self.assertEqual(
            urls,
            ["https://www.energytrend.cn/news/20260728-148232.html"],
        )

    def test_energytrend_rss_rejects_price_and_research_sections(self):
        accepted = type("Entry", (), {"url": "https://www.energytrend.cn/news/20260804-148294.html"})()
        price = type("Entry", (), {"url": "https://www.energytrend.cn/pricequotes/20260730-148244.html"})()
        research = type("Entry", (), {"url": "https://www.energytrend.cn/research/20260804-1.html"})()
        self.assertTrue(EnergyTrendScraper.accepts_rss_entry(accepted))
        self.assertFalse(EnergyTrendScraper.accepts_rss_entry(price))
        self.assertFalse(EnergyTrendScraper.accepts_rss_entry(research))

    def test_ne_time_keeps_numeric_article_routes(self):
        source = make_source("NE时代", "https://www.ne-time.cn/")
        html = """
        <a class="article-item" href="/web/article/39264">
          红旗超快充电池实现重大技术突破
        </a>
        """
        urls = NETimeScraper(StaticClient({source.url: html}), source).discover_article_urls(10)
        self.assertEqual(urls, ["https://www.ne-time.cn/web/article/39264"])

    def test_itdcw_reads_only_requested_list_cards(self):
        source = make_source("电池网", "https://www.itdcw.com/news/")
        listing = ITDCWScraper.additional_listing_urls[0]
        html = """
        <div class="list-item"><div class="item-top"><h2>
          <a href="/news/guonei/0H015D062026.html">新疆新型储能项目即将投运</a>
        </h2></div></div>
        <aside><a href="/news/focus/0H415DM2026.html">侧栏推荐新闻</a></aside>
        """
        urls = ITDCWScraper(StaticClient({listing: html}), source).discover_article_urls(10)
        self.assertEqual(
            urls,
            ["https://www.itdcw.com/news/guonei/0H015D062026.html"],
        )

    def test_xmol_login_redirect_is_treated_as_restricted(self):
        source = make_source("X-MOL", "https://www.x-mol.com/news/chem")
        client = StaticClient(
            {
                source.url: (
                    "https://www.x-mol.com/login?redirectUrl=/news/chem",
                    "<html><title>用户登录</title></html>",
                )
            }
        )
        self.assertEqual(XMolScraper(client, source).discover_article_urls(10), [])


if __name__ == "__main__":
    unittest.main()
