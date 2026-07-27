from __future__ import annotations

from .generic import GenericListingScraper


class PVMagazineScraper(GenericListingScraper):
    link_selectors = (
        "a.post-block__title[href]",
        "article h3 a[href]",
        "article h2 a[href]",
        ".article-list a[href]",
        ".entry-title a[href]",
    )
