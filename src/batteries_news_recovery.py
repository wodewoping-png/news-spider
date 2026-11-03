"""Recover Batteries News posts that appeared after their publication-day crawl.

The publisher sometimes adds dated cards to Latest days after publication.
The normal daily run correctly filters to one date, so revisit only dates with
visible, unarchived cards; do not invent news on dates when the site is idle.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

from .date_utils import parse_target_date
from .http_client import HttpClient
from .load_sources import load_sources
from .scrapers.batteries_news import BatteriesNewsCard, BatteriesNewsScraper
from .storage import canonicalize_url, load_existing_content_quality


def missing_dates(
    cards: list[BatteriesNewsCard], existing_urls: set[str], target_date: date,
    *, lookback_days: int = 31,
) -> list[date]:
    first = target_date - timedelta(days=lookback_days)
    return sorted({card.published_date for card in cards
                   if card.published_date and first <= card.published_date <= target_date
                   and canonicalize_url(card.url) not in existing_urls})


def main() -> int:
    parser = argparse.ArgumentParser(description="Recover late-listed Batteries News posts")
    parser.add_argument("--target-date", default="")
    parser.add_argument("--sources", type=Path, default=Path("sources.xlsx"))
    parser.add_argument("--output", type=Path, default=Path("data/articles.jsonl"))
    parser.add_argument("--logs", type=Path, default=Path("logs/batteries-recovery"))
    parser.add_argument("--lookback-days", type=int, default=31)
    args = parser.parse_args()
    if not 1 <= args.lookback_days <= 31:
        parser.error("lookback-days must be between 1 and 31")
    target_date = parse_target_date(args.target_date)
    sources = [source for source in load_sources(args.sources) if source.name == "Batteries News"]
    if len(sources) != 1:
        raise SystemExit("Batteries News source missing or duplicated")
    client = HttpClient(timeout=20, sleep_seconds=1.5)
    response = client.get(sources[0].url)
    if not response:
        print(f"Batteries News listing unavailable: {client.last_failure_reason}")
        return 1
    cards, _ = BatteriesNewsScraper.parse_listing(response.text, response.url)
    if not cards:
        print("Batteries News Latest module has no dated cards")
        return 1
    newest = max((card.published_date for card in cards if card.published_date), default=None)
    if newest and (target_date - newest).days >= 7:
        print(f"::warning title=Batteries News publication gap::Latest visible post is {newest}; "
              f"target publication date is {target_date}", flush=True)
    existing_urls = set(load_existing_content_quality(args.output))
    dates = missing_dates(cards, existing_urls, target_date, lookback_days=args.lookback_days)
    print(f"Batteries News Latest: {len(cards)} cards; missing publication dates: {dates}", flush=True)
    for publication_date in dates:
        command = [sys.executable, "-m", "src.main", "--sources", str(args.sources),
                   "--only-source", "Batteries News", "--target-date", publication_date.isoformat(),
                   "--output", str(args.output), "--logs", str(args.logs), "--skip-audit"]
        subprocess.run(command, check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
