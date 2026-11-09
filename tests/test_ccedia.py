from __future__ import annotations

import unittest
from datetime import date
from pathlib import Path

from src.article_parser import parse_article_html
from src.http_client import FetchResult
from src.load_sources import Source, load_sources
from src.scrapers import get_scraper_class
from src.scrapers.ccedia import CCEDIAScraper


def source(url="https://www.ccedia.com/news/11/"):
    return Source("中国能源产业发展网—能源头条", "行业媒体", "综合新能源", "综合能源", "每日", "", "", url)


def listing(cards, next_url=""):
    rows = "".join(
        f'<div class="p_loopitem"><p class="s_title"><a href="{href}">{title}</a></p>'
        f'<p class="e_timeFormat-9">{day}</p></div>'
        for href, title, day in cards
    )
    next_link = f'<a class="page_next" href="{next_url}">next</a>' if next_url else ""
    return f'<a href="/energy_detail/c-_detailId%3D999.html">navigation</a><div id="c_new_list_139-1"><div class="p_list">{rows}</div><div class="p_page">{next_link}</div></div>'


class Client:
    def __init__(self, pages):
        self.pages = pages
        self.calls = []

    def get(self, url):
        self.calls.append(url)
        html = self.pages.get(url)
        return FetchResult(url, html, 200, "text/html") if html else None


class CCEDIATests(unittest.TestCase):
    def test_all_ten_sources_have_dedicated_scraper(self):
        items = [item for item in load_sources(Path("sources.xlsx")) if item.name.startswith("中国能源产业发展网—")]
        self.assertEqual(len(items), 10)
        self.assertEqual(len({item.url for item in items}), 10)
        self.assertTrue(all(get_scraper_class(item.name) is CCEDIAScraper for item in items))

    def test_pinned_old_item_does_not_prevent_pagination(self):
        root = "https://www.ccedia.com/news/11/"
        page2 = "https://www.ccedia.com/energy/123-15-15.html"
        old = "/energy_detail/c-_detailId%3D1.html"
        today = "/energy_detail/c-_detailId%3D2.html"
        target = "/energy_detail/c-_detailId%3D3.html"
        pages = {
            root: listing([(old, "置顶旧文", "2026-10-08"), (today, "今日新闻", "2026-11-09")], "/energy/123-15-15.html"),
            page2: listing([(target, "目标日期的新闻", "2026-11-08")]),
        }
        scraper = CCEDIAScraper(Client(pages), source())
        scraper._target_date = date(2026, 11, 8)
        urls = scraper.discover_article_urls(20)
        self.assertIn(f"https://www.ccedia.com{target}", urls)
        self.assertNotIn("https://www.ccedia.com/energy_detail/c-_detailId%3D999.html", urls)
        self.assertEqual(scraper.listing_candidate_dates[f"https://www.ccedia.com{target}"], date(2026, 11, 8))

    def test_article_uses_actual_date_and_bounded_body(self):
        html = '<title>能源发展动态-中国能源产业发展网</title><p class="e_timeFormat-30">2026-11-08 19:11</p><div class="e_richText-7"><p>能源项目的进展、技术路径和产业应用。</p></div><div class="e_richText-70">站点推荐</div>'
        article = parse_article_html(html, "https://www.ccedia.com/energy_detail/c-_detailId%3D123.html", source())
        self.assertTrue(article["published_at"].startswith("2026-11-08"))
        self.assertEqual(article["title"], "能源发展动态")
        self.assertIn("能源项目", article["content"])
        self.assertNotIn("站点推荐", article["content"])


if __name__ == "__main__":
    unittest.main()
