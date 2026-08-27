from __future__ import annotations

from html import unescape
import re


FULL_CONTENT_STATUS = "full"
INCOMPLETE_CONTENT_STATUS = "incomplete"
MISSING_CONTENT_STATUS = "missing"
UNKNOWN_CONTENT_STATUS = "unknown"

ACCESS_CHALLENGE_MARKER_GROUPS = (
    ("cf_app_waf", "requestinfo"),
    ("checking your browser", "enable javascript and cookies"),
    ("verify you are human", "cloudflare"),
)

PAYWALL_MARKERS = (
    "subscribe to unlock",
    "subscribe to continue",
    "subscribe to read",
    "sign in to continue",
    "log in to continue",
    "register to continue",
    "already a subscriber",
    "this article is for subscribers",
    "仅限会员",
    "会员专享",
    "登录后阅读全文",
    "订阅后阅读全文",
    "付费后阅读全文",
)
TRUNCATION_END_RE = re.compile(
    r"(?:\.{3}|…|read more|continue reading|阅读全文|查看全文|点击展开)\s*$",
    re.I,
)
RELATIVE_TIME_LINE_RE = re.compile(
    r"^(?:about\s+)?\d+\s+(?:minutes?|hours?|days?)\s+ago$",
    re.I,
)


def _looks_like_template_or_navigation_noise(text: str) -> bool:
    """Detect page chrome that is long enough to fool generic extractors."""
    decoded = unescape(text).replace("\xa0", " ")
    lowered = decoded.lower()
    loading_count = lowered.count("loading...") + lowered.count("loading…")
    if loading_count >= 2:
        return True

    lines = [line.strip() for line in decoded.splitlines() if line.strip()]
    relative_times = sum(bool(RELATIVE_TIME_LINE_RE.fullmatch(line)) for line in lines)
    event_markers = sum(
        lowered.count(marker)
        for marker in ("conference", "business breakfast", "upcoming events")
    )
    return len(lines) >= 6 and relative_times >= 2 and event_markers >= 2


def assess_content(
    content: str,
    *,
    extraction_method: str = "",
    declared_full: bool = False,
) -> tuple[str, str]:
    """Classify whether collected text appears to contain the full article."""
    text = str(content or "").strip()
    if not text:
        return MISSING_CONTENT_STATUS, "empty_content"

    lowered = text.lower()
    if any(
        all(marker in lowered for marker in group)
        for group in ACCESS_CHALLENGE_MARKER_GROUPS
    ):
        return MISSING_CONTENT_STATUS, "access_challenge"
    if any(marker in lowered for marker in PAYWALL_MARKERS):
        return INCOMPLETE_CONTENT_STATUS, "paywall_or_login_wall"
    if _looks_like_template_or_navigation_noise(text):
        return INCOMPLETE_CONTENT_STATUS, "template_or_navigation_noise"
    if TRUNCATION_END_RE.search(text):
        return INCOMPLETE_CONTENT_STATUS, "truncated_ending"
    if extraction_method == "rss_excerpt" and not declared_full:
        return INCOMPLETE_CONTENT_STATUS, "rss_excerpt_only"
    if extraction_method == "public_preview":
        return INCOMPLETE_CONTENT_STATUS, "public_preview_only"
    if extraction_method:
        return FULL_CONTENT_STATUS, ""
    return UNKNOWN_CONTENT_STATUS, "legacy_record_not_verified"


def content_rank(status: str) -> int:
    return {
        MISSING_CONTENT_STATUS: 0,
        UNKNOWN_CONTENT_STATUS: 1,
        INCOMPLETE_CONTENT_STATUS: 2,
        FULL_CONTENT_STATUS: 3,
    }.get(str(status or "").strip().lower(), 1)

