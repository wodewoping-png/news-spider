from __future__ import annotations

import csv
import json
from datetime import date
from pathlib import Path
from typing import Iterable
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .date_utils import DEFAULT_TIMEZONE, article_date


FIELDNAMES = (
    "title",
    "published_at",
    "content",
    "url",
    "source_name",
    "domain",
    "sub_domain",
    "crawled_at",
)

TRACKING_QUERY_KEYS = {"fbclid", "gclid", "mc_cid", "mc_eid"}


def canonicalize_url(url: str) -> str:
    """Build a stable comparison key without changing the stored URL."""
    value = (url or "").strip()
    if not value:
        return ""
    parsed = urlsplit(value)
    if not parsed.netloc:
        return value.rstrip("/")
    hostname = (parsed.hostname or "").lower()
    if hostname.startswith("www."):
        hostname = hostname[4:]
    port = parsed.port
    if port and not (
        (parsed.scheme == "http" and port == 80)
        or (parsed.scheme == "https" and port == 443)
    ):
        hostname = f"{hostname}:{port}"
    query = urlencode(
        sorted(
            (key, val)
            for key, val in parse_qsl(parsed.query, keep_blank_values=True)
            if not key.lower().startswith("utm_")
            and key.lower() not in TRACKING_QUERY_KEYS
        )
    )
    path = parsed.path.rstrip("/") or "/"
    scheme = "https" if parsed.scheme.lower() in {"http", "https"} else parsed.scheme.lower()
    return urlunsplit((scheme, hostname, path, query, ""))


def load_existing_urls(jsonl_path: Path) -> set[str]:
    urls: set[str] = set()
    if not jsonl_path.exists():
        return urls
    with jsonl_path.open("r", encoding="utf-8") as file:
        for line in file:
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if item.get("url"):
                urls.add(canonicalize_url(item["url"]))
    return urls


def append_jsonl(jsonl_path: Path, articles: Iterable[dict]) -> int:
    jsonl_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with jsonl_path.open("a", encoding="utf-8") as file:
        for article in articles:
            normalized = {key: article.get(key, "") for key in FIELDNAMES}
            file.write(json.dumps(normalized, ensure_ascii=False) + "\n")
            count += 1
    return count


def export_csv(
    jsonl_path: Path,
    csv_path: Path,
    target_date: date | None = None,
    timezone_name: str = DEFAULT_TIMEZONE,
) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", encoding="utf-8-sig", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=FIELDNAMES)
        writer.writeheader()
        if not jsonl_path.exists():
            return
        with jsonl_path.open("r", encoding="utf-8") as jsonl_file:
            for line in jsonl_file:
                if not line.strip():
                    continue
                try:
                    item = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if target_date and article_date(item, timezone_name) != target_date:
                    continue
                writer.writerow({key: item.get(key, "") for key in FIELDNAMES})
