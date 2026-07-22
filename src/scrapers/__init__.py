from __future__ import annotations

from .base import BaseScraper
from .batteries_international import BatteriesInternationalScraper
from .batterytechonline import BatteryTechOnlineScraper
from .electrek import ElectrekScraper
from .electrive import ElectriveScraper
from .generic import GenericListingScraper
from .multi_page import (
    ChinaNengyuanScraper,
    ChinaNengyuanTechScraper,
    ChinaNengyuanWindScraper,
    H2ViewScraper,
    PerovskiteInfoScraper,
    SolarInEnScraper,
)
from .pv_magazine import PVMagazineScraper
from .science_net import ScienceNetScraper
from .supply_chain_digital import SupplyChainDigitalScraper
from .volta import VoltaFoundationScraper
from .xinhua_tech import XinhuaTechScraper


SCRAPER_REGISTRY: dict[str, type[BaseScraper]] = {
    "electrive": ElectriveScraper,
    "batteries international": BatteriesInternationalScraper,
    "volta foundation": VoltaFoundationScraper,
    "battery tech online": BatteryTechOnlineScraper,
    "supply chain digital": SupplyChainDigitalScraper,
    "electrek": ElectrekScraper,
    "pv magazine": PVMagazineScraper,
    "科学网新闻": ScienceNetScraper,
    "新华网科技": XinhuaTechScraper,
    "h2 view": H2ViewScraper,
    "国际太阳能光伏网": SolarInEnScraper,
    "新能源网": ChinaNengyuanTechScraper,
    "perovskite-info": PerovskiteInfoScraper,
    "全球风电网": ChinaNengyuanWindScraper,
    "中国新能源网-新闻": ChinaNengyuanScraper,
}


def get_scraper_class(source_name: str) -> type[BaseScraper]:
    return SCRAPER_REGISTRY.get(source_name.strip().lower(), GenericListingScraper)
