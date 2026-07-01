from app.scrapers.base import (
    BaseScraperAdapter,
    NormalisedCourse,
    get_scraper,
    list_scrapers,
    register_scraper,
)
from app.scrapers.cegos import CegosScraperAdapter
from app.scrapers.demos import DemosScraperAdapter
from app.scrapers.generic import GenericScraperAdapter
from app.scrapers.orsys import ORSYSScraperAdapter
from app.scrapers.scap import SCAPScraperAdapter
from app.scrapers.stub import StubScraperAdapter

__all__ = [
    "BaseScraperAdapter",
    "NormalisedCourse",
    "CegosScraperAdapter",
    "DemosScraperAdapter",
    "GenericScraperAdapter",
    "ORSYSScraperAdapter",
    "SCAPScraperAdapter",
    "StubScraperAdapter",
    "get_scraper",
    "list_scrapers",
    "register_scraper",
]
