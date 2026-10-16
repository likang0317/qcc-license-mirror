"""数据源工厂"""
from .base import DataSource, Contact
from .manual import ManualSource
from .qcc_scrape import QccScrapeSource
from .qcc_api import QccApiSource

SOURCES = {
    "manual": ManualSource,
    "qcc_scrape": QccScrapeSource,
    "qcc_api": QccApiSource,
}

def create(type: str, **kwargs) -> DataSource:
    cls = SOURCES.get(type, ManualSource)
    return cls(**kwargs)
