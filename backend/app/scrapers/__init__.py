from app.scrapers.base import (
    BaseScraperAdapter,
    NormalisedCourse,
    get_scraper,
    list_scrapers,
    register_scraper,
)
from app.scrapers.scap import SCAPScraperAdapter
from app.scrapers.stub import StubScraperAdapter

__all__ = [
    "BaseScraperAdapter",
    "NormalisedCourse",
    "SCAPScraperAdapter",
    "StubScraperAdapter",
    "get_scraper",
    "list_scrapers",
    "register_scraper",
]
