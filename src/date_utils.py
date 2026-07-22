from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone
from typing import Optional
from zoneinfo import ZoneInfo

from dateutil import parser as date_parser


DEFAULT_TIMEZONE = "Asia/Shanghai"
COMMON_TZINFOS = {
    "EST": -5 * 3600,
    "EDT": -4 * 3600,
    "MST": -7 * 3600,
    "MDT": -6 * 3600,
    "PST": -8 * 3600,
    "PDT": -7 * 3600,
}

URL_DATE_PATTERNS = (
    re.compile(r"t(?P<year>20\d{2})(?P<month>\d{2})(?P<day>\d{2})_"),
    re.compile(r"/(?P<year>20\d{2})(?P<month>\d{2})(?P<day>\d{2})/"),
    re.compile(r"/(?P<year>20\d{2})(?P<month>\d{2})/(?P<day>\d{2})/"),
    re.compile(r"/(?P<year>20\d{2})(?P<month>\d{2})/(?P<day>\d{1,2})[^/]*\.html"),
    re.compile(r"(?P<year>20\d{2})[-_/](?P<month>\d{1,2})[-_/](?P<day>\d{1,2})"),
)


def local_today(timezone_name: str = DEFAULT_TIMEZONE) -> date:
    return datetime.now(ZoneInfo(timezone_name)).date()


def local_yesterday(timezone_name: str = DEFAULT_TIMEZONE) -> date:
    return local_today(timezone_name) - timedelta(days=1)


def default_target_date(
    timezone_name: str = DEFAULT_TIMEZONE,
    *,
    now: datetime | None = None,
    rollover_hour: int = 6,
) -> date:
    """Return the publication date for the nominal nightly crawl."""
    if not 0 <= rollover_hour <= 23:
        raise ValueError("rollover_hour must be between 0 and 23")
    local_now = now or datetime.now(ZoneInfo(timezone_name))
    if local_now.tzinfo is None:
        local_now = local_now.replace(tzinfo=ZoneInfo(timezone_name))
    else:
        local_now = local_now.astimezone(ZoneInfo(timezone_name))
    nominal_run_date = local_now.date()
    if local_now.hour < rollover_hour:
        nominal_run_date -= timedelta(days=1)
    return nominal_run_date - timedelta(days=1)


def parse_target_date(
    value: str | None,
    timezone_name: str = DEFAULT_TIMEZONE,
    *,
    now: datetime | None = None,
    rollover_hour: int = 6,
) -> date:
    if not value:
        return default_target_date(
            timezone_name,
            now=now,
            rollover_hour=rollover_hour,
        )
    return datetime.strptime(value, "%Y-%m-%d").date()


def date_from_url(url: str) -> Optional[date]:
    for pattern in URL_DATE_PATTERNS:
        match = pattern.search(url)
        if not match:
            continue
        try:
            return date(
                int(match.group("year")),
                int(match.group("month")),
                int(match.group("day")),
            )
        except ValueError:
            return None
    return None


def normalize_chinese_date(text: str) -> str:
    return (
        text.replace("年", "-")
        .replace("月", "-")
        .replace("日", " ")
        .replace("时", ":")
        .replace("分", ":")
        .replace("秒", " ")
    )


def parse_published_datetime(value: str, timezone_name: str = DEFAULT_TIMEZONE) -> Optional[datetime]:
    value = (value or "").strip()
    if not value:
        return None
    try:
        parsed = date_parser.parse(
            normalize_chinese_date(value),
            fuzzy=True,
            tzinfos=COMMON_TZINFOS,
        )
    except (ValueError, OverflowError, TypeError):
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=ZoneInfo(timezone_name))
    return parsed.astimezone(ZoneInfo(timezone_name))


def article_date(article: dict, timezone_name: str = DEFAULT_TIMEZONE) -> Optional[date]:
    parsed = parse_published_datetime(str(article.get("published_at") or ""), timezone_name)
    if parsed:
        return parsed.date()
    return date_from_url(str(article.get("url") or ""))


def ensure_published_at(article: dict) -> dict:
    if article.get("published_at"):
        return article
    url_date = date_from_url(str(article.get("url") or ""))
    if url_date:
        article["published_at"] = url_date.isoformat()
    return article


def normalize_published_at(article: dict, timezone_name: str = DEFAULT_TIMEZONE) -> dict:
    parsed = parse_published_datetime(str(article.get("published_at") or ""), timezone_name)
    if parsed:
        article["published_at"] = parsed.date().isoformat()
        return article
    url_date = date_from_url(str(article.get("url") or ""))
    if url_date:
        article["published_at"] = url_date.isoformat()
    return article


def is_article_on_date(article: dict, target_date: date, timezone_name: str = DEFAULT_TIMEZONE) -> bool:
    return article_date(article, timezone_name) == target_date
