import json
import unittest
from unittest.mock import Mock

from candidate_sources.government_announcements.curated_policy import (
    curated_scrapers,
    load_policy_sites,
)
from src.http_client import RobotsCache
from src.scrapers.government_announcements import GovernmentAnnouncementScraper


class CuratedPolicyContractTests(unittest.TestCase):
    def test_every_agency_has_an_explicit_state(self):
        sites = load_policy_sites()
        self.assertEqual(len(sites), 57)
        self.assertEqual(len({site["official_domain"] for site in sites}), 57)
        self.assertTrue(all(site["status"] in {"active", "existing", "pending", "hold"} for site in sites))
        self.assertTrue(all(site["reason"] for site in sites))
        self.assertGreaterEqual(len(curated_scrapers()), 14)

    def test_cross_subdomain_dates_and_external_links(self):
        parser = curated_scrapers()["文化和旅游部—公告通知"]()
        html = """<table>
          <tr><td><a href="https://zwgk.mct.gov.cn/zfxxgkml/kjjy/202610/t20261016_967388.html">
            文化和旅游部关于印发《旅游发展规划》的通知</a></td><td>2026-10-16</td></tr>
          <tr><td><a href="https://example.com/zfxxgkml/kjjy/202610/t20261016_999.html">
            文化和旅游部关于印发《伪造文件》的通知</a></td><td>2026-10-16</td></tr>
          <tr><td><a href="https://zwgk.mct.gov.cn/zfxxgkml/kjjy/202610/t20261016_999.html">
            文化和旅游部关于印发《没有日期》的通知</a></td><td></td></tr>
        </table>"""
        items = parser.parse_listing(html, parser.listing_url)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].platform_published_at.isoformat(), "2026-10-16")

    def test_official_http_redirect_is_normalized_and_date_removed_from_title(self):
        parser = curated_scrapers()["教育部—最新文件"]()
        html = '<ul><li><a href="http://www.moe.gov.cn/srcsite/A06/s3321/202610/t20261009_1453396.html">关于印发《科技教育方案》的通知</a><span>2026-10-15</span></li></ul>'
        items = parser.parse_listing(html, parser.listing_url.replace("https://", "http://"))
        self.assertEqual(len(items), 1)
        self.assertTrue(items[0].url.startswith("https://www.moe.gov.cn/"))
        spb = curated_scrapers()["国家邮政局—通知公告"]()
        html = '<li><a href="/gjyzj/c100009/c100010/202610/92fefd07df414671825d1002e8b9750d.shtml"><p>国家邮政局关于发布《行业标准》的通知</p><span>2026-10-20</span></a></li>'
        items = spb.parse_listing(html, spb.listing_url)
        self.assertEqual(items[0].title, "国家邮政局关于发布《行业标准》的通知")

    def test_nppa_script_title_and_cma_publication_date(self):
        nppa = curated_scrapers()["国家新闻出版署（国家版权局）—通知公示"]()
        html = '''<li><a href="./202609/t20260928_1010273.html"><script>
        var _docTitle = '2026年度国家古籍整理出版资助项目公告';
        document.write(_docTitle);
        </script></a><span>[2026-09-28]</span></li>'''
        items = nppa.parse_listing(html, nppa.listing_url)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].title, "2026年度国家古籍整理出版资助项目公告")
        self.assertEqual(items[0].platform_published_at.isoformat(), "2026-09-28")

        cma = curated_scrapers()["中国气象局—政策文件"]()
        html = '''<li class="list-item"><font class="date endtime">2026年01月09日</font>
        <font class="date fwny">2025年12月26日</font>
        <a href="./202601/t20260112_7537551.html">中国气象局关于推进能源气象服务体系建设的指导意见</a></li>'''
        items = cma.parse_listing(html, cma.listing_url)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].platform_published_at.isoformat(), "2026-01-09")

    def test_fmprc_declares_policy_document_without_title_date(self):
        parser = curated_scrapers()["外交部—国际组织文件"]()
        html = '''<li><a href="./202610/t20261021_12044136.shtml">
        上海合作组织成员国政府首脑理事会联合公报（2026-10-21）</a></li>
        <li><a href="./202610/t20261021_12044137.shtml">部长出访新闻（2026-10-21）</a></li>'''
        items = parser.parse_listing(html, parser.listing_url)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].title, "上海合作组织成员国政府首脑理事会联合公报")
        self.assertEqual(items[0].platform_published_at.isoformat(), "2026-10-21")

    def test_official_embedded_records_keep_dates_and_skip_unrelated_items(self):
        fixtures = (
            ("国家知识产权局—政策通知", "https://www.cnipa.gov.cn/art/2026/10/21/art_75_208634.html",
             "国家知识产权局关于发布集成电路布图设计请求类表格的通知", "2026-10-21"),
            ("国家广播电视总局—政策公告", "https://www.nrta.gov.cn/art/2026/7/31/art_113_73786.html",
             "国家广播电视总局关于发布《广播电视行业标准》的通知", "2026-07-31"),
            ("国家医疗保障局—政策法规", "https://www.nhsa.gov.cn/art/2026/9/15/art_104_22141.html",
             "国家医疗保障局关于试行高水平新技术服务价格制度的通知", "2026-09-15"),
        )
        for name, url, title, day in fixtures:
            with self.subTest(name=name):
                parser = curated_scrapers()[name]()
                html = (f'<script><datastore><record><![CDATA[<li><span>2026-02-00024</span>'
                        f'<a href="{url}">{title}</a><span>{day}</span></li>]]></record>'
                        f'<record><![CDATA[<li><a href="https://example.com/art/2026/9/15/art_104_99.html">'
                        f'{title}</a><span>{day}</span></li>]]></record></datastore></script>')
                items = parser.parse_listing(html, parser.listing_url)
                self.assertEqual(len(items), 1)
                self.assertEqual(items[0].platform_published_at.isoformat(), day)

        nrta = curated_scrapers()["国家广播电视总局—政策公告"]()
        html = '''<record><![CDATA[<li><a href="https://www.nrta.gov.cn/art/2026/9/29/art_113_74147.html"
        >《关于促进广播电视和网络视听公益广告高质量发展的意见》发布</a>
        <span>2026-09-29</span></li>]]></record>'''
        self.assertEqual(nrta.parse_listing(html, nrta.listing_url), [])

    def test_ggj_policy_notice_excludes_event_preview(self):
        parser = curated_scrapers()["国家机关事务管理局—公共机构政策通知"]()
        html = '''<li><a href="./202607/t20260731_49595.htm">国家机关事务管理局
        国家发展和改革委员会关于印发《公共机构节能工作方案》的通知</a>
        <span>2026-07-31</span></li><li><a href="./202610/t20261010_49795.htm">
        直播预告：公共机构绿色低碳讲堂</a><span>2026-10-10</span></li>'''
        items = parser.parse_listing(html, parser.listing_url)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].platform_published_at.isoformat(), "2026-07-31")

    def test_neac_policy_document_excludes_demonstration_award(self):
        parser = curated_scrapers()["国家民族事务委员会—政策文件"]()
        html = '''<li><a href="https://www.neac.gov.cn/seac/c103593/202601/1185934.shtml">
        国家民委关于印发《民族团结进步示范区创建管理办法》的通知</a>
        <span>[2026-01-08]</span></li><li><a href="https://www.neac.gov.cn/seac/xwzx/202601/1186743.shtml">
        国家民委关于命名示范单位的决定</a><span>[2026-01-29]</span></li>'''
        items = parser.parse_listing(html, parser.listing_url)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].platform_published_at.isoformat(), "2026-01-08")

    def test_disease_control_embedded_json_keeps_official_dated_document(self):
        parser = curated_scrapers()["国家疾病预防控制局—政策法规"]()
        rows = [
            {"aT": "国家疾控局关于印发传染病疫情信息公布管理办法的通知",
             "aPd": "2026-05-14 17:11", "aU": json.dumps({"common": "/jbkzzx/c100012/common/content/content_2057633897501855744.html"})},
            {"aT": "国家疾控局关于印发伪造办法的通知", "aPd": "2026-05-14",
             "aU": json.dumps({"common": "https://example.com/evil.html"})},
        ]
        html = "<script>var itemObj = " + json.dumps(rows, ensure_ascii=False) + ";</script>"
        items = parser.parse_listing(html, parser.listing_url)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].platform_published_at.isoformat(), "2026-05-14")
        self.assertTrue(items[0].url.startswith("https://www.ndcpa.gov.cn/"))

        interpretation = curated_scrapers()["国家疾病预防控制局—具名政策解读"]()
        rows = [{"aT": "《疾病预防控制十五五规划》政策解读", "aPd": "2026-07-27 18:02",
                 "aU": json.dumps({"common": "/jbkzzx/c100013/common/content/content_2081593247836573696.html"})}]
        html = "<script>var itemObj = " + json.dumps(rows, ensure_ascii=False) + ";</script>"
        self.assertEqual(len(interpretation.parse_listing(html, interpretation.listing_url)), 1)

    def test_nfra_api_uses_publication_date_and_pins_document_path(self):
        parser = curated_scrapers()["国家金融监督管理总局—政策法规"]()
        payload = {"rptCode": 200, "data": {"rows": [
            {"docId": 1268952, "docTitle": "保险公司资产负债管理办法",
             "publishDate": "2026-08-21 20:07:00", "builddate": "2026-08-20"},
            {"docId": 1268953, "docTitle": "保险公司资产负债管理办法", "builddate": "2026-08-20"},
        ]}}
        items = parser.parse_listing_json(json.dumps(payload), parser.data_url)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].platform_published_at.isoformat(), "2026-08-21")
        self.assertEqual(items[0].url, "https://www.nfra.gov.cn/cn/view/pages/ItemDetail.html?docId=1268952&itemId=926")
        with self.assertRaises(ValueError):
            parser.parse_listing_json(json.dumps(payload), parser.data_url.replace("itemId=926", "itemId=916"))

    def test_statistics_and_mine_are_dated_and_same_origin(self):
        stats = curated_scrapers()["国家统计局—数据发布"]()
        html = '<li><a href="./202610/t20261020_1965658.html">2026年三季度国内生产总值初步核算结果</a><span>2026-10-20</span></li>'
        self.assertEqual(len(stats.parse_listing(html, stats.listing_url)), 1)
        mine = curated_scrapers()["国家矿山安全监察局—通知公告"]()
        html = '''<li><a href="./202610/t20261016_736000.shtml">国家矿山安全监察局关于印发《煤矿安全监管监察行政处罚裁量权基准》的通知</a><span>2026-10-16</span></li>
        <li><a href="./202609/t20260930_718035.shtml">国家矿山安全监察局公布第三批典型执法案例</a><span>2026-09-30</span></li>'''
        items = mine.parse_listing(html, mine.listing_url)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].platform_published_at.isoformat(), "2026-10-16")

    def test_detail_dated_columns_use_verified_publication_field(self):
        audit = curated_scrapers()["审计署—审计结果公告"]()
        audit_list = '<dl><a href="../../n5/n25/c10792969/content.html" title="2026年第1号公告：中央部门单位2025年度预算执行情况审计结果">公告</a><dd>[06-23]</dd></dl>'
        item = audit.parse_listing(audit_list, audit.listing_url)[0]
        self.assertIsNone(item.platform_published_at)
        self.assertEqual(audit.verified_date('<meta name="PubDate" content="2026-06-23 08:35">', item.url).isoformat(), "2026-06-23")
        with self.assertRaises(ValueError):
            audit.verified_date('<meta name="PubDate" content="">', item.url)

        caac = curated_scrapers()["中国民用航空局—政策发布"]()
        caac_list = '<tr><td><a href="http://www.caac.gov.cn/PHONE/XXGK_17/XXGK/ZCFB/202610/t20261008_231816.html">中国民用航空局关于印发《国内航线航班评审优化措施》的通知</a></td><td>2026年09月01日</td></tr>'
        item = caac.parse_listing(caac_list, caac.listing_url)[0]
        self.assertEqual(item.url, "https://www.caac.gov.cn/XXGK/XXGK/ZCFB/202610/t20261008_231816.html")
        self.assertIsNone(item.platform_published_at)
        self.assertEqual(caac.verified_date("<script>var __$pubtime='2026-10-08 19:57:18';</script>", item.url).isoformat(), "2026-10-08")

        sport = curated_scrapers()["国家体育总局—政策法规"]()
        sport_list = '<li><a href="../../n315/n331/n405/c28934431/content.html">体育总局办公厅关于印发《足球教练员职称评价标准》的通知</a><span>08-05</span></li>'
        item = sport.parse_listing(sport_list, sport.listing_url)[0]
        self.assertEqual(sport.verified_date('<meta name="PubDate" content="2025-08-05">', item.url).isoformat(), "2025-08-05")

    def test_robots_html_challenge_does_not_grant_access(self):
        session = Mock()
        session.get.return_value = Mock(status_code=200,
            headers={"content-type": "text/html"}, text="<html><script>verification()</script></html>")
        cache = RobotsCache(session, "DailyNewsSpider/0.1", 5)
        self.assertFalse(cache.can_fetch("https://www.csrc.gov.cn/csrc/policy.html", fail_closed=True))
        session.get.assert_called_once()

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


if __name__ == "__main__":
    unittest.main()
