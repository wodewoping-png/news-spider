import unittest
from datetime import date
from pathlib import Path
from src.article_parser import parse_article_html
from src.http_client import FetchResult, request_headers_for_url, BROWSER_USER_AGENT
from src.load_sources import Source, load_sources
from src.scrapers import get_scraper_class
from src.scrapers.industry_press import PESWindScraper, RecyclingInsideScraper

PES = Source('PES—Wind Press Releases', '行业媒体', '风能', '', '不定期', '', '', 'https://pes.eu.com/press-releases/tag/wind')
RECYCLING = Source('RecyclingInside—Recycling & Waste News', '行业媒体', '资源循环', '', '不定期', '', '', 'https://recyclinginside.com/recycling-waste-news/')

class Client:
    def __init__(self, pages):
        self.pages, self.calls, self.last_failure_reason = pages, [], ''
    def get(self, url, **kwargs):
        self.calls.append(url)
        self.last_failure_reason = ''
        if url not in self.pages:
            self.last_failure_reason = 'HTTP 503'
            return None
        return FetchResult(url, self.pages[url], 200, 'text/html')

def pes_card(url, day='06 November, 2026'):
    return f'<article><a href="{url}"><p class="p-small">Wind, Press Releases — {day}</p><h3>Wind technology news</h3></a></article>'
def pes_list(cards, next_url=''):
    return f'<div id="hs_cos_wrapper_blog_listing_body">{cards}</div><link rel="next" href="{next_url}">'
def recycling_card(url, stamp='2026-11-26T23:30:00+01:00'):
    return f'<article class="gs-post-card"><h3 class="gs-post-card__title"><a href="{url}">Sorting equipment news</a></h3><time datetime="{stamp}"></time></article>'

class IndustryPressTests(unittest.TestCase):
    def test_sources_loaded_once_and_registered(self):
        rows=load_sources(Path('sources.xlsx'))
        for source, cls in [(PES,PESWindScraper),(RECYCLING,RecyclingInsideScraper)]:
            matching=[s for s in rows if s.url==source.url]
            self.assertEqual(len(matching),1)
            self.assertIs(get_scraper_class(matching[0].name),cls)
            self.assertIsNone(matching[0].skip_reason)
            self.assertTrue(cls.handles_configured_feed)

    def test_pes_scope_dedup_and_pagination(self):
        article='https://pes.eu.com/press-releases/wind-one'
        page2=PES.url+'/page/2'
        pages={PES.url:pes_list(pes_card(article)+pes_card(article+'?utm_source=test')+pes_card('https://other.eu.com/press-releases/fake'),page2),page2:pes_list(pes_card('/press-releases/wind-two'),'https://pes.eu.com/press-releases/tag/solar/page/3')}
        client=Client(pages);scraper=PESWindScraper(client,PES)
        self.assertEqual(scraper.discover_article_urls(20),[article,'https://pes.eu.com/press-releases/wind-two'])
        self.assertEqual(client.calls,[PES.url,page2])

    def test_pes_beijing_day_uses_detail_timestamp_not_list_day(self):
        url='https://pes.eu.com/press-releases/wind-one'
        body='Wind project technical results and operating evidence. '*20
        detail=f'<meta property="og:title" content="Wind news"><meta property="article:published_time" content="2026-11-06T16:10:54Z"><section class="post-body"><article><div><p>{body}</p></div></article></section>'
        scraper=PESWindScraper(Client({PES.url:pes_list(pes_card(url)),url:detail}),PES)
        articles=scraper.scrape(target_date=date(2026,11,7),candidate_limit=5)
        self.assertEqual(len(articles),1)
        self.assertEqual(articles[0]['published_at'],'2026-11-06T16:10:54Z')

    def test_recycling_excludes_video_sidebar_and_normalizes_time(self):
        url='https://recyclinginside.com/news/sorting-system/'
        html='<section id="latest">'+recycling_card(url)+recycling_card(url+'#top')+recycling_card('https://other.com/news/fake/')+'</section><section id="videos">'+recycling_card('/news/video/')+'</section>'
        scraper=RecyclingInsideScraper(Client({RECYCLING.url:html}),RECYCLING)
        self.assertEqual(scraper.discover_article_urls(20),[url])
        self.assertEqual(scraper.listing_candidate_dates[url],date(2026,11,27))
        self.assertEqual(request_headers_for_url(url)['User-Agent'],BROWSER_USER_AGENT)

    def test_pagination_failure_is_not_reported_as_idle(self):
        url='https://recyclinginside.com/news/old/'
        page2=RECYCLING.url+'page/2/'
        html='<section id="latest">'+recycling_card(url)+'</section>'+f'<a class="next page-numbers" href="{page2}">Next</a>'
        scraper=RecyclingInsideScraper(Client({RECYCLING.url:html}),RECYCLING)
        self.assertEqual(scraper.scrape(target_date=date(2026,11,26)),[])
        self.assertEqual(scraper.last_failed_fetch_count,1)
        self.assertFalse(scraper.last_target_date_absent)
        self.assertIn('503',scraper.last_fetch_issues)

    def test_body_boundaries_keep_advertising_and_navigation_out(self):
        body='Measured recycling plant throughput and equipment performance. '*20
        for source,wrapper in [(PES,f'<section class="post-body"><article><h1>Wind story</h1><div><p>{body}</p></div></article></section>'),(RECYCLING,f'<div class="elementor-widget-theme-post-content"><p>{body}</p></div>')]:
            html='<meta property="og:title" content="Technical report">'+wrapper+'<aside>ADVERTISING_NOISE</aside><nav>DIRECTORY_NOISE</nav>'
            article=parse_article_html(html,source.url,source)
            self.assertIn('equipment performance',article['content'])
            self.assertNotIn('NOISE',article['content'])
            self.assertEqual(article['content_status'],'full')

if __name__=='__main__':unittest.main()
