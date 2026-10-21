import unittest

from candidate_sources.government_announcements.curated_policy import (
    curated_scrapers,
    load_policy_sites,
)


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


if __name__ == "__main__":
    unittest.main()
