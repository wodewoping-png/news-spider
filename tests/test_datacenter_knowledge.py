from __future__ import annotations

import unittest
from datetime import date

from src.content_quality import INCOMPLETE_CONTENT_STATUS
from src.http_client import FetchResult
from src.load_sources import Source
from src.scrapers.datacenter_knowledge import DataCenterKnowledgeScraper


def source() -> Source:
    return Source(
        name="Data Center Knowledge",
        media_type="vertical media",
        domain="data centers",
        sub_domain="infrastructure and operations",
        frequency="daily",
        description="",
        note="RSS: https://www.datacenterknowledge.com/rss.xml",
        url="https://www.datacenterknowledge.com/latest-news",
    )


class StaticClient:
    def __init__(self, pages: dict[str, str]) -> None:
        self.pages = pages
        self.requested: list[str] = []

    def get(self, url: str, **_kwargs):
        self.requested.append(url)
        html = self.pages.get(url)
        if html is None:
            return None
        content_type = "text/xml" if url.endswith(".xml") else "text/html"
        return FetchResult(
            url=url,
            text=html,
            status_code=200,
            content_type=content_type,
        )


def card(css_class: str, title_class: str, date_class: str, url: str, day: str) -> str:
    return f"""
    <div class="ContentPreview {css_class}">
      <a class="{title_class}" href="{url}">A sufficiently long title</a>
      <span class="{date_class}">{day}</span>
    </div>
    """


def listing(
    featured: str = "",
    latest: str = "",
    regular: str = "",
    next_url: str = "",
) -> str:
    pagination = (
        f'<nav class="ListContent-Pagination"><a aria-label="Go to Next page 2" '
        f'href="{next_url}">Next</a></nav>'
        if next_url
        else ""
    )
    return f"""
    <main class="ListContent">
      <div class="ListContent-Content_featured">{featured}</div>
      <div class="ListContent-Content_latest">{latest}</div>
      {regular}
      {pagination}
    </main>
    """


def rss(url: str, published: str, description: str = "Public feed excerpt") -> str:
    return f"""<?xml version="1.0"?>
    <rss><channel><item>
      <title>RSS title</title><link>{url}</link>
      <pubDate>{published}</pubDate>
      <description><![CDATA[{description}]]></description>
    </item></channel></rss>"""


def detail(body: str) -> str:
    return f"""
    <html><head><meta property="og:title" content="Detail title"></head><body>
      <main><div class="ArticleBase-BodyContent_Article">
        <p>{body}</p>
      </div><aside><p>{'sidebar noise ' * 100}</p></aside></main>
    </body></html>
    """


class DataCenterKnowledgeTests(unittest.TestCase):
    def test_listing_combines_all_news_groups_and_deduplicates_urls(self):
        duplicate = "/infrastructure/top-story"
        html = listing(
            featured=card(
                "ListContent-Content_featured",
                "ArticlePreview-Title",
                "ArticlePreview-Date",
                duplicate,
                "Aug 5, 2026",
            ),
            latest=card(
                "ListContent-LatestItem",
                "ContentCard-Title",
                "ContentCard-Date",
                duplicate,
                "Aug 5, 2026",
            )
            + card(
                "ListContent-LatestItem",
                "ContentCard-Title",
                "ContentCard-Date",
                "/energy/latest-story",
                "Aug 5, 2026",
            ),
            regular=card(
                "ListContent-ContentItem",
                "ListPreview-Title",
                "ListPreview-Date",
                "/operations/list-story",
                "Aug 4, 2026",
            ),
            next_url="/latest-news?page=2",
        )
        cards, next_url = DataCenterKnowledgeScraper.parse_listing(
            html,
            "https://www.datacenterknowledge.com/latest-news",
        )
        self.assertEqual(
            [item.url for item in cards],
            [
                "https://www.datacenterknowledge.com/infrastructure/top-story",
                "https://www.datacenterknowledge.com/energy/latest-story",
                "https://www.datacenterknowledge.com/operations/list-story",
            ],
        )
        self.assertEqual(cards[0].published_date, date(2026, 8, 5))
        self.assertEqual(
            next_url,
            "https://www.datacenterknowledge.com/latest-news?page=2",
        )

    def test_scraper_follows_pagination_and_uses_detail_full_text(self):
        article_url = "https://www.datacenterknowledge.com/energy/target-story"
        page_two = "https://www.datacenterknowledge.com/latest-news?page=2"
        full_body = "Complete public detail paragraph. " * 80
        pages = {
            source().url: listing(
                regular=card(
                    "ListContent-ContentItem",
                    "ListPreview-Title",
                    "ListPreview-Date",
                    "/energy/newer-story",
                    "Aug 6, 2026",
                ),
                next_url=page_two,
            ),
            page_two: listing(
                regular=card(
                    "ListContent-ContentItem",
                    "ListPreview-Title",
                    "ListPreview-Date",
                    "/energy/target-story",
                    "Aug 5, 2026",
                )
            ),
            source().configured_rss_url: rss(
                article_url,
                "Wed, 05 Aug 2026 20:31:51 GMT",
            ),
            article_url: detail(full_body),
        }
        client = StaticClient(pages)
        articles = DataCenterKnowledgeScraper(client, source()).scrape(
            10,
            target_date=date(2026, 8, 6),
            candidate_limit=100,
        )
        self.assertEqual(len(articles), 1)
        self.assertEqual(articles[0]["url"], article_url)
        self.assertGreater(len(articles[0]["content"]), 1000)
        self.assertNotIn("sidebar noise", articles[0]["content"])
        self.assertIn(page_two, client.requested)

    def test_rss_description_is_only_an_incomplete_fallback(self):
        article_url = "https://www.datacenterknowledge.com/energy/feed-only"
        pages = {
            source().url: listing(
                featured=card(
                    "ListContent-Content_featured",
                    "ArticlePreview-Title",
                    "ArticlePreview-Date",
                    "/energy/feed-only",
                    "Aug 5, 2026",
                )
            ),
            source().configured_rss_url: rss(
                article_url,
                "Wed, 05 Aug 2026 20:31:51 GMT",
                "A useful but incomplete public feed description.",
            ),
        }
        articles = DataCenterKnowledgeScraper(
            StaticClient(pages),
            source(),
        ).scrape(10, target_date=date(2026, 8, 6))
        self.assertEqual(len(articles), 1)
        self.assertEqual(articles[0]["content_status"], INCOMPLETE_CONTENT_STATUS)
        self.assertEqual(articles[0]["content_extraction"], "rss_excerpt")

    def test_scraper_includes_rss_only_item_before_listing_refreshes(self):
        article_url = "https://www.datacenterknowledge.com/energy/rss-first"
        pages = {
            source().url: listing(
                featured=card(
                    "ListContent-Content_featured",
                    "ArticlePreview-Title",
                    "ArticlePreview-Date",
                    "/energy/older-listing-story",
                    "Aug 4, 2026",
                )
            ),
            source().configured_rss_url: rss(
                article_url,
                "Wed, 05 Aug 2026 20:31:51 GMT",
            ),
            article_url: detail("RSS-first full article body. " * 80),
        }
        articles = DataCenterKnowledgeScraper(
            StaticClient(pages),
            source(),
        ).scrape(10, target_date=date(2026, 8, 6))
        self.assertEqual([article["url"] for article in articles], [article_url])
        self.assertGreater(len(articles[0]["content"]), 1000)

    def test_scraper_records_complete_non_target_date_evidence(self):
        old_url = "https://www.datacenterknowledge.com/energy/old-story"
        pages = {
            source().url: listing(
                featured=card(
                    "ListContent-Content_featured",
                    "ArticlePreview-Title",
                    "ArticlePreview-Date",
                    "/energy/old-story",
                    "Aug 22, 2026",
                )
            ),
            source().configured_rss_url: rss(
                old_url,
                "Sat, 22 Aug 2026 12:00:00 GMT",
            ),
        }
        scraper = DataCenterKnowledgeScraper(StaticClient(pages), source())

        articles = scraper.scrape(10, target_date=date(2026, 8, 23))

        self.assertEqual(articles, [])
        self.assertEqual(scraper.last_candidate_count, 1)
        self.assertEqual(scraper.last_date_filtered_count, 1)
        self.assertEqual(scraper.last_undated_candidate_count, 0)
        self.assertEqual(scraper.last_candidate_date_min, "2026-08-22")
        self.assertEqual(scraper.last_candidate_date_max, "2026-08-22")


if __name__ == "__main__":
    unittest.main()
