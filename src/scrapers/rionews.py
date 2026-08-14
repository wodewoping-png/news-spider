from __future__ import annotations

import logging
import os
from datetime import date
from pathlib import Path

from ..rionews import load_rionews_articles
from .base import BaseScraper
from .china_energy import ChinaEnergyScraper
from .international_energy import InternationalEnergyScraper
from .itdcw import ITDCWScraper
from .xevcar import XEVCarScraper


class RIONewsSourceScraper(BaseScraper):
    """Import one configured source from the curated RIOnews daily workbook."""

    media_prefix = ""
    fallback_scraper_class: type[BaseScraper] | None = None

    def _daily_dir(self) -> Path:
        return Path(os.getenv("RIONEWS_DAILY_DIR", "data/rionews/daily"))

    def _workbook_path(self, target_date: date | None) -> Path | None:
        daily_dir = self._daily_dir()
        if target_date:
            return daily_dir / f"news_export_{target_date.isoformat()}.xlsx"
        candidates = sorted(daily_dir.glob("news_export_*.xlsx"))
        return candidates[-1] if candidates else None

    def scrape(
        self,
        limit: int = 20,
        *,
        target_date: date | None = None,
        candidate_limit: int | None = None,
    ) -> list[dict]:
        workbook_path = self._workbook_path(target_date)
        if workbook_path is None or not workbook_path.exists():
            if self.fallback_scraper_class is None:
                raise RuntimeError(
                    "RIOnews input workbook is unavailable for "
                    f"{target_date or 'latest'}: {workbook_path or self._daily_dir()}"
                )
            logging.warning(
                "RIOnews input workbook is unavailable for %s; "
                "falling back to the public %s scraper",
                target_date or "latest",
                self.source.name,
            )
            fallback = self.fallback_scraper_class(self.client, self.source)
            articles = fallback.scrape(
                limit,
                target_date=target_date,
                candidate_limit=candidate_limit,
            )
            self.last_candidate_count = getattr(
                fallback,
                "last_candidate_count",
                len(articles),
            )
            self.last_fetched_count = getattr(
                fallback,
                "last_fetched_count",
                len(articles),
            )
            return articles

        articles = load_rionews_articles(
            workbook_path,
            self.source,
            target_date=target_date,
            media_prefix=self.media_prefix,
        )
        self.last_candidate_count = len(articles)
        effective_limit = max(limit, candidate_limit or limit)
        selected = articles[:effective_limit]
        self.last_fetched_count = len(selected)
        return selected


class RIONewsChinaEnergyScraper(RIONewsSourceScraper):
    media_prefix = "中国能源网_"
    fallback_scraper_class = ChinaEnergyScraper


class RIONewsBatteryScraper(RIONewsSourceScraper):
    media_prefix = "电池网_"
    fallback_scraper_class = ITDCWScraper


class RIONewsXEVCarScraper(RIONewsSourceScraper):
    media_prefix = "我爱电车网_"
    fallback_scraper_class = XEVCarScraper


class RIONewsInternationalEnergyScraper(RIONewsSourceScraper):
    media_prefix = "国际能源网_"
    fallback_scraper_class = InternationalEnergyScraper
