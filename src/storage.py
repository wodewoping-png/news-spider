from __future__ import annotations

import csv
import json
from datetime import date
from pathlib import Path
from typing import Iterable
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .content_quality import content_rank
from .date_utils import DEFAULT_TIMEZONE, article_date


FIELDNAMES = (
    "title",
    "published_at",
    "content",
    "content_status",
    "content_issue",
    "content_extraction",
    "url",
    "source_name",
    "domain",
    "sub_domain",
    "crawled_at",
    "industry_primary_path",
    "industry_top_level",
    "industry_leaf",
    "industry_classifications",
    "industry_classification_status",
    "industry_classified_at",
    "industry_classifier_model",
    "industry_taxonomy_version",
)

INDUSTRY_FIELDNAMES = FIELDNAMES[-8:]

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


def load_existing_content_quality(jsonl_path: Path) -> dict[str, dict]:
    quality: dict[str, dict] = {}
    if not jsonl_path.exists():
        return quality
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
            current = quality.get(url_key)
            if current is None or is_better_article(item, current):
                quality[url_key] = item
    return quality


def is_better_article(candidate: dict, existing: dict) -> bool:
    candidate_status = content_rank(str(candidate.get("content_status") or ""))
    existing_status = content_rank(str(existing.get("content_status") or ""))
    candidate_length = len(str(candidate.get("content") or "").strip())
    existing_length = len(str(existing.get("content") or "").strip())
    if candidate_status == 3 and existing_status != 3:
        return True
    if existing_status == 3 and candidate_status != 3:
        return False
    if candidate_status == 0:
        return False
    if existing_status == 0:
        return True
    return candidate_length > existing_length


def _preserve_industry_classification(candidate: dict, existing: dict) -> dict:
    """Keep prior AI enrichment when a content refresh was not reclassified."""
    candidate_status = str(
        candidate.get("industry_classification_status") or ""
    ).lower()
    existing_status = str(
        existing.get("industry_classification_status") or ""
    ).lower()
    if candidate_status in {"classified", "unclassified"}:
        return candidate
    if candidate_status == "error" and existing_status not in {
        "classified",
        "unclassified",
    }:
        return candidate
    merged = dict(candidate)
    for key in INDUSTRY_FIELDNAMES:
        if key in existing:
            merged[key] = existing[key]
    return merged


def _csv_value(value: object) -> object:
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return value


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
        if current is None or is_better_article(normalized, current):
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
                    if is_better_article(candidate, existing):
                        output_lines.append(
                            json.dumps(
                                _preserve_industry_classification(candidate, existing),
                                ensure_ascii=False,
                            )
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
                writer.writerow(
                    {key: _csv_value(item.get(key, "")) for key in FIELDNAMES}
                )
