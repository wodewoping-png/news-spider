from __future__ import annotations

import argparse
import json
import logging
import os
from datetime import date, datetime, timedelta
from pathlib import Path
from statistics import median
from zoneinfo import ZoneInfo

from .article_parser import fetch_and_parse_article, utc_now_iso
from .audit import run_daily_audit
from .content_quality import FULL_CONTENT_STATUS, assess_content
from .date_utils import (
    DEFAULT_TIMEZONE,
    article_date,
    ensure_published_at,
    is_article_on_date,
    normalize_published_at,
    parse_target_date,
)
from .http_client import DEFAULT_USER_AGENT, HttpClient
from .industry_classifier import (
    DEFAULT_BATCH_SIZE as DEFAULT_CLASSIFICATION_BATCH_SIZE,
    DEFAULT_MAX_CONTENT_CHARS as DEFAULT_CLASSIFICATION_CONTENT_CHARS,
    DEFAULT_MIN_CONFIDENCE as DEFAULT_CLASSIFICATION_CONFIDENCE,
    DEFAULT_MODEL as DEFAULT_CLASSIFICATION_MODEL,
    DEFAULT_TAXONOMY_PATH,
    ZAIIndustryClassifier,
    classify_jsonl,
)
from .load_sources import (
    default_sources_path,
    expects_daily_output,
    expects_output_on_date,
    load_sources,
)
from .rss_discovery import discover_feed, fetch_feed_entries
from .scrapers import get_scraper_class
from .storage import (
    canonicalize_url,
    export_csv,
    is_better_article,
    load_existing_content_quality,
    upsert_jsonl,
)


DEFAULT_CSV_TIMEZONE = DEFAULT_TIMEZONE
RSS_DISCOVERY_DISABLED_SOURCES = {
    "batteries news",
    "volta foundation",
    "perovskite-info",
    "pv magazine c&i pv",
    "科学网新闻",
    "新华网科技",
    "h2 view",
    "国际太阳能光伏网",
    "新能源网",
    "全球风电网",
    "中国新能源网-新闻",
    "光伏测试网",
    "索比光伏",
    "国际能源网",
    "中国能源网",
    "我爱电车网",
    "北极星储能网",
    "energytrend储能",
    "ne时代",
    "电池网",
    "x-mol",
}
THE_INFORMATION_SOURCE_KEY = "the information"
THE_INFORMATION_SUBSCRIBER_FEED = "https://www.theinformation.com/subscriber_feed"
THE_INFORMATION_USERNAME_ENV = "THE_INFORMATION_RSS_USERNAME"
THE_INFORMATION_PASSWORD_ENV = "THE_INFORMATION_RSS_PASSWORD"
DEFAULT_MIN_CONTENT_CHARS = 500


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
        default=DEFAULT_MIN_CONTENT_CHARS,
        help="Record the number of unusually short articles; completeness is assessed separately.",
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
    parser.add_argument(
        "--only-source",
        action="append",
        help="Only crawl the exact source name; may be repeated (used by recovery jobs).",
    )
    parser.add_argument(
        "--skip-audit",
        action="store_true",
        help="Skip daily statistics/audit update (used by isolated historical recovery jobs).",
    )
    parser.add_argument(
        "--skip-industry-classification",
        action="store_true",
        help="Do not call Z.AI even when ZAI_API_KEY is configured.",
    )
    parser.add_argument(
        "--industry-taxonomy",
        type=Path,
        default=DEFAULT_TAXONOMY_PATH,
        help="Semantic industry taxonomy JSON generated from 行业图景.xmind.",
    )
    parser.add_argument(
        "--industry-model",
        default=os.getenv("ZAI_MODEL", DEFAULT_CLASSIFICATION_MODEL),
        help="Z.AI model used for semantic news classification.",
    )
    parser.add_argument(
        "--industry-batch-size",
        type=int,
        default=DEFAULT_CLASSIFICATION_BATCH_SIZE,
    )
    parser.add_argument(
        "--industry-content-chars",
        type=int,
        default=DEFAULT_CLASSIFICATION_CONTENT_CHARS,
        help="Maximum article characters sent to Z.AI per article.",
    )
    parser.add_argument(
        "--industry-min-confidence",
        type=float,
        default=DEFAULT_CLASSIFICATION_CONFIDENCE,
    )
    return parser.parse_args()


def enrich_from_rss_entry(
    client: HttpClient,
    source,
    entry,
    *,
    feed_declared_full: bool = False,
) -> dict | None:
    article = fetch_and_parse_article(client, entry.url, source)
    feed_declared_full = bool(
        feed_declared_full or getattr(entry, "content_is_full", False)
    )
    feed_method = "rss_full_content" if feed_declared_full else "rss_excerpt"
    if not article:
        if not entry.summary:
            return None
        content_status, content_issue = assess_content(
            entry.summary,
            extraction_method=feed_method,
            declared_full=feed_declared_full,
        )
        article = {
            "title": entry.title,
            "published_at": entry.published_at,
            "content": entry.summary,
            "content_status": content_status,
            "content_issue": content_issue,
            "content_extraction": feed_method,
            "url": entry.url,
            "source_name": source.name,
            "domain": source.domain,
            "sub_domain": source.sub_domain,
            "crawled_at": utc_now_iso(),
        }
    if entry.title and not article.get("title"):
        article["title"] = entry.title
    if entry.published_at and not article.get("published_at"):
        article["published_at"] = entry.published_at
    public_excerpt = (entry.summary or "").strip()
    current_status, _ = assess_content(
        str(article.get("content") or ""),
        extraction_method=str(article.get("content_extraction") or "page_full_text"),
    )
    if public_excerpt and (
        feed_declared_full
        or current_status != FULL_CONTENT_STATUS
    ) and len(public_excerpt) > len(str(article.get("content") or "").strip()):
        article["content"] = public_excerpt
        article["content_extraction"] = feed_method
    article["content_status"], article["content_issue"] = assess_content(
        str(article.get("content") or ""),
        extraction_method=str(article.get("content_extraction") or "page_full_text"),
        declared_full=(
            feed_declared_full
            and article.get("content_extraction") == feed_method
        ),
    )
    article["url"] = article.get("url") or entry.url
    return article


def ensure_content_quality(
    article: dict,
    *,
    default_extraction: str = "scraper_full_text",
) -> None:
    extraction_method = str(
        article.get("content_extraction") or default_extraction
    )
    article["content_extraction"] = extraction_method
    article["content_status"], article["content_issue"] = assess_content(
        str(article.get("content") or ""),
        extraction_method=extraction_method,
    )


def resolve_feed_access(
    source_name: str,
    configured_feed_url: str | None,
    *,
    environ: dict[str, str] | None = None,
) -> tuple[str | None, tuple[str, str] | None, bool, str]:
    """Resolve source-specific feed authentication without exposing credentials."""
    if source_name.strip().lower() != THE_INFORMATION_SOURCE_KEY:
        return configured_feed_url, None, False, "rss"

    environment = environ if environ is not None else os.environ
    username = str(environment.get(THE_INFORMATION_USERNAME_ENV) or "").strip()
    password = str(environment.get(THE_INFORMATION_PASSWORD_ENV) or "")
    if bool(username) != bool(password):
        raise ValueError(
            f"{THE_INFORMATION_USERNAME_ENV} and "
            f"{THE_INFORMATION_PASSWORD_ENV} must both be configured"
        )
    if username and password:
        return (
            THE_INFORMATION_SUBSCRIBER_FEED,
            (username, password),
            True,
            "rss_authenticated",
        )
    return configured_feed_url, None, False, "rss_public"


def has_confirmed_non_target_candidates(
    candidates_seen: int,
    date_filtered_candidates: int,
    undated_candidates: int,
) -> bool:
    """Return true only when every observed candidate is dated outside the target day."""
    return (
        candidates_seen > 0
        and date_filtered_candidates >= candidates_seen
        and undated_candidates == 0
    )


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


def append_source_error(
    logs_dir: Path,
    target_date: date,
    source,
    exc: BaseException,
) -> dict:
    """Persist one source-level failure for later repair without stopping the run."""
    occurred_at = datetime.now(ZoneInfo(DEFAULT_CSV_TIMEZONE)).isoformat()
    record = {
        "occurred_at": occurred_at,
        "target_date": target_date.isoformat(),
        "source": source.name,
        "url": source.url,
        "error_type": type(exc).__name__,
        "error": str(exc),
    }
    error_path = logs_dir / "source-errors.jsonl"
    error_path.parent.mkdir(parents=True, exist_ok=True)
    with error_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record


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
    if args.only_source:
        requested_sources = set(args.only_source)
        sources = [source for source in sources if source.name in requested_sources]
        found_sources = {source.name for source in sources}
        missing_sources = sorted(requested_sources - found_sources)
        if missing_sources:
            logging.error("Requested sources not found: %s", missing_sources)
            return 2
    existing_quality = load_existing_content_quality(args.output)
    existing_urls = set(existing_quality)
    client = HttpClient(
        user_agent=args.user_agent,
        timeout=args.timeout,
        sleep_seconds=args.sleep,
        respect_robots=not args.ignore_robots,
    )
    skip_industry_classification = getattr(
        args, "skip_industry_classification", False
    )
    industry_classifier = None
    if not skip_industry_classification:
        industry_classifier = ZAIIndustryClassifier.from_environment(
            taxonomy_path=getattr(
                args, "industry_taxonomy", DEFAULT_TAXONOMY_PATH
            ),
            model=getattr(
                args, "industry_model", DEFAULT_CLASSIFICATION_MODEL
            ),
            batch_size=getattr(
                args, "industry_batch_size", DEFAULT_CLASSIFICATION_BATCH_SIZE
            ),
            max_content_chars=getattr(
                args,
                "industry_content_chars",
                DEFAULT_CLASSIFICATION_CONTENT_CHARS,
            ),
            min_confidence=getattr(
                args,
                "industry_min_confidence",
                DEFAULT_CLASSIFICATION_CONFIDENCE,
            ),
        )
    if industry_classifier:
        logging.info(
            "Industry classification enabled: model=%s, taxonomy=%s",
            industry_classifier.model,
            industry_classifier.taxonomy.version,
        )
    else:
        logging.info(
            "Industry classification disabled: %s",
            "command-line option" if skip_industry_classification else "ZAI_API_KEY is not configured",
        )

    total_new = 0
    total_refreshed = 0
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
        date_filtered_candidates = 0
        undated_candidates = 0
        candidate_date_min = ""
        candidate_date_max = ""
        observed_candidate_dates: list[date] = []
        target_date_absent = False
        crawl_mode = "listing"
        try:
            source_key = source.name.strip().lower()
            scraper_class = get_scraper_class(source.name)
            scraper_handles_feed = bool(
                getattr(scraper_class, "handles_configured_feed", False)
            )
            feed_url = None if scraper_handles_feed else source.configured_rss_url
            feed_auth = None
            feed_required = False
            feed_crawl_mode = "rss"
            if not scraper_handles_feed:
                feed_url, feed_auth, feed_required, feed_crawl_mode = resolve_feed_access(
                    source.name,
                    feed_url,
                )
            if (
                not scraper_handles_feed
                and not feed_url
                and source_key not in RSS_DISCOVERY_DISABLED_SOURCES
            ):
                feed_url = discover_feed(client, source.url)
            entries = []
            if feed_url:
                if feed_auth:
                    logging.info(
                        "Using authenticated subscriber RSS for %s",
                        source.name,
                    )
                elif source.configured_rss_url:
                    logging.info("Using configured RSS for %s: %s", source.name, feed_url)
                entries = list(
                    fetch_feed_entries(
                        client,
                        feed_url,
                        candidate_limit,
                        auth=feed_auth,
                        required=feed_required,
                    )
                )
                if feed_required and not entries:
                    raise RuntimeError(
                        "Authenticated subscriber RSS returned no entries"
                    )
                accepts_rss_entry = getattr(scraper_class, "accepts_rss_entry", None)
                if callable(accepts_rss_entry):
                    entries = [
                        entry for entry in entries if accepts_rss_entry(entry)
                    ]
            if entries:
                crawl_mode = feed_crawl_mode
                candidates_seen = len(entries)
                for entry in entries:
                    if len(new_articles) >= args.limit_per_source:
                        break
                    entry_key = canonicalize_url(entry.url)
                    if (
                        entry_key in existing_urls
                        and str(
                            existing_quality.get(entry_key, {}).get(
                                "content_status"
                            )
                            or ""
                        ).lower()
                        == FULL_CONTENT_STATUS
                    ):
                        continue
                    if entry.published_at and args.date_filter == "today":
                        feed_article = {"published_at": entry.published_at, "url": entry.url}
                        feed_date = article_date(feed_article, DEFAULT_CSV_TIMEZONE)
                        if feed_date:
                            observed_candidate_dates.append(feed_date)
                        if feed_date != target_date:
                            date_filtered_candidates += 1
                            logging.info(
                                "Skip non-target-date RSS entry: %s (%s)",
                                entry.url,
                                entry.published_at,
                            )
                            continue
                    article = enrich_from_rss_entry(
                        client,
                        source,
                        entry,
                        feed_declared_full=(
                            feed_crawl_mode == "rss_authenticated"
                        ),
                    )
                    pages_fetched += 1
                    if article and args.date_filter == "today" and not entry.published_at:
                        parsed_candidate_date = article_date(
                            article,
                            DEFAULT_CSV_TIMEZONE,
                        )
                        if parsed_candidate_date:
                            observed_candidate_dates.append(parsed_candidate_date)
                            if parsed_candidate_date != target_date:
                                date_filtered_candidates += 1
                        else:
                            undated_candidates += 1
                    elif not article and args.date_filter == "today" and not entry.published_at:
                        undated_candidates += 1
                    article_key = canonicalize_url(article.get("url", "")) if article else ""
                    if article and article_key:
                        previous_article = existing_quality.get(article_key)
                        if previous_article is not None and not is_better_article(
                            article,
                            previous_article,
                        ):
                            continue
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
                        existing_quality[article_key] = article
                if observed_candidate_dates:
                    candidate_date_min = min(observed_candidate_dates).isoformat()
                    candidate_date_max = max(observed_candidate_dates).isoformat()
            else:
                if feed_url:
                    logging.warning(
                        "RSS unavailable or empty for %s; falling back to listing scraper",
                        source.name,
                    )
                scraper = scraper_class(client, source)
                scrape_target = target_date if args.date_filter == "today" else None
                scraped_articles = scraper.scrape(
                    args.limit_per_source,
                    target_date=scrape_target,
                    candidate_limit=candidate_limit,
                )
                candidates_seen = getattr(scraper, "last_candidate_count", len(scraped_articles))
                pages_fetched = getattr(scraper, "last_fetched_count", len(scraped_articles))
                date_filtered_candidates = getattr(
                    scraper,
                    "last_date_filtered_count",
                    0,
                )
                undated_candidates = getattr(
                    scraper,
                    "last_undated_candidate_count",
                    0,
                )
                candidate_date_min = getattr(
                    scraper,
                    "last_candidate_date_min",
                    "",
                )
                candidate_date_max = getattr(
                    scraper,
                    "last_candidate_date_max",
                    "",
                )
                target_date_absent = bool(
                    getattr(scraper, "last_target_date_absent", False)
                )
                for article in scraped_articles:
                    ensure_content_quality(article)
                    url = article.get("url")
                    url_key = canonicalize_url(url or "")
                    if url and url_key:
                        previous_article = existing_quality.get(url_key)
                        if previous_article is not None and not is_better_article(
                            article,
                            previous_article,
                        ):
                            continue
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
                        existing_quality[url_key] = article
        except Exception as exc:  # Keep one bad source from stopping the daily run.
            logging.exception("Source failed: %s", source.name)
            failure = append_source_error(args.logs, target_date, source, exc)
            failed_sources.append((source.name, failure["error"]))
            health_records.append(
                {
                    "source": source.name,
                    "url": source.url,
                    "frequency": source.frequency,
                    "status": "failed",
                    "reason": failure["error"],
                    "failed_at": failure["occurred_at"],
                    "error_type": failure["error_type"],
                    "crawl_mode": crawl_mode,
                    "candidates_seen": candidates_seen,
                    "pages_fetched": pages_fetched,
                    "new_articles": 0,
                }
            )
            continue

        added_count, refreshed_count = upsert_jsonl(args.output, new_articles)
        changed_count = added_count + refreshed_count
        total_new += added_count
        total_refreshed += refreshed_count
        content_lengths = [
            len(str(article.get("content") or "").strip())
            for article in new_articles
        ]
        usable_count = sum(
            str(article.get("content_status") or "").lower()
            == FULL_CONTENT_STATUS
            for article in new_articles
        )
        incomplete_count = max(changed_count - usable_count, 0)
        short_count = sum(
            length < args.min_content_chars for length in content_lengths
        )
        confirmed_no_news = has_confirmed_non_target_candidates(
            candidates_seen,
            date_filtered_candidates,
            undated_candidates,
        ) or target_date_absent
        if changed_count == 0 and confirmed_no_news:
            status = "idle"
            date_range = candidate_date_max
            if candidate_date_min and candidate_date_min != candidate_date_max:
                date_range = f"{candidate_date_min} to {candidate_date_max}"
            reason = (
                "all observed candidates were published outside the target date"
                + (f" ({date_range})" if date_range else "")
            )
        elif changed_count == 0 and not expects_output_on_date(source.frequency, target_date):
            status = "idle"
            reason = "no target-date articles were expected for this source schedule"
        elif changed_count == 0:
            status = "zero"
            reason = "no target-date articles were collected"
        elif incomplete_count:
            status = "degraded"
            reason = (
                f"{incomplete_count} articles were not verified as full text"
            )
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
                "date_filtered_candidates": date_filtered_candidates,
                "undated_candidates": undated_candidates,
                "candidate_date_min": candidate_date_min,
                "candidate_date_max": candidate_date_max,
                "new_articles": added_count,
                "refreshed_articles": refreshed_count,
                "usable_articles": usable_count,
                "incomplete_articles": incomplete_count,
                "short_articles": short_count,
                "min_content_chars": args.min_content_chars,
                "content_chars_min": min(content_lengths, default=0),
                "content_chars_median": (
                    int(median(content_lengths)) if content_lengths else 0
                ),
                "content_chars_max": max(content_lengths, default=0),
            }
        )
        logging.info(
            "Source complete: %s, new articles=%s, refreshed=%s, usable=%s, status=%s",
            source.name,
            added_count,
            refreshed_count,
            usable_count,
            status,
        )

    if industry_classifier:
        classification_result = classify_jsonl(
            industry_classifier,
            args.output,
            target_date=target_date,
            timezone_name=DEFAULT_CSV_TIMEZONE,
        )
        logging.info(
            "Industry classification pass complete: selected=%s total=%s malformed=%s",
            classification_result["classified"],
            classification_result["records"],
            classification_result["malformed"],
        )

    export_target_date = target_date if args.date_filter == "today" else None
    export_csv(args.output, args.csv, export_target_date, DEFAULT_CSV_TIMEZONE)
    health_path = write_health_report(args.logs, target_date, health_records)
    audit_report = None
    if not args.skip_audit:
        audit_report = run_daily_audit(
            args.output,
            args.logs,
            target_date,
            health_records,
            min_content_chars=args.min_content_chars,
            timezone_name=DEFAULT_CSV_TIMEZONE,
        )
    logging.info("Run complete. New articles: %s", total_new)
    logging.info("Run complete. Refreshed short articles: %s", total_refreshed)
    logging.info("Channel health report: %s", health_path)
    if audit_report:
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
