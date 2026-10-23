from __future__ import annotations

import json
import unittest
from datetime import date
from unittest.mock import Mock

from candidate_sources.government_announcements.scrapers import (
    MnrNoticesScraper as MnrNoticesParser,
    NeaNoticesScraper as NeaNoticesParser,
)
from candidate_sources.government_announcements.curated_policy import curated_scrapers
from src.http_client import FetchResult
from src.load_sources import Source
from src.scrapers import get_scraper_class
from src.scrapers.government_announcements import GovernmentAnnouncementScraper, MnrNoticesScraper, NeaNoticesScraper


def source(name: str, url: str) -> Source:
    return Source(
        name=name,
        media_type="政府机构",
        domain="综合科技",
        sub_domain="政策/通知公告",
        frequency="工作日",
        description="",
        note="",
        url=url,
    )


class StaticClient:
    def __init__(self, pages: dict[str, str]) -> None:
        self.pages = pages
        self.requested: list[str] = []

    def get(self, url: str, **_kwargs):
        self.requested.append(url)
        text = self.pages.get(url)
        if text is None:
            return None
        content_type = "application/json" if url.endswith(".json") else "text/html"
        return FetchResult(url=url, text=text, status_code=200, content_type=content_type)


class GovernmentAnnouncementProductionTests(unittest.TestCase):
    def test_sastind_uses_detail_publication_not_listing_month_or_document_date(self):
        parser = curated_scrapers()["国家国防科技工业局—政策法规"]()
        url = "https://www.sastind.gov.cn/n10086167/n10086221/c10786994/content.html"
        listing = f'''<ul><li><a href="{url}" title="国家原子能机构等公告2026年第1号 发布核出口管制清单">
            国家原子能机构等公告2026年第1号 发布核出口管制清单<span>10-16</span></a></li></ul>'''
        detail = '''<span class="wz_xx">发布日期：2026-10-16</span>
            <div>公告署期：2026年10月10日；2026年11月1日起施行。</div>'''
        client = StaticClient({parser.listing_url: listing, url: detail})
        scraper = get_scraper_class(parser.source_name)(client, source(parser.source_name, parser.listing_url))
        items = scraper._listing_items(parser)
        self.assertEqual([(item.url, item.platform_published_at) for item in items], [(url, date(2026, 10, 16))])
        self.assertEqual(client.requested, [parser.listing_url, url])
        self.assertEqual(scraper.scrape(target_date=date(2026, 10, 10)), [])
        self.assertEqual(scraper.scrape(target_date=date(2026, 10, 16))[0]["content_policy"], "metadata_only")
        with self.assertRaises(ValueError):
            parser.verified_date('<p>2026年11月1日起施行</p>', url)

    def test_adapter_replaces_list_date_with_verified_detail_date(self):
        parser = curated_scrapers()["中国民用航空局—政策发布"]()
        link = "http://www.caac.gov.cn/PHONE/XXGK_17/XXGK/ZCFB/202610/t20261008_231816.html"
        listing = f'<tr><td><a href="{link}">中国民用航空局关于印发《航班评审优化措施》的通知</a></td><td>2026年08月18日</td></tr>'
        client = Mock()
        client.get.side_effect = [Mock(text=listing, url=parser.listing_url),
                                  Mock(text="var __$pubtime='2026-10-08 19:57:18';", url=link.replace("http://www.caac.gov.cn/PHONE/XXGK_17/", "https://www.caac.gov.cn/XXGK/"))]
        adapter = GovernmentAnnouncementScraper(client, Mock())
        items = adapter._listing_items(parser)
        self.assertEqual(items[0].platform_published_at.isoformat(), "2026-10-08")
        self.assertTrue(all(call.kwargs["strict_robots"] for call in client.get.call_args_list))

    def test_reviewed_channels_are_registered(self):
        self.assertIs(get_scraper_class("国家能源局—通知"), NeaNoticesScraper)
        self.assertIs(get_scraper_class("自然资源部—通知公告"), MnrNoticesScraper)

    def test_nea_adapter_filters_by_date_and_collects_verified_text(self):
        parser = NeaNoticesParser()
        detail_url = "https://www.nea.gov.cn/20260909/22d62e1a042a420c846f7598589136e2/c.html"
        listing = json.dumps(
            {
                "datasource": [
                    {
                        "showTitle": "能源通知",
                        "publishUrl": detail_url,
                        "publishTime": "2026-09-09",
                    },
                    {
                        "showTitle": "旧通知",
                        "publishUrl": "https://www.nea.gov.cn/20260908/12d62e1a042a420c846f7598589136e2/c.html",
                        "publishTime": "2026-09-08",
                    },
                ]
            },
            ensure_ascii=False,
        )
        detail = """
        <meta name="SiteName" content="国家能源局">
        <meta name="ArticleTitle" content="能源通知">
        <meta name="PubDate" content="2026-09-08">
        <span id="detailContent"><p>通知正文</p><p><a href="a.pdf">附件</a></p></span>
        """
        client = StaticClient({parser.data_url: listing, detail_url: detail})
        scraper = NeaNoticesScraper(client, source("国家能源局—通知", parser.listing_url))

        articles = scraper.scrape(target_date=date(2026, 9, 9))

        self.assertEqual(len(articles), 1)
        self.assertEqual(articles[0]["content"], "通知正文")
        self.assertEqual(articles[0]["published_at"], "2026-09-09")
        self.assertEqual(articles[0]["content_extraction"], "government_document_text")
        self.assertEqual(scraper.last_date_filtered_count, 1)

    def test_mnr_adapter_stores_metadata_without_requesting_detail(self):
        parser = MnrNoticesParser()
        listing = """
        <ul class="ky_open_list"><li><span>2026-09-09</span>
        <a href="http://gi.mnr.gov.cn/202609/t20260909_2938017.html">自然资源公示</a>
        </li></ul>
        """
        client = StaticClient({parser.listing_url: listing})
        scraper = MnrNoticesScraper(client, source("自然资源部—通知公告", parser.listing_url))

        articles = scraper.scrape(target_date=date(2026, 9, 9))

        self.assertEqual(len(articles), 1)
        self.assertEqual(articles[0]["content"], "")
        self.assertEqual(articles[0]["content_policy"], "metadata_only")
        self.assertEqual(client.requested, [parser.listing_url])


if __name__ == "__main__":
    unittest.main()
