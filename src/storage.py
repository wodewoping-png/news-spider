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


def load_existing_content_lengths(jsonl_path: Path) -> dict[str, int]:
    lengths: dict[str, int] = {}
    if not jsonl_path.exists():
        return lengths
    with jsonl_path.open("r", encoding="utf-8") as file:
        for line in file:
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            url_key = canonicalize_url(str(item.get("url") or ""))
            if not url_key:
                continue
            content_length = len(str(item.get("content") or "").strip())
            lengths[url_key] = max(lengths.get(url_key, 0), content_length)
    return lengths


def append_jsonl(jsonl_path: Path, articles: Iterable[dict]) -> int:
    jsonl_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with jsonl_path.open("a", encoding="utf-8") as file:
        for article in articles:
            normalized = {key: article.get(key, "") for key in FIELDNAMES}
            file.write(json.dumps(normalized, ensure_ascii=False) + "\n")
            count += 1
    return count


def upsert_jsonl(jsonl_path: Path, articles: Iterable[dict]) -> tuple[int, int]:
    """Append new URLs and replace existing records only when content is longer."""
    incoming: dict[str, dict] = {}
    for article in articles:
        url_key = canonicalize_url(str(article.get("url") or ""))
        if not url_key:
            continue
        normalized = {key: article.get(key, "") for key in FIELDNAMES}
        current = incoming.get(url_key)
        if current is None or len(str(normalized["content"]).strip()) > len(
            str(current.get("content") or "").strip()
        ):
            incoming[url_key] = normalized
    if not incoming:
        return 0, 0

    jsonl_path.parent.mkdir(parents=True, exist_ok=True)
    output_lines: list[str] = []
    seen: set[str] = set()
    updated = 0
    if jsonl_path.exists():
        with jsonl_path.open("r", encoding="utf-8") as file:
            for line in file:
                if not line.strip():
                    continue
                try:
                    existing = json.loads(line)
                except json.JSONDecodeError:
                    output_lines.append(line.rstrip("\n"))
                    continue
                url_key = canonicalize_url(str(existing.get("url") or ""))
                candidate = incoming.get(url_key)
                if candidate is not None and url_key not in seen:
                    seen.add(url_key)
                    if len(str(candidate.get("content") or "").strip()) > len(
                        str(existing.get("content") or "").strip()
                    ):
                        output_lines.append(
                            json.dumps(candidate, ensure_ascii=False)
                        )
                        updated += 1
                        continue
                output_lines.append(line.rstrip("\n"))

    added = 0
    for url_key, article in incoming.items():
        if url_key in seen:
            continue
        output_lines.append(json.dumps(article, ensure_ascii=False))
        added += 1

    temporary_path = jsonl_path.with_suffix(jsonl_path.suffix + ".tmp")
    temporary_path.write_text(
        "\n".join(output_lines) + ("\n" if output_lines else ""),
        encoding="utf-8",
    )
    temporary_path.replace(jsonl_path)
    return added, updated


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
