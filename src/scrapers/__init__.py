from __future__ import annotations

from .base import BaseScraper
from .batteries_international import BatteriesInternationalScraper
from .batteries_news import BatteriesNewsScraper
from .batterytechonline import BatteryTechOnlineScraper
from .datacenter_knowledge import DataCenterKnowledgeScraper
from .bjx_storage import BJXStorageScraper
from .electrek import ElectrekScraper
from .electrive import ElectriveScraper
from .energytrend import EnergyTrendScraper
from .generic import GenericListingScraper
from .insideevs import InsideEVsScraper
from .interesting_engineering import InterestingEngineeringScraper
from .multi_page import (
    ChinaNengyuanScraper,
    ChinaNengyuanTechScraper,
    ChinaNengyuanWindScraper,
    H2ViewScraper,
    PerovskiteInfoScraper,
    SolarInEnScraper,
)
from .ne_time import NETimeScraper
from .pv_magazine import PVMagazineCIPVScraper, PVMagazineScraper
from .rionews import (
    RIONewsBatteryScraper,
    RIONewsChinaEnergyScraper,
    RIONewsInternationalEnergyScraper,
    RIONewsXEVCarScraper,
)
from .science_net import ScienceNetScraper
from .solarbe import SolarbeScraper
from .supply_chain_digital import SupplyChainDigitalScraper
from .testpv import TestPVScraper
from .volta import VoltaFoundationScraper
from .renewables_now import RenewablesNowScraper
from .xinhua_tech import XinhuaTechScraper
from .xmol import XMolScraper
from .tgs4c import TGS4COffshoreScraper


SCRAPER_REGISTRY: dict[str, type[BaseScraper]] = {
    "electrive": ElectriveScraper,
    "光伏测试网": TestPVScraper,
    "索比光伏": SolarbeScraper,
    "国际能源网": RIONewsInternationalEnergyScraper,
    "中国能源网": RIONewsChinaEnergyScraper,
    "我爱电车网": RIONewsXEVCarScraper,
    "北极星储能网": BJXStorageScraper,
    "insideevs": InsideEVsScraper,
    "interesting engineering": InterestingEngineeringScraper,
    "energytrend储能": EnergyTrendScraper,
    "ne时代": NETimeScraper,
    "电池网": RIONewsBatteryScraper,
    "x-mol": XMolScraper,
    "batteries international": BatteriesInternationalScraper,
    "batteries news": BatteriesNewsScraper,
    "data center knowledge": DataCenterKnowledgeScraper,
    "volta foundation": VoltaFoundationScraper,
    "battery tech online": BatteryTechOnlineScraper,
    "supply chain digital": SupplyChainDigitalScraper,
    "electrek": ElectrekScraper,
    "pv magazine": PVMagazineScraper,
    "pv magazine c&i pv": PVMagazineCIPVScraper,
    "renewables now": RenewablesNowScraper,
    "4c offshore": TGS4COffshoreScraper,
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
