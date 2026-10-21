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


if __name__ == "__main__":
    unittest.main()
