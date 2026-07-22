from __future__ import annotations

from .generic import GenericListingScraper


class XinhuaTechScraper(GenericListingScraper):
    """Prefer Xinhua's chronological list over long-lived focus cards."""

    link_selectors = (
        "#content-list .item .tit a[href]",
        "#content-list .item a[href]",
        ".list .item .tit a[href]",
        ".focus .tit a[href]",
    )
