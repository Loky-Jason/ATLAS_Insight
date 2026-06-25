from abc import ABC, abstractmethod
from typing import TypedDict


class NormalisedCourse(TypedDict):
    external_id: str
    title: str
    url: str | None
    description: str | None
    duration_hours: float | None
    price: float | None
    category: str | None
    format: str | None
    certification: str | None


_scraper_registry: dict[str, type["BaseScraperAdapter"]] = {}


def register_scraper(name: str):
    """Decorator to register a scraper adapter class."""
    def wrapper(cls: type[BaseScraperAdapter]):
        _scraper_registry[name] = cls
        return cls
    return wrapper


def get_scraper(name: str) -> type["BaseScraperAdapter"]:
    if name not in _scraper_registry:
        raise ValueError(
            f"Unknown scraper: {name}. Available: {list(_scraper_registry.keys())}"
        )
    return _scraper_registry[name]


def list_scrapers() -> list[str]:
    return list(_scraper_registry.keys())


class BaseScraperAdapter(ABC):
    def __init__(self, school_registry_id: int) -> None:
        self.school_registry_id = school_registry_id

    @abstractmethod
    def fetch_all_courses(self) -> list[NormalisedCourse]:
        ...

    @abstractmethod
    def close(self) -> None:
        ...

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
