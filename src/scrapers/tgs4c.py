from __future__ import annotations

from .generic import GenericListingScraper


class TGS4COffshoreScraper(GenericListingScraper):
    """Prefer the complete TGS 4C news-card stream, including featured items."""

    link_selectors = (
        "a[href*='-nid'][href$='.html']",
    )
