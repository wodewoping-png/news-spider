import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import Mock

from candidate_sources.government_announcements.curated_policy import CgsMnrPolicyScraper, curated_scrapers
from candidate_sources.government_announcements.scrapers import MnrNoticesScraper as MnrParser
from src.http_client import FetchResult, HttpClient
from src.load_sources import Source
from src.scrapers.government_announcements import MnrNoticesScraper, GovernmentAnnouncementScraper
from src.government_archive import archive_source, archive_bucket


class Client:
    def __init__(self, pages):
        self.pages, self.requested, self.last_failure_reason = pages, [], ''

    def get(self, url, **kwargs):
        self.requested.append((url, kwargs))
        self.last_failure_reason = ''
        if url not in self.pages:
            self.last_failure_reason = 'robots.txt unavailable (HTTP 503); strict check deferred'
            return None
        return FetchResult(url, self.pages[url], 200, 'text/html')


class MinistryRevalidationTests(unittest.TestCase):
    def test_mnr_fallback_verifies_source_and_publication_without_url_date(self):
        parser = CgsMnrPolicyScraper()
        url = 'https://www.cgs.gov.cn/zcwj/202609/t20260901_867703.html'
        listing = f'<li><a href="{url}">自然资源部关于印发《临时用海管理办法》的通知</a><span>2026-08-10</span></li>'
        detail = '<meta name="ContentSource" content="自然资源部"><meta name="PubDate" content="2026-08-10 11:30:00">'
        client = Client({parser.listing_url: listing, url: detail})
        source = Source('自然资源部—通知公告', '政府机构', '政策', '政策', '工作日', '', '', MnrParser.listing_url)
        scraper = MnrNoticesScraper(client, source)
        articles = scraper.scrape(target_date=date(2026, 8, 10))
        self.assertEqual(len(articles), 1)
        self.assertEqual(articles[0]['url'], url)
        self.assertEqual(articles[0]['published_at'], '2026-08-10')
        self.assertIn('partial official', articles[0]['listing_note'])
        self.assertTrue(all(kwargs['strict_robots'] for _, kwargs in client.requested))
        scraper.scrape(target_date=date(2026, 11, 16))
        self.assertFalse(scraper.last_target_date_absent)
        self.assertEqual(scraper.last_failed_fetch_count, 1)
        with tempfile.TemporaryDirectory() as temp:
            report, _ = archive_source(source, client, date(2026, 8, 10), Path(temp), 100)
        self.assertEqual(report['status'], 'partial_fallback')
        self.assertIn('partial official', report['listing_note'])
        with self.assertRaises(ValueError):
            parser.verified_date(detail.replace('自然资源部', '其他来源'), url)

    def test_chinajob_uses_row_date_excludes_external_and_deduplicates(self):
        parser = curated_scrapers()['人力资源和社会保障部—中国就业网政策文件']()
        url = '/c/2026-11-16/642278.shtml'
        title = '辽宁：关于进一步健全就业公共服务体系的通知'
        html = f'<div class="item"><div><a href="{url}">{title}</a></div><span>2026-11-16</span><a href="{url}">{title}</a></div>'
        html += f'<div class="item"><a href="https://other.gov.cn{url}">{title}</a><span>2026-11-16</span></div>'
        items = parser.parse_listing(html, parser.listing_url)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].platform_published_at, date(2026, 11, 16))

    def test_caac_extra_columns_use_detail_dates_and_statistics_bucket(self):
        for label, path in [('政策发布', 'ZCFB'), ('统计数据', 'TJSJ')]:
            parser = curated_scrapers()['中国民用航空局—' + label]()
            html = f'<tr><td><a href="http://www.caac.gov.cn/PHONE/XXGK_17/XXGK/{path}/202610/t20261019_231883.html">关于发布中国民航生产指标统计的通知</a></td><td>2026-10-20</td></tr>'
            item = parser.parse_listing(html, parser.listing_url)[0]
            self.assertIsNone(item.platform_published_at)
            mobile = parser.publication_urls(item.url)[1]
            client = Client({parser.listing_url: html, item.url: '<li>发文日期：2026-10-20</li>', mobile: "var __$pubtime='2026-10-19 10:00:00';"})
            scraper = GovernmentAnnouncementScraper(client, Source('test', '', '', '', '', '', '', parser.listing_url))
            verified = scraper._listing_items(parser)
            self.assertEqual(verified[0].platform_published_at, date(2026, 10, 19))
            self.assertEqual(verified[0].url, item.url)
            self.assertEqual(parser.verified_date("var __$pubtime='2026-10-19 10:00:00';", item.url), date(2026, 10, 19))
        self.assertEqual(archive_bucket('中国民用航空局—统计数据'), ('统计数据清单.csv', '统计数据'))

    def test_robots_unavailable_is_distinct_from_disallow(self):
        for status, body, reason in [(503, '', 'robots.txt unavailable (HTTP 503)'), (200, 'User-agent: *\nDisallow: /', 'blocked by robots.txt')]:
            client = HttpClient(sleep_seconds=0)
            client.session.get = Mock(return_value=Mock(status_code=status, text=body, content=body.encode(), headers={'content-type': 'text/plain'}))
            self.assertIsNone(client.get('https://example.gov.cn/list', strict_robots=True))
            self.assertTrue(client.last_failure_reason.startswith(reason))
            self.assertEqual(client.session.get.call_count, 1)


if __name__ == '__main__':
    unittest.main()
