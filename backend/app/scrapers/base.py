import logging
import re
from abc import ABC, abstractmethod
from typing import TypedDict

import httpx

logger = logging.getLogger(__name__)


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
    MAX_COURSES: int | None = None

    def __init__(self, school_registry_id: int) -> None:
        self.school_registry_id = school_registry_id
        self._http = httpx.Client()
        self._http.headers.update({"User-Agent": "ATLAS-Insight/1.0"})

    @abstractmethod
    def fetch_all_courses(self) -> list[NormalisedCourse]:
        ...

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> "BaseScraperAdapter":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object | None,
    ) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Helpers partagés
    # ------------------------------------------------------------------

    def _fetch_sitemap_urls(self, sitemap_url: str, label: str) -> list[str]:
        """Fetch sitemap XML and return formation URLs."""
        try:
            resp = self._http.get(sitemap_url, timeout=30)
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            logger.error("%s — erreur sitemap : %s", label, exc)
            raise RuntimeError(f"Échec récupération du sitemap {label}.") from exc

        urls = re.findall(r"<loc>(.*?)</loc>", resp.text)
        return [u.strip() for u in urls if "/formation/" in u.lower()]

    def _fetch_all_from_sitemap(self, sitemap_url: str, label: str) -> list[NormalisedCourse]:
        """Template method: iterate sitemap URLs, call _fetch_course (overridden by subclass)."""
        logger.info("%s — fetching sitemap...", label)
        urls = self._fetch_sitemap_urls(sitemap_url, label)
        logger.info("%s — %d formations dans le sitemap.", label, len(urls))

        results: list[NormalisedCourse] = []
        for i, url in enumerate(urls):
            if self.MAX_COURSES is not None and i >= self.MAX_COURSES:
                logger.warning("%s — borne MAX_COURSES=%d atteinte.", label, self.MAX_COURSES)
                break
            try:
                course = self._fetch_course(url)
                if course:
                    results.append(course)
            except Exception:
                logger.exception("%s — erreur sur %s", label, url)

        logger.info("%s — %d cours extraits.", label, len(results))
        return results

    def _fetch_course(self, url: str) -> NormalisedCourse | None:
        """Override in subclasses for page-specific parsing."""
        return None
