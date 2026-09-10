from __future__ import annotations

import json
import unittest

from candidate_sources.government_announcements.scrapers import (
    MemNoticesScraper,
    MiitPublicNoticesScraper,
    MnrNoticesScraper,
    MofcomPolicyReleasesScraper,
    MostNoticesScraper,
    MotPolicyDocumentsScraper,
    NeaAnnouncementsScraper,
    NeaNoticesScraper,
    NdaPolicyReleasesScraper,
    SamrAntitrustNoticesScraper,
)
from candidate_sources.government_announcements.base import ContractViolation


class GovernmentAnnouncementScraperTests(unittest.TestCase):
    def test_nea_json_listing_normalizes_only_verified_https_detail_urls(self):
        scraper = NeaNoticesScraper()
        payload = json.dumps(
            {
                "datasource": [
                    {
                        "showTitle": "<a>能源通知</a>",
                        "publishUrl": "http://www.nea.gov.cn/20260909/22d62e1a042a420c846f7598589136e2/c.html",
                        "publishTime": "2026-09-09 22:53:26",
                    },
                    {
                        "showTitle": "外站",
                        "publishUrl": "https://example.org/item.html",
                        "publishTime": "2026-09-09",
                    },
                ]
            },
            ensure_ascii=False,
        )
        items = scraper.parse_listing_json(payload)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].title, "能源通知")
        self.assertTrue(items[0].url.startswith("https://www.nea.gov.cn/"))

    def test_nea_detail_is_text_only_and_does_not_fetch_attachment(self):
        scraper = NeaAnnouncementsScraper()
        url = "https://www.nea.gov.cn/20260904/324fdc3e4908431392b82d19ab10de6b/c.html"
        html = """
        <meta name="SiteName" content="国家能源局">
        <meta name="ArticleTitle" content="能源公告">
        <meta name="PubDate" content="2026-09-04 10:00:00">
        <meta name="ContentSource" content="国家能源局">
        <span id="detailContent"><p>公告正文</p><img src="x.jpg">
        <a href="attachment.docx">附件清单</a><script>bad()</script>
        <p><strong>政策解读：</strong><a href="related.html">解读内容</a></p></span>
        """
        article = scraper.parse_detail(html, url)
        self.assertEqual(article.title, "能源公告")
        self.assertIn("公告正文", article.content)
        self.assertNotIn("bad", article.content)
        self.assertNotIn("附件清单", article.content)
        self.assertNotIn("政策解读", article.content)
        self.assertFalse(article.production_enabled)
        self.assertFalse(scraper.downloads_attachments)

    def test_miit_fragment_and_detail(self):
        scraper = MiitPublicNoticesScraper()
        fragment = """
        <div class="page-content"><ul><li class="cf">
          <a href="/zwgk/wjgs/art/2026/art_0b2035d10a644ff38840f697f5b35abe.html"
             title="新能源车型公示">截断标题</a><span>2026-09-09</span>
        </li><li><a href="https://example.org/out.html">外站</a><span>2026-09-08</span></li></ul></div>
        """
        payload = json.dumps({"data": {"html": fragment}}, ensure_ascii=False)
        items = scraper.parse_api_response(payload)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].title, "新能源车型公示")
        detail = """
        <meta name="SiteName" content="中华人民共和国工业和信息化部">
        <meta name="ContentSource" content="装备工业一司">
        <h1 id="con_title">新能源车型公示</h1>
        <span id="con_time">发布时间：2026-09-09 08:05</span>
        <div id="con_con"><p>公示正文</p><img src="x.png"></div>
        """
        article = scraper.parse_detail(detail, items[0].url)
        self.assertEqual(article.source, "装备工业一司")
        self.assertEqual(article.platform_published_at.isoformat(), "2026-09-09")
        self.assertEqual(article.content, "公示正文")

    def test_all_candidates_fail_closed_on_origin_path_and_scheme(self):
        for scraper in (NeaNoticesScraper(), NeaAnnouncementsScraper(), MiitPublicNoticesScraper()):
            for url in (
                f"http://{scraper.allowed_host}/anything",
                "https://example.org/anything",
                f"https://{scraper.allowed_host}/unverified/path.html",
            ):
                with self.assertRaises(ContractViolation):
                    scraper.guard_url(url, detail=True)

    def test_expanded_ministry_listing_contracts(self):
        cases = [
            (
                MostNoticesScraper(),
                '<ul class="info_list2"><li><a href="./202609/t20260908_197283.html" title="科技通知">x</a><span class="date mhide">2026-09-08</span></li><li><a href="x.pdf">附件</a><span class="date mhide">2026-09-08</span></li></ul>',
                "科技通知",
            ),
            (
                MnrNoticesScraper(),
                '<ul class="ky_open_list"><li><span>2026-09-09</span><a href="http://gi.mnr.gov.cn/202609/t20260909_2938017.html">自然资源公示</a></li></ul>',
                "自然资源公示",
            ),
            (
                MotPolicyDocumentsScraper(),
                '<tbody id="xxgkzn_list_tbody_ID"><tr><td>1</td><td><a href="../jigou/glj/202609/t20260904_4223835.html">交通通知</a></td><td>文号</td><td>2026年09月04日</td></tr></tbody>',
                "交通通知",
            ),
            (
                MofcomPolicyReleasesScraper(),
                '<ul class="policy-list f-mt20"><li><a href="http://www.mofcom.gov.cn/zcfb/zc/art/2026/art_97e72afd4b7f41dab15603c723ea46a9.html">商务公告</a><a href="/zcjd/x.html">政策解读</a><span>2026-09-07</span></li></ul>',
                "商务公告",
            ),
            (
                MemNoticesScraper(),
                '<div class="tonglan_list"><li><a href="/gk/zfxxgkpt/fdzdgknr/202609/t20260904_715238.shtml" title="应急通知">应急通知 2026-09-04</a></li></div>',
                "应急通知",
            ),
            (
                NdaPolicyReleasesScraper(),
                '<ul class="u-list"><li><a href="/sjj/zwgk/zcfb/0708/20260708133949899211227_pc.html">数据政策</a><strong>解读</strong><div><a href="/sjj/zwgk/zjjd/x.html">专家解读</a></div><span>2026.07.08</span></li></ul>',
                "数据政策",
            ),
            (
                SamrAntitrustNoticesScraper(),
                '<div class="gts_contentLeftListbox"><ul><li><a href="/jzxts/tzgg/zqyj/art/2026/art_0a8b25d52d704b8a902f6bcdb3977995.html">监管公告</a></li><li class="gts_contentLeftList01time">2026-09-10</li></ul></div>',
                "监管公告",
            ),
        ]
        for scraper, html, expected_title in cases:
            with self.subTest(scraper=scraper.source_id):
                items = scraper.parse_listing(html, scraper.listing_url)
                self.assertEqual(len(items), 1)
                self.assertEqual(items[0].title, expected_title)
                self.assertTrue(items[0].url.startswith("https://"))

    def test_expanded_ministry_details_are_text_only(self):
        cases = [
            (MostNoticesScraper(), "https://www.most.gov.cn/tztg/202609/t20260908_197283.html", '<meta name="SiteName" content="中华人民共和国科学技术部"><meta name="ArticleTitle" content="科技通知"><meta name="PubDate" content="2026-09-08"><meta name="ContentSource" content="科技部"><div class="text wide"><p>正文</p></div>'),
            (MnrNoticesScraper(), "https://gi.mnr.gov.cn/202609/t20260909_2938017.html", '<meta name="SiteName" content="自然资源部门户网站"><meta name="ArticleTitle" content="资源公告"><meta name="PubDate" content="2026-09-09"><meta name="ContenSource" content="自然资源部"><div id="content1"><p>正文</p></div>'),
            (MotPolicyDocumentsScraper(), "https://xxgk.mot.gov.cn/2020/jigou/glj/202609/t20260904_4223835.html", '<meta name="SiteName" content="交通运输部政府网站"><meta name="ArticleTitle" content="交通通知"><meta name="PubDate" content="2026-09-04"><div id="Zoom"><p>正文</p></div>'),
            (MofcomPolicyReleasesScraper(), "https://www.mofcom.gov.cn/zcfb/zc/art/2026/art_97e72afd4b7f41dab15603c723ea46a9.html", '<meta name="SiteName" content="中华人民共和国商务部"><meta name="ArticleTitle" content="商务公告"><meta name="PubDate" content="2026-09-07"><div class="art-con art-con-bottonmLine"><p>正文</p></div>'),
            (MemNoticesScraper(), "https://www.mem.gov.cn/gk/zfxxgkpt/fdzdgknr/202609/t20260904_715238.shtml", '<title>应急通知</title><div class="scy_detail_top">发文单位：应急管理部 发布日期：2026年09月04日</div><div id="content"><p>正文</p></div>'),
            (NdaPolicyReleasesScraper(), "https://www.nda.gov.cn/sjj/zwgk/zcfb/0708/20260708133949899211227_pc.html", '<meta name="SiteName" content="国家数据局"><meta name="ArticleTitle" content="数据政策"><meta name="PubDate" content="2026.07.08"><div class="article"><p>正文</p></div>'),
            (SamrAntitrustNoticesScraper(), "https://www.samr.gov.cn/jzxts/tzgg/zqyj/art/2026/art_0a8b25d52d704b8a902f6bcdb3977995.html", '<meta name="SiteName" content="国家市场监督管理总局"><meta name="ArticleTitle" content="监管公告"><meta name="PubDate" content="2026-09-10"><div class="zt_xilan_07"><p>正文</p></div>'),
        ]
        for scraper, url, html in cases:
            with self.subTest(scraper=scraper.source_id):
                article = scraper.parse_detail(html, url)
                self.assertEqual(article.content, "正文")
                self.assertFalse(article.production_enabled)


if __name__ == "__main__":
    unittest.main()
