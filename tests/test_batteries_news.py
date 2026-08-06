from __future__ import annotations

import unittest
from datetime import date

from src.http_client import FetchResult
from src.load_sources import Source
from src.scrapers.batteries_news import BatteriesNewsScraper


def source() -> Source:
    return Source(
        name="Batteries News",
        media_type="垂直领域媒体",
        domain="电池",
        sub_domain="综合电池新闻",
        frequency="实时",
        description="",
        note="",
        url="https://batteriesnews.com/",
    )


def listing(cards: list[tuple[str, str]], next_url: str = "") -> str:
    rendered = "".join(
        f"""
        <article class="gridlove-post">
          <h2 class="entry-title"><a href="{url}">Article</a></h2>
          <div class="meta-date"><span class="updated">{published}</span></div>
        </article>
        """
        for url, published in cards
    )
    pagination = f'<a href="{next_url}">Load More</a>' if next_url else ""
    return f"""
    <div class="gridlove-module module-type-posts" id="latest-module">
      <div class="module-header"><h2>📢 Latest</h2></div>
      {rendered}
    </div>
    {pagination}
    """


def detail(title: str, published: str, body: str) -> str:
    return f"""
    <html><head>
      <meta property="og:title" content="{title}">
      <meta property="article:published_time" content="{published}">
    </head><body>
      <div class="gridlove-content"><div class="entry-content"><p>{body}</p></div></div>
      <aside><p>{'sidebar noise ' * 100}</p></aside>
    </body></html>
    """


class StaticClient:
    def __init__(self, pages: dict[str, str]) -> None:
        self.pages = pages
        self.requested: list[str] = []

    def get(self, url: str, **_kwargs):
        self.requested.append(url)
        html = self.pages.get(url)
        if html is None:
            return None
        return FetchResult(url=url, text=html, status_code=200, content_type="text/html")


class BatteriesNewsTests(unittest.TestCase):
    def test_reads_only_latest_module_and_target_date(self):
        article_url = "https://batteriesnews.com/current-story/"
        pages = {
            "https://batteriesnews.com/": listing(
                [
                    (article_url, "August 4, 2026"),
                    ("https://batteriesnews.com/older-story/", "July 22, 2026"),
                ],
                "https://batteriesnews.com/page/2/",
            ),
            article_url: detail("Current story", "2026-08-04T08:00:00+00:00", "Complete article body " * 80),
        }
        client = StaticClient(pages)
        scraper = BatteriesNewsScraper(client, source())
        articles = scraper.scrape(target_date=date(2026, 8, 4), candidate_limit=100)

        self.assertEqual(len(articles), 1)
        self.assertEqual(articles[0]["title"], "Current story")
        self.assertNotIn("sidebar noise", articles[0]["content"])
        self.assertNotIn("https://batteriesnews.com/page/2/", client.requested)
        self.assertEqual(scraper.last_fetched_count, 1)

    def test_follows_load_more_until_target_date_page(self):
        article_url = "https://batteriesnews.com/target-story/"
        pages = {
            "https://batteriesnews.com/": listing(
                [("https://batteriesnews.com/newer-story/", "August 4, 2026")],
                "https://batteriesnews.com/page/2/",
            ),
            "https://batteriesnews.com/page/2/": listing(
                [
                    (article_url, "July 21, 2026"),
                    ("https://batteriesnews.com/older-story/", "July 20, 2026"),
                ]
            ),
            article_url: detail("Target story", "2026-07-21T08:00:00+00:00", "Target article body " * 80),
        }
        client = StaticClient(pages)
        scraper = BatteriesNewsScraper(client, source())
        articles = scraper.scrape(target_date=date(2026, 7, 21), candidate_limit=100)

        self.assertEqual([article["title"] for article in articles], ["Target story"])
        self.assertIn("https://batteriesnews.com/page/2/", client.requested)


if __name__ == "__main__":
    unittest.main()
