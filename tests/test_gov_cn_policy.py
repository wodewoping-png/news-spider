import json
import unittest
from datetime import date

from candidate_sources.government_announcements.base import ContractViolation
from candidate_sources.government_announcements.gov_cn import (
    GovCnPolicyDocumentsScraper,
    GovCnPolicyInterpretationsScraper,
)
from candidate_sources.government_announcements.selected_ministries import (
    ForestryPolicyDocumentsScraper,
    LswzPolicyReleasesScraper,
)


class GovCnPolicyTests(unittest.TestCase):
    def test_news_and_unverified_links_do_not_enter_policy_lists(self):
        policy = GovCnPolicyDocumentsScraper()
        interpretation = GovCnPolicyInterpretationsScraper()
        rows = [
            {"TITLE": "国务院关于发展体育赛事的意见", "DOCRELPUBTIME": "2026-10-09",
             "URL": "https://www.gov.cn/zhengce/content/202610/content_7082820.htm"},
            {"TITLE": "领导人会见代表团", "DOCRELPUBTIME": "2026-10-09",
             "URL": "https://www.gov.cn/zhengce/202610/content_7082821.htm"},
            {"TITLE": "负责人就《关于做好专业学位工作的意见》答记者问", "DOCRELPUBTIME": "2026-10-09",
             "URL": "https://www.gov.cn/zhengce/202610/content_7082822.htm"},
            {"TITLE": "《关于做好专业学位工作的意见》政策解读", "DOCRELPUBTIME": "2026-10-09",
             "URL": "https://elsewhere.example/zhengce/202610/content_7082823.htm"},
            {"TITLE": "图表：《关于做好专业学位工作的意见》政策解读", "DOCRELPUBTIME": "2026-10-09",
             "URL": "https://www.gov.cn/zhengce/jiedu/tujie/202610/content_7082824.htm"},
        ]
        self.assertEqual([item.title for item in policy.parse_listing_json(json.dumps(rows))],
                         ["国务院关于发展体育赛事的意见"])
        self.assertEqual([item.title for item in interpretation.parse_listing_json(json.dumps(rows))],
                         ["负责人就《关于做好专业学位工作的意见》答记者问"])

    def test_policy_detail_uses_official_page_marker_and_publication_date(self):
        scraper = GovCnPolicyDocumentsScraper()
        url = "https://www.gov.cn/zhengce/content/202610/content_7082820.htm"
        html = ('<title>国务院关于发展体育赛事的意见_最新政策_中国政府网</title>'
                '<meta name="firstpublishedtime" content="2026-10-09-18:00:00">'
                '<div id="UCAP-CONTENT"><p>决定实施该政策。</p>'
                '<p>附件：<a href="/file.pdf">下载文件</a></p></div>')
        article = scraper.parse_detail(html, url)
        self.assertEqual(article.platform_published_at, date(2026, 10, 9))
        self.assertIn("决定实施该政策", article.content)
        self.assertNotIn("下载文件", article.content)
        with self.assertRaises(ContractViolation):
            scraper.parse_detail(html.replace("_中国政府网", "_其他网站"), url)

    def test_ministry_policy_lists_reject_cross_column_reposts(self):
        forestry = ForestryPolicyDocumentsScraper()
        forestry_html = ('<div class="news_list"><ul>'
                         '<li><span>2026-09-15</span><a href="/lyj/1/lczc/20260915/688613.html">林草指导意见</a></li>'
                         '<li><span>2026-09-15</span><a href="/c/www/gwywj/683927.jhtml">转载国务院文件</a></li>'
                         '</ul></div>')
        self.assertEqual(len(forestry.parse_listing(forestry_html, forestry.listing_url)), 1)

        lswz = LswzPolicyReleasesScraper()
        lswz_html = ('<ul class="lists">'
                     '<li><a href="/html/zcfb/2026-07/23/content_294434.shtml">粮食安全通知</a></li>'
                     '<li><a href="https://outside.example/html/zcfb/2026-07/23/content_42.shtml">转载</a></li>'
                     '</ul>')
        self.assertEqual(len(lswz.parse_listing(lswz_html, lswz.listing_url)), 1)


if __name__ == "__main__":
    unittest.main()
