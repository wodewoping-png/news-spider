import json
import unittest
from unittest.mock import Mock
from datetime import date
import requests
from src.http_client import RobotsCache, valid_robots_text
from src.load_sources import Source
from src.scrapers.inew_frontier import INEWFrontierScraper
from src.scrapers.government_announcements import GovCnPolicyDocumentsScraper

class RepairTests(unittest.TestCase):
    def test_bom_robots_preserves_disallow(self):
        response=requests.Response();response.status_code=200
        response._content=b'\xef\xbb\xbfUser-agent: *\nDisallow: /private/\n'
        response.encoding='ISO-8859-1'
        response.headers['Content-Type']='text/plain'
        self.assertTrue(valid_robots_text(response))
        session=Mock();session.get.return_value=response
        robots=RobotsCache(session,'DailyNewsSpider',5)
        self.assertTrue(robots.can_fetch('https://www.gov.cn/zhengce/',fail_closed=True))
        self.assertFalse(robots.can_fetch('https://www.gov.cn/private/',fail_closed=True))

    def test_policy_failure_is_not_silent_zero(self):
        client=Mock();client.get.return_value=None;client.last_failure_reason='blocked by robots.txt'
        scraper=GovCnPolicyDocumentsScraper(client,Mock())
        self.assertEqual(scraper.scrape(target_date=date(2026,11,13)),[])
        self.assertEqual(scraper.last_failed_fetch_count,1)
        self.assertEqual(scraper.last_fetch_issues,'blocked by robots.txt')

    def test_inew_api_category_date_and_detail(self):
        client=Mock();client.get.side_effect=[Mock(text=json.dumps({'code':200,'rows':[
            {'contentId':1,'columnCode':'FRONTIER','publishTime':'2026-11-10T12:00:00'},
            {'contentId':2,'columnCode':'CENTER','publishTime':'2026-11-10T12:00:00'},
            {'contentId':3,'columnCode':'FRONTIER','publishTime':'2026-11-09T12:00:00'}]})),
            Mock(text=json.dumps({'data':{'content':{'contentId':1,'title':'测试科研进展','contentHtml':'<p>这是一篇公开的科研进展文章正文。</p>'}}}))]
        source=Source('mtl.inew.cn—学术前沿','','','','','','','')
        scraper=INEWFrontierScraper(client,source)
        articles=scraper.scrape(target_date=date(2026,11,10))
        self.assertEqual(len(articles),1)
        self.assertEqual(articles[0]['url'],'https://mtl.inew.cn/academic-news/detail/1')
        self.assertEqual(scraper.last_date_filtered_count,1)
        self.assertIn('科研进展文章正文',articles[0]['content'])
