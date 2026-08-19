from __future__ import annotations

import unittest
from datetime import date

from src.content_quality import FULL_CONTENT_STATUS, INCOMPLETE_CONTENT_STATUS, assess_content
from src.http_client import FetchResult
from src.load_sources import Source
from src.scrapers.interesting_engineering import InterestingEngineeringScraper


def make_source() -> Source:
    return Source(
        name="interesting engineering",
        media_type="垂直领域媒体",
        domain="综合科技",
        sub_domain="无",
        frequency="实时",
        description="",
        note="RSS: https://interestingengineering.com/feed",
        url="https://interestingengineering.com/news",
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


def listing(day: str, article_path: str, next_path: str = "") -> str:
    next_link = (
        f'<a aria-label="Go to next page" href="{next_path}">next</a>'
        if next_path
        else ""
    )
    return f"""
    <article>
      <h1>news</h1>
      <section>
        <div>{day}</div>
        <div><h3><a href="{article_path}">A sufficiently long article title</a></h3></div>
      </section>
      {next_link}
    </article>
    """


def rss(article_url: str, content: str) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0"
      xmlns:content="http://purl.org/rss/1.0/modules/content/">
      <channel><item>
        <title>Full public RSS article</title>
        <link>{article_url}</link>
        <pubDate>Wed, 05 Aug 2026 23:30:00 +0000</pubDate>
        <content:encoded><![CDATA[<p>{content}</p>]]></content:encoded>
      </item></channel>
    </rss>"""


class InterestingEngineeringTests(unittest.TestCase):
    def test_listing_reads_news_cards_and_next_page_only(self):
        html = listing(
            "8/6/2026",
            "/energy/public-news-story",
            "/news/page/2",
        ) + '<aside><h3><a href="/innovation/sidebar-story">Sidebar</a></h3></aside>'
        cards, next_url = InterestingEngineeringScraper.parse_listing(
            html,
            "https://interestingengineering.com/news",
        )
        self.assertEqual(
            [card.url for card in cards],
            ["https://interestingengineering.com/energy/public-news-story"],
        )
        self.assertEqual(cards[0].published_date, date(2026, 8, 6))
        self.assertEqual(next_url, "https://interestingengineering.com/news/page/2")

    def test_scraper_follows_pagination_and_prefers_public_rss_full_text(self):
        source = make_source()
        article_url = "https://interestingengineering.com/energy/target-story"
        full_text = "Public RSS full text " * 80
        pages = {
            source.url: listing(
                "8/7/2026",
                "/energy/newer-story",
                "/news/page/2",
            ),
            "https://interestingengineering.com/news/page/2": listing(
                "8/6/2026",
                "/energy/target-story",
            ),
            source.configured_rss_url: rss(article_url, full_text),
        }
        scraper = InterestingEngineeringScraper(StaticClient(pages), source)
        articles = scraper.scrape(
            10,
            target_date=date(2026, 8, 6),
            candidate_limit=50,
        )
        self.assertEqual(len(articles), 1)
        self.assertEqual(articles[0]["url"], article_url)
        self.assertGreater(len(articles[0]["content"]), 500)
        self.assertEqual(articles[0]["content_extraction"], "rss_full_content")
        self.assertEqual(scraper.last_candidate_count, 2)

    def test_rss_timestamp_overrides_previous_day_listing_date(self):
        source = make_source()
        article_url = "https://interestingengineering.com/energy/timezone-story"
        pages = {
            source.url: listing("8/5/2026", "/energy/timezone-story"),
            source.configured_rss_url: rss(article_url, "Public full text " * 80),
        }
        articles = InterestingEngineeringScraper(StaticClient(pages), source).scrape(
            10,
            target_date=date(2026, 8, 6),
        )
        self.assertEqual(len(articles), 1)
        self.assertEqual(articles[0]["url"], article_url)

    def test_public_detail_preview_is_used_when_feed_has_no_item(self):
        source = make_source()
        article_url = "https://interestingengineering.com/energy/preview-story"
        pages = {
            source.url: listing("8/6/2026", "/energy/preview-story"),
            source.configured_rss_url: "<rss><channel></channel></rss>",
            article_url: """
                <html><head><meta property="article:published_time"
                content="2026-08-06T08:00:00+00:00"></head>
                <body><h1>Preview story</h1><div class="body-content">
                <p>This is the first publicly visible preview paragraph with useful details.</p>
                <p>This is the second publicly visible preview paragraph with useful details.</p>
                </div><div id="paywall-div">Subscribe</div></body></html>
            """,
        }
        articles = InterestingEngineeringScraper(StaticClient(pages), source).scrape(
            10,
            target_date=date(2026, 8, 6),
        )
        self.assertEqual(len(articles), 1)
        self.assertIn("first publicly visible preview", articles[0]["content"])
        self.assertNotIn("Subscribe", articles[0]["content"])
        self.assertEqual(articles[0]["content_extraction"], "public_preview")
        status, issue = assess_content(
            articles[0]["content"],
            extraction_method=articles[0]["content_extraction"],
        )
        self.assertEqual(status, INCOMPLETE_CONTENT_STATUS)
        self.assertEqual(issue, "public_preview_only")

    def test_substantive_public_detail_is_kept_as_full_text(self):
        source = make_source()
        article_url = "https://interestingengineering.com/energy/public-full-story"
        pages = {
            source.url: listing("8/6/2026", "/energy/public-full-story"),
            source.configured_rss_url: "<rss><channel></channel></rss>",
            article_url: f"""
                <html><head><meta property="article:published_time"
                content="2026-08-06T08:00:00+00:00"></head>
                <body><h1>Substantive public story</h1><div class="body-content">
                <p>{"Detailed public reporting with technical context. " * 40}</p>
                </div></body></html>
            """,
        }
        articles = InterestingEngineeringScraper(StaticClient(pages), source).scrape(
            10,
            target_date=date(2026, 8, 6),
        )
        self.assertEqual(len(articles), 1)
        self.assertGreater(len(articles[0]["content"]), 800)
        self.assertNotEqual(articles[0]["content_extraction"], "public_preview")
        status, issue = assess_content(
            articles[0]["content"],
            extraction_method=articles[0]["content_extraction"],
        )
        self.assertEqual((status, issue), (FULL_CONTENT_STATUS, ""))


if __name__ == "__main__":
    unittest.main()
