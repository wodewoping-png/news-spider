from __future__ import annotations

import argparse
import logging
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from .article_parser import fetch_and_parse_article
from .http_client import DEFAULT_USER_AGENT, HttpClient
from .load_sources import default_sources_path, load_sources
from .rss_discovery import discover_feed, fetch_feed_entries
from .scrapers import get_scraper_class
from .storage import append_jsonl, export_csv, load_existing_urls


DEFAULT_CSV_TIMEZONE = "Asia/Shanghai"


def default_csv_path(now: datetime | None = None) -> Path:
    run_date = (now or datetime.now(ZoneInfo(DEFAULT_CSV_TIMEZONE))).strftime("%Y-%m-%d")
    return Path("data") / f"articles-{run_date}.csv"


def setup_logging(log_dir: Path) -> Path:
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "daily-news.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )
    return log_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Daily web-news crawler")
    parser.add_argument("--sources", type=Path, default=default_sources_path())
    parser.add_argument("--output", type=Path, default=Path("data/articles.jsonl"))
    parser.add_argument("--csv", type=Path, default=default_csv_path())
    parser.add_argument("--logs", type=Path, default=Path("logs"))
    parser.add_argument("--limit-per-source", type=int, default=20)
    parser.add_argument("--sleep", type=float, default=1.5)
    parser.add_argument("--timeout", type=int, default=20)
    parser.add_argument("--user-agent", default=DEFAULT_USER_AGENT)
    parser.add_argument("--ignore-robots", action="store_true")
    return parser.parse_args()


def enrich_from_rss_entry(client: HttpClient, source, entry) -> dict | None:
    article = fetch_and_parse_article(client, entry.url, source)
    if not article:
        return None
    if entry.title and not article.get("title"):
        article["title"] = entry.title
    if entry.published_at and not article.get("published_at"):
        article["published_at"] = entry.published_at
    article["url"] = article.get("url") or entry.url
    return article


def main() -> int:
    args = parse_args()
    setup_logging(args.logs)
    logging.info("Starting daily news spider")
    logging.info("Source file: %s", args.sources)

    sources = load_sources(args.sources)
    existing_urls = load_existing_urls(args.output)
    client = HttpClient(
        user_agent=args.user_agent,
        timeout=args.timeout,
        sleep_seconds=args.sleep,
        respect_robots=not args.ignore_robots,
    )

    total_new = 0
    skipped_sources: list[tuple[str, str]] = []
    failed_sources: list[tuple[str, str]] = []

    for source in sources:
        skip_reason = source.skip_reason
        if skip_reason:
            skipped_sources.append((source.name, skip_reason))
            logging.info("Skip source: %s (%s)", source.name, skip_reason)
            continue

        logging.info("Processing source: %s <%s>", source.name, source.url)
        new_articles: list[dict] = []
        try:
            feed_url = source.configured_rss_url or discover_feed(client, source.url)
            if feed_url:
                if source.configured_rss_url:
                    logging.info("Using configured RSS for %s: %s", source.name, feed_url)
                for entry in fetch_feed_entries(client, feed_url, args.limit_per_source):
                    if entry.url in existing_urls:
                        continue
                    article = enrich_from_rss_entry(client, source, entry)
                    if article and article.get("url") not in existing_urls:
                        new_articles.append(article)
                        existing_urls.add(article["url"])
            else:
                scraper_class = get_scraper_class(source.name)
                scraper = scraper_class(client, source)
                for article in scraper.scrape(args.limit_per_source):
                    url = article.get("url")
                    if url and url not in existing_urls:
                        new_articles.append(article)
                        existing_urls.add(url)
        except Exception as exc:  # Keep one bad source from stopping the daily run.
            logging.exception("Source failed: %s", source.name)
            failed_sources.append((source.name, str(exc)))
            continue

        count = append_jsonl(args.output, new_articles)
        total_new += count
        logging.info("Source complete: %s, new articles=%s", source.name, count)

    export_csv(args.output, args.csv)
    logging.info("Run complete. New articles: %s", total_new)
    logging.info("Skipped sources: %s", skipped_sources)
    logging.info("Failed sources: %s", failed_sources)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
