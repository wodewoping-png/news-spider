from __future__ import annotations

import json
import unittest
from datetime import date, datetime
from unittest.mock import Mock, patch
from zoneinfo import ZoneInfo

import requests

from src.article_parser import normalize_source_date, parse_article_html
from src.content_quality import assess_content
from src.date_utils import date_from_url, default_target_date, parse_target_date
from src.http_client import (
    BROWSER_USER_AGENT,
    FetchResult,
    HttpClient,
    RequiredFetchError,
    is_access_challenge_html,
    request_headers_for_url,
)
from src.load_sources import Source, expects_output_on_date
from src.main import (
    DEFAULT_MIN_CONTENT_CHARS,
    THE_INFORMATION_PUBLIC_FEED,
    THE_INFORMATION_SUBSCRIBER_FEED,
    default_csv_path,
    enrich_from_rss_entry,
    expects_daily_output,
    fetch_feed_with_public_fallback,
    has_confirmed_non_target_candidates,
    is_uied_aggregator_feed,
    merge_feed_entries,
    resolve_feed_access,
)
from src.rss_discovery import FeedEntry, parse_feed
from src.scrapers.generic import GenericListingScraper
from src.scrapers.multi_page import H2ViewScraper, PerovskiteInfoScraper
from src.scrapers.renewables_now import RenewablesNowScraper
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

    def test_sciencenet_uses_browser_user_agent_by_default(self):
        headers = request_headers_for_url("https://www.sciencenet.cn/xml/news-0.aspx?news=0")
        self.assertIn("Mozilla/5.0", headers["User-Agent"])
        self.assertEqual(
            request_headers_for_url("https://www.sciencenet.cn/", "custom-agent"), {}
        )

    def test_insideevs_uses_browser_user_agent_by_default(self):
        headers = request_headers_for_url("https://insideevs.com/news/123/example/")
        self.assertIn("Mozilla/5.0", headers["User-Agent"])
        self.assertEqual(
            request_headers_for_url("https://insideevs.com/news/", "custom-agent"), {}
        )

    def test_public_fallback_channel_date_containers_are_parsed(self):
        cases = (
            (
                "中国能源网",
                '<div class="showtitinfo">2026-08-13 08:19:30 来源：中国能源网</div>',
                "2026-08-13 08:19:30",
            ),
            (
                "我爱电车网",
                '<span class="qr_code">2026-08-13 09:40</span>',
                "2026-08-13 09:40",
            ),
        )
        for source_name, date_html, expected in cases:
            with self.subTest(source=source_name):
                source = make_source(source_name, "https://example.com/article")
                article = parse_article_html(
                    f"<html><body><h1>Fallback article</h1>{date_html}"
                    f"<article><p>{'Detailed public reporting. ' * 40}</p></article>"
                    "</body></html>",
                    source.url,
                    source,
                )
                self.assertEqual(article["published_at"], expected)

    def test_china_energy_strict_body_excludes_recommendation_sidebar(self):
        source = make_source(
            "中国能源网",
            "https://www.china5e.com/news/news-1-1.html",
        )
        article = parse_article_html(
            "<html><body><h1>Energy article</h1>"
            f"<div id='showcontent'><p>{'Complete public article detail. ' * 40}</p></div>"
            "<aside><p>Recommended headline...</p></aside>"
            "</body></html>",
            source.url,
            source,
        )
        self.assertIn("Complete public article detail", article["content"])
        self.assertNotIn("Recommended headline", article["content"])
        self.assertEqual(article["content_status"], "full")

    def test_bjx_waf_script_is_detected_as_access_challenge(self):
        html = """
        <html><script>
        appkey: "CF_APP_WAF";
        var requestInfo = {"sceneId":"redacted"};
        </script></html>
        """
        self.assertTrue(is_access_challenge_html(html))
        self.assertEqual(
            assess_content(
                'appkey: "CF_APP_WAF"; var requestInfo = {"token":"redacted"};',
                extraction_method="trafilatura_full_text",
            ),
            ("missing", "access_challenge"),
        )

    def test_4c_offshore_uses_day_month_year_dates(self):
        self.assertEqual(
            normalize_source_date("12/08/2026", "4C Offshore"),
            "2026-08-12",
        )
        self.assertEqual(
            normalize_source_date("12/08/2026", "US publisher"),
            "12/08/2026",
        )

    def test_http_client_rejects_http_200_access_challenge(self):
        response = Mock()
        response.status_code = 200
        response.url = "https://news.bjx.com.cn/html/20260812/1.shtml"
        response.headers = {"content-type": "text/html"}
        response.encoding = "utf-8"
        response.text = (
            '<script>appkey: "CF_APP_WAF"; '
            'var requestInfo = {"sceneId":"redacted"};</script>'
        )
        response.raise_for_status.return_value = None
        client = HttpClient(sleep_seconds=0, respect_robots=False)
        with patch.object(client.session, "get", return_value=response):
            self.assertIsNone(client.get(response.url, allow_non_html=False))

    def test_the_information_uses_browser_user_agent(self):
        headers = request_headers_for_url(THE_INFORMATION_SUBSCRIBER_FEED)

        self.assertEqual(headers["User-Agent"], BROWSER_USER_AGENT)

    def test_required_cloudflare_challenge_is_retried_and_diagnosed(self):
        response = Mock()
        response.status_code = 403
        response.url = THE_INFORMATION_SUBSCRIBER_FEED
        response.headers = {
            "content-type": "text/html; charset=UTF-8",
            "cf-mitigated": "challenge",
            "server": "cloudflare",
        }
        response.text = "<title>Just a moment...</title>"
        client = HttpClient(sleep_seconds=0, respect_robots=False)

        with (
            patch.object(client.session, "get", return_value=response) as request,
            patch("src.http_client.time.sleep"),
            self.assertRaisesRegex(RequiredFetchError, "Cloudflare challenge"),
        ):
            client.get(
                THE_INFORMATION_SUBSCRIBER_FEED,
                auth=("subscriber@example.com", "secret"),
                required=True,
            )

        self.assertEqual(request.call_count, 3)

    def test_cloudflare_retry_can_recover_without_losing_auth(self):
        challenge = Mock()
        challenge.status_code = 403
        challenge.url = THE_INFORMATION_SUBSCRIBER_FEED
        challenge.headers = {"cf-mitigated": "challenge"}
        challenge.text = "<title>Just a moment...</title>"
        success = Mock()
        success.status_code = 200
        success.url = THE_INFORMATION_SUBSCRIBER_FEED
        success.headers = {"content-type": "application/atom+xml"}
        success.encoding = "utf-8"
        success.text = "<feed><title>The Information</title></feed>"
        success.raise_for_status.return_value = None
        client = HttpClient(sleep_seconds=0, respect_robots=False)

        with (
            patch.object(
                client.session,
                "get",
                side_effect=[challenge, success],
            ) as request,
            patch("src.http_client.time.sleep"),
        ):
            result = client.get(
                THE_INFORMATION_SUBSCRIBER_FEED,
                auth=("subscriber@example.com", "secret"),
                required=True,
            )

        self.assertIsNotNone(result)
        self.assertEqual(request.call_count, 2)
        for call in request.call_args_list:
            self.assertEqual(
                call.kwargs["auth"],
                ("subscriber@example.com", "secret"),
            )

    def test_low_frequency_source_is_not_expected_daily(self):
        self.assertFalse(expects_daily_output("\u6bcf\u5468"))
        self.assertFalse(expects_daily_output("Monthly"))
        self.assertTrue(expects_daily_output("\u6bcf\u65e5"))

    def test_weekday_source_is_not_expected_on_weekend(self):
        self.assertTrue(expects_output_on_date("\u5de5\u4f5c\u65e5", date(2026, 7, 24)))
        self.assertFalse(expects_output_on_date("\u5de5\u4f5c\u65e5", date(2026, 7, 25)))
        self.assertFalse(expects_output_on_date("\u4f4e\u9891", date(2026, 7, 24)))

    def test_configured_rss_stops_at_chinese_punctuation(self):
        source = Source(
            name="feed",
            media_type="",
            domain="",
            sub_domain="",
            frequency="",
            description="",
            note="RSS: https://example.com/feed；正文使用公开摘要",
            url="https://example.com/",
        )
        self.assertEqual(source.configured_rss_url, "https://example.com/feed")

    def test_configured_rss_urls_include_uied_supplement_in_note_order(self):
        source = Source(
            name="IT之家",
            media_type="",
            domain="",
            sub_domain="",
            frequency="",
            description="",
            note=(
                "RSS: https://www.ithome.com/rss/；"
                "聚合备用RSS: https://uiedtool.com/rss-proxy/rss；"
                "聚合备用RSS: https://uiedtool.com/rss-proxy/rss"
            ),
            url="https://www.ithome.com/",
        )
        self.assertEqual(
            source.configured_rss_urls,
            (
                "https://www.ithome.com/rss/",
                "https://uiedtool.com/rss-proxy/rss",
            ),
        )

    def test_uied_feed_is_identified_as_discovery_platform(self):
        self.assertTrue(
            is_uied_aggregator_feed("https://uiedtool.com/rss-proxy/rss")
        )
        self.assertFalse(is_uied_aggregator_feed("https://www.ithome.com/rss/"))

    def test_feed_merge_deduplicates_original_article_urls(self):
        first = FeedEntry("one", "https://example.com/a", "")
        duplicate = FeedEntry("one duplicate", "https://www.example.com/a/", "")
        second = FeedEntry("two", "https://example.com/b", "")

        merged, added = merge_feed_entries([first], [duplicate, second])

        self.assertEqual(merged, [first, second])
        self.assertEqual(added, 1)

    def test_uied_discovery_entry_keeps_original_publisher_name(self):
        source = make_source("机器之心", "https://www.jiqizhixin.com/")
        entry = FeedEntry(
            "AI research headline",
            "https://www.jiqizhixin.com/articles/2026-09-05",
            "Sat, 05 Sep 2026 08:00:00 +0800",
            "Original publisher summary with enough useful discovery context.",
        )
        with patch("src.main.fetch_and_parse_article", return_value=None):
            article = enrich_from_rss_entry(None, source, entry)

        self.assertEqual(article["source_name"], "机器之心")
        self.assertNotEqual(article["source_name"], "UIED AI新闻")


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

    def test_sciencenet_ignores_placeholder_canonical_url(self):
        source = make_source("ScienceNet", "https://news.sciencenet.cn/")
        url = "https://news.sciencenet.cn/htmlnews/2026/7/568672.shtm"
        html = '<meta property="og:url" content="[path]"><title>ScienceNet article</title>'
        article = parse_article_html(html, url, source)
        self.assertEqual(article["url"], url)

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

    def test_url_dated_candidates_confirm_target_day_had_no_articles(self):
        source = make_source("example", "https://example.com/list")
        scraper = GenericListingScraper(StaticClient({}), source)
        urls = [
            "https://example.com/html/20260822/1.shtml",
            "https://example.com/html/20260821/2.shtml",
        ]
        with patch.object(scraper, "discover_article_urls", return_value=urls):
            articles = scraper.scrape(
                20,
                target_date=date(2026, 8, 23),
                candidate_limit=20,
            )

        self.assertEqual(articles, [])
        self.assertEqual(scraper.last_candidate_count, 2)
        self.assertEqual(scraper.last_date_filtered_count, 2)
        self.assertEqual(scraper.last_undated_candidate_count, 0)
        self.assertEqual(scraper.last_candidate_date_min, "2026-08-21")
        self.assertEqual(scraper.last_candidate_date_max, "2026-08-22")
        self.assertTrue(
            has_confirmed_non_target_candidates(
                scraper.last_candidate_count,
                scraper.last_date_filtered_count,
                scraper.last_undated_candidate_count,
            )
        )

    def test_undated_candidate_does_not_confirm_no_news(self):
        self.assertFalse(has_confirmed_non_target_candidates(2, 1, 1))

    def test_ordered_listing_of_older_articles_confirms_no_news(self):
        source = make_source("example", "https://example.com/list")
        scraper = GenericListingScraper(StaticClient({}), source)
        urls = [f"https://example.com/news/{index}.html" for index in range(20)]

        def older_article(_client, url, _source):
            return {
                "title": url,
                "published_at": "2026-08-21",
                "content": "x" * 500,
                "url": url,
            }

        with (
            patch.object(scraper, "discover_article_urls", return_value=urls),
            patch(
                "src.scrapers.generic.fetch_and_parse_article",
                side_effect=older_article,
            ),
        ):
            articles = scraper.scrape(20, target_date=date(2026, 8, 23))

        self.assertEqual(articles, [])
        self.assertTrue(scraper.last_target_date_absent)

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
        self.assertFalse(scraper.last_target_date_absent)

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

    def test_perovskite_info_discovers_drupal_story_teasers(self):
        source = make_source(
            "perovskite-info",
            "https://www.perovskite-info.com/perovskite-solar",
        )
        html = """
        <div class="view-content">
          <article class="node node--type-story node--view-mode-teaser">
            <h2 class="field--name-title">
              <a href="/stable-perovskite-cell">Stable perovskite cell reaches milestone</a>
            </h2>
          </article>
        </div>
        """
        client = StaticClient({source.url: html})

        urls = PerovskiteInfoScraper(client, source).discover_article_urls(20)

        self.assertEqual(
            urls,
            ["https://www.perovskite-info.com/stable-perovskite-cell"],
        )

    def test_nested_json_ld_publish_date_is_parsed(self):
        source = make_source("perovskite-info", "https://www.perovskite-info.com/")
        html = """
        <script type="application/ld+json">
          {"@graph":[{"@type":"NewsArticle","datePublished":"2026-07-27T06:00:00+0300"}]}
        </script>
        <article><h1>Perovskite milestone</h1><p>Long enough public article body text for parsing.</p></article>
        """
        article = parse_article_html(html, source.url, source)
        self.assertEqual(article["published_at"], "2026-07-27T06:00:00+0300")

    def test_json_ld_article_body_wins_over_short_dom_excerpt(self):
        source = make_source("example", "https://example.com/")
        structured_body = (
            "This is the complete structured article body. " + "detail " * 120
        )
        html = f"""
        <script type="application/ld+json">
          {{"@type":"NewsArticle","articleBody":"{structured_body}"}}
        </script>
        <article><p>Short public excerpt only.</p></article>
        """

        article = parse_article_html(html, source.url, source)

        self.assertGreater(len(article["content"]), 500)
        self.assertIn("complete structured article body", article["content"])

    def test_lists_tables_and_captions_are_preserved_in_article_body(self):
        source = make_source("example", "https://example.com/")
        html = """
        <article>
          <p>Introductory paragraph with enough context for the article.</p>
          <ul>
            <li>First material project milestone and its detailed outcome.</li>
            <li>Second material project milestone and its detailed outcome.</li>
          </ul>
          <table>
            <tr><th>Region and capacity</th><td>North region reaches 850 MW.</td></tr>
          </table>
          <figure><figcaption>Detailed project location caption.</figcaption></figure>
        </article>
        """

        article = parse_article_html(html, source.url, source)

        self.assertIn("First material project milestone", article["content"])
        self.assertIn("North region reaches 850 MW", article["content"])
        self.assertIn("Detailed project location caption", article["content"])
        self.assertEqual(article["content_status"], "full")

    def test_paywall_prompt_is_not_reported_as_full_content(self):
        source = make_source("example", "https://example.com/")
        html = """
        <article>
          <h1>Subscriber story</h1>
          <p>Subscribe to unlock this article and continue reading.</p>
        </article>
        """

        article = parse_article_html(html, source.url, source)

        self.assertEqual(article["content_status"], "incomplete")
        self.assertEqual(article["content_issue"], "paywall_or_login_wall")

    def test_default_content_quality_threshold_is_expanded(self):
        self.assertEqual(DEFAULT_MIN_CONTENT_CHARS, 500)

    def test_rss_public_excerpt_is_parsed(self):
        feed = """
        <rss><channel><item>
          <title>Public headline</title>
          <link>https://example.com/article</link>
          <pubDate>Mon, 27 Jul 2026 08:00:00 GMT</pubDate>
          <description><![CDATA[<p>Public RSS summary with useful context.</p>]]></description>
        </item></channel></rss>
        """
        entries = parse_feed(feed)
        self.assertEqual(entries[0].summary, "Public RSS summary with useful context.")

    def test_rss_public_excerpt_replaces_short_paywall_body(self):
        feed = """
        <rss><channel><item>
          <title>Public headline</title>
          <link>https://example.com/article</link>
          <description><![CDATA[
            <p>This public RSS excerpt contains substantially more useful context
            than the short subscription prompt returned by the article page.</p>
          ]]></description>
        </item></channel></rss>
        """
        entry = parse_feed(feed)[0]
        source = make_source("The Information", "https://www.theinformation.com/")
        paywall_article = {
            "title": "",
            "published_at": "",
            "content": "Subscribe to unlock",
            "url": entry.url,
        }
        with patch("src.main.fetch_and_parse_article", return_value=paywall_article):
            article = enrich_from_rss_entry(None, source, entry)
        self.assertIn("substantially more useful context", article["content"])
        self.assertEqual(article["content_status"], "incomplete")

    def test_rss_content_is_used_when_article_page_cannot_be_parsed(self):
        feed = """
        <rss><channel><item>
          <title>Subscriber headline</title>
          <link>https://www.theinformation.com/articles/subscriber-story</link>
          <pubDate>Tue, 28 Jul 2026 08:00:00 GMT</pubDate>
          <description><![CDATA[
            <p>Authenticated subscriber feed content that remains available
            even when the linked article page cannot be parsed.</p>
          ]]></description>
        </item></channel></rss>
        """
        entry = parse_feed(feed)[0]
        source = make_source("The Information", "https://www.theinformation.com/")
        with patch("src.main.fetch_and_parse_article", return_value=None):
            article = enrich_from_rss_entry(
                None,
                source,
                entry,
                feed_declared_full=True,
            )

        self.assertEqual(article["title"], "Subscriber headline")
        self.assertIn("Authenticated subscriber feed content", article["content"])
        self.assertEqual(article["source_name"], "The Information")
        self.assertEqual(article["content_status"], "full")

    def test_content_encoded_feed_entry_is_declared_full(self):
        feed = """
        <rss xmlns:content="http://purl.org/rss/1.0/modules/content/">
          <channel><item>
            <title>Full feed story</title>
            <link>https://example.com/full-feed-story</link>
            <description>Short summary.</description>
            <content:encoded><![CDATA[
              <p>First complete paragraph from the publisher.</p>
              <p>Second complete paragraph with the conclusion.</p>
            ]]></content:encoded>
          </item></channel>
        </rss>
        """

        entry = parse_feed(feed)[0]

        self.assertTrue(entry.content_is_full)
        self.assertIn("Second complete paragraph", entry.summary)

    def test_the_information_uses_official_subscriber_feed_with_both_secrets(self):
        feed_url, auth, required, crawl_mode = resolve_feed_access(
            "the information",
            "https://www.theinformation.com/feed",
            environ={
                "THE_INFORMATION_RSS_USERNAME": "subscriber@example.com",
                "THE_INFORMATION_RSS_PASSWORD": "secret",
            },
        )

        self.assertEqual(feed_url, THE_INFORMATION_SUBSCRIBER_FEED)
        self.assertEqual(auth, ("subscriber@example.com", "secret"))
        self.assertTrue(required)
        self.assertEqual(crawl_mode, "rss_authenticated")

    def test_the_information_rejects_partial_secret_configuration(self):
        with self.assertRaisesRegex(ValueError, "must both be configured"):
            resolve_feed_access(
                "the information",
                "https://www.theinformation.com/feed",
                environ={"THE_INFORMATION_RSS_USERNAME": "subscriber@example.com"},
            )

    def test_the_information_keeps_public_feed_without_secrets(self):
        feed_url, auth, required, crawl_mode = resolve_feed_access(
            "the information",
            "https://www.theinformation.com/feed",
            environ={},
        )

        self.assertEqual(feed_url, "https://www.theinformation.com/feed")
        self.assertIsNone(auth)
        self.assertFalse(required)
        self.assertEqual(crawl_mode, "rss_public")

    def test_the_information_falls_back_to_official_public_feed(self):
        public_entry = FeedEntry(
            title="Public headline",
            url="https://www.theinformation.com/articles/public-headline",
            published_at="Fri, 04 Sep 2026 12:00:00 +0000",
        )
        with patch(
            "src.main.fetch_feed_entries",
            side_effect=[
                RequiredFetchError("Cloudflare challenge"),
                [public_entry],
            ],
        ) as fetch:
            entries, crawl_mode = fetch_feed_with_public_fallback(
                object(),
                "the information",
                THE_INFORMATION_SUBSCRIBER_FEED,
                100,
                auth=("subscriber@example.com", "secret"),
                required=True,
                crawl_mode="rss_authenticated",
            )

        self.assertEqual(entries, [public_entry])
        self.assertEqual(crawl_mode, "rss_public_fallback")
        self.assertEqual(fetch.call_args_list[1].args[1], THE_INFORMATION_PUBLIC_FEED)
        self.assertEqual(fetch.call_args_list[1].kwargs, {})

    def test_required_authenticated_fetch_forwards_auth_without_leaking_it(self):
        response = Mock()
        response.status_code = 401
        response.raise_for_status.side_effect = requests.HTTPError(
            "unauthorized",
            response=response,
        )
        client = HttpClient(sleep_seconds=0, respect_robots=False)
        with patch.object(client.session, "get", return_value=response) as request:
            with self.assertRaises(RequiredFetchError) as raised:
                client.get(
                    THE_INFORMATION_SUBSCRIBER_FEED,
                    auth=("subscriber@example.com", "secret"),
                    required=True,
                )

        request.assert_called_once()
        self.assertEqual(
            request.call_args.kwargs["auth"],
            ("subscriber@example.com", "secret"),
        )
        self.assertIn("HTTP 401", str(raised.exception))
        self.assertNotIn("subscriber@example.com", str(raised.exception))
        self.assertNotIn("secret", str(raised.exception))

    def test_renewables_now_filters_navigation_links(self):
        source = make_source("Renewables Now", "https://renewablesnow.com/news/")
        html = """
        <a href="/news/solar/">Solar sector</a>
        <a href="/advanced-search/">Advanced search</a>
        <a href="/news/real-project-headline-1298706/">Real article</a>
        <a href="/news/archive/">Archive</a>
        """
        client = StaticClient({source.url: html})
        urls = RenewablesNowScraper(client, source).discover_article_urls(20)
        self.assertEqual(
            urls,
            ["https://renewablesnow.com/news/real-project-headline-1298706/"],
        )

    def test_renewables_now_extracts_article_body_without_page_chrome(self):
        source = make_source("Renewables Now", "https://renewablesnow.com/news/")
        embedded_body = """
        <p>German vertical bifacial photovoltaics firm Next2Sun AG is launching
        a share issue to finance its next phase of growth.</p>
        <p>The company seeks to accelerate implementation of its own solar
        projects and scale its business model.</p>
        <p class="article_reportLayer">Power your inbox with newsletters.</p>
        <p>Next2Sun expects project volume of more than 70 MW in 2027.</p>
        """.strip()
        flight_record = f"6d:T{len(embedded_body):x},{embedded_body}6e:{{}}"
        encoded_record = json.dumps(flight_record).replace("<", "\\u003c").replace(
            ">", "\\u003e"
        )
        html = f"""
        <html><body>
          <script>self.__next_f.push([1,{encoded_record}])</script>
          <div class="info-article">
            <h1>Next2Sun launches EUR-5m share issue</h1>
            <div>Aug 25, 2026, 4:58:20 PM</div>
            <div class="paywall">
              <div class="styles_leadArticleText__etnRf">
                <div>German vertical bifacial photovoltaics firm Next2Sun AG
                is launching a share issue to finance its next phase of growth.</div>
              </div>
              <div class="text-just">
                <div class="styles_leadArticleText__etnRf">
                  <p>The company seeks to accelerate implementation of its own
                  solar projects and scale its business model.</p>
                  <p class="article_reportLayer">Power your inbox with newsletters.</p>
                  <p>Next2Sun expects project volume of more than 70 MW in 2027.</p>
                </div>
              </div>
            </div>
          </div>
          <aside>
            <div>about 13 hours ago</div><div>Loading...</div><div>Loading...</div>
            <div>MESIA Business Breakfast on Smart Cities</div>
            <div>Horizons Clean Energy Expansion India Conference</div>
          </aside>
        </body></html>
        """

        parsed = parse_article_html(
            html,
            "https://renewablesnow.com/news/next2sun-launches-eur-5m-share-issue-1300157/",
            source,
        )

        self.assertIn("German vertical bifacial", parsed["content"])
        self.assertIn("more than 70 MW", parsed["content"])
        self.assertNotIn("Loading", parsed["content"])
        self.assertNotIn("Business Breakfast", parsed["content"])
        self.assertNotIn("Power your inbox", parsed["content"])
        self.assertEqual(parsed["content_status"], "full")
        self.assertEqual(
            parsed["content_extraction"],
            "nextjs_embedded_full_text",
        )

    def test_content_quality_rejects_loading_and_event_template_noise(self):
        content = """
        about 13 hours ago
        &#x20; about 16 hours ago
        &#x20; Loading...
        &#x20; Loading...
        &#x20; about 13 hours ago
        &#x20; MESIA Business Breakfast on Smart Cities
        &#x20; Horizons Clean Energy Expansion India Conference
        """

        self.assertEqual(
            assess_content(content, extraction_method="trafilatura_full_text"),
            ("incomplete", "template_or_navigation_noise"),
        )

    def test_renewables_now_extracts_body_field_split_across_flight_chunks(self):
        source = make_source("Renewables Now", "https://renewablesnow.com/news/")
        body = (
            "<p>German solar developer started construction of a solar park.</p>"
            "<p>The project will generate enough electricity for local homes.</p>"
            "<p>Commissioning is targeted for the end of 2026.</p>"
        )
        split_at = body.index("local homes")
        first = json.dumps(f'6c:{{"body":{json.dumps(body[:split_at])[0:-1]}')
        second = json.dumps(
            f'{json.dumps(body[split_at:])[1:]},"access":true}}\n'
        )
        html = f"""
        <html><body>
          <script>self.__next_f.push([1,{first}])</script>
          <script>self.__next_f.push([1,{second}])</script>
          <div class="info-article"><div class="paywall">
            <p>German solar developer started construction of a solar park.</p>
          </div></div>
        </body></html>
        """

        parsed = parse_article_html(
            html,
            "https://renewablesnow.com/news/example-split-body-1299932/",
            source,
        )

        self.assertIn("local homes", parsed["content"])
        self.assertIn("end of 2026", parsed["content"])
        self.assertEqual(parsed["content_status"], "full")
        self.assertEqual(
            parsed["content_extraction"],
            "nextjs_embedded_full_text",
        )

    def test_renewables_now_lead_only_fallback_is_not_marked_full(self):
        source = make_source("Renewables Now", "https://renewablesnow.com/news/")
        html = """
        <div class="info-article"><div class="paywall">
          <p>This is only the short server-rendered lead paragraph while the
          actual article body is still waiting for its dynamic data.</p>
        </div></div>
        """

        parsed = parse_article_html(
            html,
            "https://renewablesnow.com/news/example-story-1300157/",
            source,
        )

        self.assertEqual(parsed["content_status"], "incomplete")
        self.assertEqual(
            parsed["content_issue"],
            "dynamic_full_text_unavailable",
        )

    def test_ne_time_uses_first_content_line_when_page_title_is_site_name(self):
        source = make_source("NE时代", "https://www.ne-time.cn/")
        html = """
        <html>
          <head>
            <meta property="og:title" content="NE时代">
            <title>NE时代</title>
          </head>
          <body>
            <article>
              <p>空中客车与 MTU 合作开发氢燃料电池发动机</p>
              <p>双方计划成立合资企业推动航空动力系统商业化。</p>
            </article>
          </body>
        </html>
        """

        parsed = parse_article_html(
            html,
            "https://www.ne-time.cn/web/article/123",
            source,
        )

        self.assertEqual(
            parsed["title"],
            "空中客车与 MTU 合作开发氢燃料电池发动机",
        )


if __name__ == "__main__":
    unittest.main()
