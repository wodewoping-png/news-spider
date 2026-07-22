from __future__ import annotations

import argparse
import json
import logging
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from .article_parser import fetch_and_parse_article
from .audit import run_daily_audit
from .date_utils import (
    DEFAULT_TIMEZONE,
    ensure_published_at,
    is_article_on_date,
    normalize_published_at,
    parse_target_date,
)
from .http_client import DEFAULT_USER_AGENT, HttpClient
from .load_sources import default_sources_path, expects_daily_output, load_sources
from .rss_discovery import discover_feed, fetch_feed_entries
from .scrapers import get_scraper_class
from .storage import (
    append_jsonl,
    canonicalize_url,
    export_csv,
    load_existing_urls,
)


DEFAULT_CSV_TIMEZONE = DEFAULT_TIMEZONE
RSS_DISCOVERY_DISABLED_SOURCES = {
    "volta foundation",
    "科学网新闻",
    "新华网科技",
    "h2 view",
    "国际太阳能光伏网",
    "新能源网",
    "全球风电网",
    "中国新能源网-新闻",
}


def default_csv_path(
    now: datetime | None = None,
    *,
    target_date: date | None = None,
) -> Path:
    if target_date:
        run_date = (target_date + timedelta(days=1)).isoformat()
    else:
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
    parser.add_argument("--csv", type=Path)
    parser.add_argument("--logs", type=Path, default=Path("logs"))
    parser.add_argument("--limit-per-source", type=int, default=20)
    parser.add_argument(
        "--candidate-limit",
        type=int,
        default=100,
        help="Maximum listing/feed candidates inspected before the final per-source limit.",
    )
    parser.add_argument("--sleep", type=float, default=1.5)
    parser.add_argument("--timeout", type=int, default=20)
    parser.add_argument("--user-agent", default=DEFAULT_USER_AGENT)
    parser.add_argument("--ignore-robots", action="store_true")
    parser.add_argument(
        "--rollover-hour",
        type=int,
        default=6,
        help="Before this Asia/Shanghai hour, a delayed run belongs to the previous run day.",
    )
    parser.add_argument(
        "--min-content-chars",
        type=int,
        default=200,
        help="Content shorter than this is reported as degraded.",
    )
    parser.add_argument(
        "--target-date",
        help=(
            "Only keep articles published on this date (YYYY-MM-DD). "
            "Default: the previous nominal run date in Asia/Shanghai."
        ),
    )
    parser.add_argument(
        "--date-filter",
        choices=("today", "all"),
        default="today",
        help=(
            "'today' keeps only the target date; use 'all' to export all dates."
        ),
    )
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


def write_health_report(
    logs_dir: Path,
    target_date: date,
    records: list[dict],
) -> Path:
    report_path = logs_dir / "channel-health.json"
    payload = {
        "generated_at": datetime.now(ZoneInfo(DEFAULT_CSV_TIMEZONE)).isoformat(),
        "target_date": target_date.isoformat(),
        "sources": records,
    }
    report_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return report_path


def main() -> int:
    args = parse_args()
    setup_logging(args.logs)
    logging.info("Starting daily news spider")
    logging.info("Source file: %s", args.sources)
    target_date = parse_target_date(
        args.target_date,
        DEFAULT_CSV_TIMEZONE,
        rollover_hour=args.rollover_hour,
    )
    if args.csv is None:
        args.csv = default_csv_path(target_date=target_date)
    logging.info("Date filter: %s, target date=%s", args.date_filter, target_date)
    logging.info(
        "Per-source limits: final=%s, candidates=%s",
        args.limit_per_source,
        args.candidate_limit,
    )

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
    degraded_sources: list[tuple[str, str]] = []
    health_records: list[dict] = []
    candidate_limit = max(args.candidate_limit, args.limit_per_source)

    for source in sources:
        skip_reason = source.skip_reason
        if skip_reason:
            skipped_sources.append((source.name, skip_reason))
            logging.info("Skip source: %s (%s)", source.name, skip_reason)
            health_records.append(
                {
                    "source": source.name,
                    "frequency": source.frequency,
                    "status": "skipped",
                    "reason": skip_reason,
                    "new_articles": 0,
                }
            )
            continue

        logging.info("Processing source: %s <%s>", source.name, source.url)
        new_articles: list[dict] = []
        candidates_seen = 0
        pages_fetched = 0
        crawl_mode = "listing"
        try:
            source_key = source.name.strip().lower()
            feed_url = source.configured_rss_url
            if not feed_url and source_key not in RSS_DISCOVERY_DISABLED_SOURCES:
                feed_url = discover_feed(client, source.url)
            if feed_url:
                crawl_mode = "rss"
                if source.configured_rss_url:
                    logging.info("Using configured RSS for %s: %s", source.name, feed_url)
                entries = list(fetch_feed_entries(client, feed_url, candidate_limit))
                candidates_seen = len(entries)
                for entry in entries:
                    if len(new_articles) >= args.limit_per_source:
                        break
                    entry_key = canonicalize_url(entry.url)
                    if entry_key in existing_urls:
                        continue
                    if entry.published_at and args.date_filter == "today":
                        feed_article = {"published_at": entry.published_at, "url": entry.url}
                        if not is_article_on_date(feed_article, target_date, DEFAULT_CSV_TIMEZONE):
                            logging.info(
                                "Skip non-target-date RSS entry: %s (%s)",
                                entry.url,
                                entry.published_at,
                            )
                            continue
                    article = enrich_from_rss_entry(client, source, entry)
                    pages_fetched += 1
                    article_key = canonicalize_url(article.get("url", "")) if article else ""
                    if article and article_key and article_key not in existing_urls:
                        ensure_published_at(article)
                        if args.date_filter == "today" and not is_article_on_date(article, target_date, DEFAULT_CSV_TIMEZONE):
                            logging.info(
                                "Skip non-target-date article: %s (%s)",
                                article.get("url"),
                                article.get("published_at"),
                            )
                            continue
                        normalize_published_at(article, DEFAULT_CSV_TIMEZONE)
                        new_articles.append(article)
                        existing_urls.add(article_key)
            else:
                scraper_class = get_scraper_class(source.name)
                scraper = scraper_class(client, source)
                scrape_target = target_date if args.date_filter == "today" else None
                scraped_articles = scraper.scrape(
                    args.limit_per_source,
                    target_date=scrape_target,
                    candidate_limit=candidate_limit,
                )
                candidates_seen = getattr(scraper, "last_candidate_count", len(scraped_articles))
                pages_fetched = getattr(scraper, "last_fetched_count", len(scraped_articles))
                for article in scraped_articles:
                    url = article.get("url")
                    url_key = canonicalize_url(url or "")
                    if url and url_key not in existing_urls:
                        ensure_published_at(article)
                        if args.date_filter == "today" and not is_article_on_date(article, target_date, DEFAULT_CSV_TIMEZONE):
                            logging.info(
                                "Skip non-target-date article: %s (%s)",
                                url,
                                article.get("published_at"),
                            )
                            continue
                        normalize_published_at(article, DEFAULT_CSV_TIMEZONE)
                        new_articles.append(article)
                        existing_urls.add(url_key)
        except Exception as exc:  # Keep one bad source from stopping the daily run.
            logging.exception("Source failed: %s", source.name)
            failed_sources.append((source.name, str(exc)))
            health_records.append(
                {
                    "source": source.name,
                    "frequency": source.frequency,
                    "status": "failed",
                    "reason": str(exc),
                    "crawl_mode": crawl_mode,
                    "candidates_seen": candidates_seen,
                    "pages_fetched": pages_fetched,
                    "new_articles": 0,
                }
            )
            continue

        count = append_jsonl(args.output, new_articles)
        total_new += count
        usable_count = sum(
            len(str(article.get("content") or "").strip()) >= args.min_content_chars
            for article in new_articles
        )
        if count == 0 and not expects_daily_output(source.frequency):
            status = "idle"
            reason = "no target-date articles were expected from this low-frequency source"
        elif count == 0:
            status = "zero"
            reason = "no target-date articles were collected"
        elif usable_count < count:
            status = "degraded"
            reason = f"{count - usable_count} articles have short content"
        else:
            status = "healthy"
            reason = ""
        if status in {"zero", "degraded"}:
            degraded_sources.append((source.name, reason))
            logging.warning("Source degraded: %s (%s)", source.name, reason)
        health_records.append(
            {
                "source": source.name,
                "frequency": source.frequency,
                "status": status,
                "reason": reason,
                "crawl_mode": crawl_mode,
                "candidates_seen": candidates_seen,
                "pages_fetched": pages_fetched,
                "new_articles": count,
                "usable_articles": usable_count,
            }
        )
        logging.info(
            "Source complete: %s, new articles=%s, usable=%s, status=%s",
            source.name,
            count,
            usable_count,
            status,
        )

    export_target_date = target_date if args.date_filter == "today" else None
    export_csv(args.output, args.csv, export_target_date, DEFAULT_CSV_TIMEZONE)
    health_path = write_health_report(args.logs, target_date, health_records)
    audit_report = run_daily_audit(
        args.output,
        args.logs,
        target_date,
        health_records,
        min_content_chars=args.min_content_chars,
        timezone_name=DEFAULT_CSV_TIMEZONE,
    )
    logging.info("Run complete. New articles: %s", total_new)
    logging.info("Channel health report: %s", health_path)
    logging.info(
        "Daily audit: status=%s, anomalies=%s",
        audit_report["overall"]["anomaly_level"],
        len(audit_report["anomalies"]),
    )
    if audit_report["overall"]["anomaly_level"] != "normal":
        logging.warning(
            "Daily collection anomaly: %s",
            audit_report["overall"]["anomaly_reason"],
        )
    logging.info("Skipped sources: %s", skipped_sources)
    logging.info("Failed sources: %s", failed_sources)
    logging.info("Degraded sources: %s", degraded_sources)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
