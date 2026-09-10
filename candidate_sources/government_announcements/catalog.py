from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CandidateSite:
    slug: str
    source_name: str
    region: str
    operator: str
    listing_urls: tuple[str, ...]
    sample_urls: tuple[str, ...]

    @property
    def primary_listing_url(self) -> str:
        return self.listing_urls[0]


GOVERNMENT_SITES: tuple[CandidateSite, ...] = (
    CandidateSite(
        slug="nea_notices",
        source_name="国家能源局_通知",
        region="全国",
        operator="国家能源局",
        listing_urls=("https://www.nea.gov.cn/policy/tz.htm",),
        sample_urls=(
            "https://www.nea.gov.cn/20260909/22d62e1a042a420c846f7598589136e2/c.html",
        ),
    ),
    CandidateSite(
        slug="nea_announcements",
        source_name="国家能源局_公告",
        region="全国",
        operator="国家能源局",
        listing_urls=("https://www.nea.gov.cn/policy/gg.htm",),
        sample_urls=(
            "https://www.nea.gov.cn/20260904/324fdc3e4908431392b82d19ab10de6b/c.html",
        ),
    ),
    CandidateSite(
        slug="miit_policy_documents",
        source_name="工业和信息化部_政策文件",
        region="全国",
        operator="工业和信息化部",
        listing_urls=("https://www.miit.gov.cn/zwgk/zcwj/index.html",),
        sample_urls=(
            "https://www.miit.gov.cn/zwgk/zcwj/wjfb/gg/art/2026/art_49854ea253964d85a688bc4a07fe0714.html",
        ),
    ),
    CandidateSite(
        slug="miit_public_notices",
        source_name="工业和信息化部_文件公示",
        region="全国",
        operator="工业和信息化部",
        listing_urls=("https://www.miit.gov.cn/zwgk/wjgs/index.html",),
        sample_urls=(
            "https://www.miit.gov.cn/zwgk/wjgs/art/2026/art_0b2035d10a644ff38840f697f5b35abe.html",
        ),
    ),
    CandidateSite(
        slug="ndrc_public_notices",
        source_name="国家发展改革委_通知公告",
        region="全国",
        operator="国家发展和改革委员会",
        listing_urls=("https://www.ndrc.gov.cn/xwdt/tzgg/",),
        sample_urls=(
            "https://www.ndrc.gov.cn/xwdt/tzgg/202608/t20260828_1407234.html",
        ),
    ),
)
