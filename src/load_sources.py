from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

import pandas as pd


SOURCE_COLUMNS = {
    "name": "网站/来源",
    "media_type": "媒体类型",
    "domain": "主干领域",
    "sub_domain": "细分领域",
    "frequency": "更新频率",
    "description": "内容简介",
    "note": "备注",
    "url": "链接",
}

SKIP_NOTE_KEYWORDS = (
    "公众号",
    "无法访问",
    "需邮箱订阅",
    "邮箱订阅",
    "不适合",
)


@dataclass(frozen=True)
class Source:
    name: str
    media_type: str
    domain: str
    sub_domain: str
    frequency: str
    description: str
    note: str
    url: str

    @property
    def skip_reason(self) -> Optional[str]:
        note = self.note.strip()
        for keyword in SKIP_NOTE_KEYWORDS:
            if keyword in note:
                return f"备注包含“{keyword}”"
        if not self.url:
            return "链接为空"
        return None

    @property
    def configured_rss_url(self) -> str:
        match = re.search(r"(?:RSS|rss)\s*[:：]\s*(https?://\S+)", self.note)
        if not match:
            return ""
        return match.group(1).rstrip("。；;，,")


def default_sources_path() -> Path:
    for candidate in (Path("sources.xlsx"), Path("news web.xlsx")):
        if candidate.exists():
            return candidate
    return Path("sources.xlsx")


def _clean(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def load_sources(path: Path) -> list[Source]:
    df = pd.read_excel(path, engine="openpyxl")
    missing = [column for column in SOURCE_COLUMNS.values() if column not in df.columns]
    if missing:
        raise ValueError(f"sources file is missing columns: {', '.join(missing)}")

    sources: list[Source] = []
    for _, row in df.iterrows():
        source = Source(
            name=_clean(row[SOURCE_COLUMNS["name"]]),
            media_type=_clean(row[SOURCE_COLUMNS["media_type"]]),
            domain=_clean(row[SOURCE_COLUMNS["domain"]]),
            sub_domain=_clean(row[SOURCE_COLUMNS["sub_domain"]]),
            frequency=_clean(row[SOURCE_COLUMNS["frequency"]]),
            description=_clean(row[SOURCE_COLUMNS["description"]]),
            note=_clean(row[SOURCE_COLUMNS["note"]]),
            url=_clean(row[SOURCE_COLUMNS["url"]]),
        )
        if source.name or source.url:
            sources.append(source)
    return sources


def iter_active_sources(sources: Iterable[Source]) -> Iterable[Source]:
    for source in sources:
        if source.skip_reason is None:
            yield source


def expects_daily_output(frequency: str) -> bool:
    normalized = (frequency or "").strip().lower()
    low_frequency_markers = (
        "\u5468",
        "\u6708",
        "\u5b63\u5ea6",
        "\u4f4e\u9891",
        "weekly",
        "monthly",
        "quarterly",
    )
    return not any(marker in normalized for marker in low_frequency_markers)
