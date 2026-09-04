import logging
import re
from abc import ABC, abstractmethod
from typing import TypedDict

import httpx

from app.core.url_safety import is_same_site, validate_external_url

logger = logging.getLogger(__name__)

# Segment d'URL identifiant une page de formation dans un sitemap.
# Défaut partagé ORSYS/Demos ; surchargeable par adaptateur ou par config.
COURSE_URL_PATTERN = "/formation/"


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

    def __init__(self, school_registry_id: int, config: dict | None = None) -> None:
        self.school_registry_id = school_registry_id
        self.config = config or {}
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

    def _fetch_sitemap_urls(
        self,
        sitemap_url: str,
        label: str,
        url_pattern: str | None = COURSE_URL_PATTERN,
    ) -> list[str]:
        """Fetch sitemap XML and return the course URLs it declares.

        Le sitemap est un document distant : ses `<loc>` sont des entrées non
        fiables. On n'en retient que des URLs http(s) externes appartenant au
        même site que le sitemap — sinon un sitemap compromis ferait émettre au
        serveur des requêtes vers l'hôte de son choix (SSRF).

        `url_pattern` filtre les pages de formation ; `None` désactive le filtre
        pour les appelants qui appliquent le leur.
        """
        try:
            resp = self._http.get(sitemap_url, timeout=30)
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            logger.error("%s — erreur sitemap : %s", label, exc)
            raise RuntimeError(f"Échec récupération du sitemap {label}.") from exc

        declared = [u.strip() for u in re.findall(r"<loc>(.*?)</loc>", resp.text)]
        if url_pattern:
            declared = [u for u in declared if url_pattern.lower() in u.lower()]

        kept: list[str] = []
        for url in declared:
            try:
                validate_external_url(url)
            except ValueError:
                logger.warning("%s — URL de sitemap rejetée (interne) : %s", label, url)
                continue
            if not is_same_site(url, sitemap_url):
                logger.warning("%s — URL de sitemap hors site ignorée : %s", label, url)
                continue
            kept.append(url)

        if len(kept) != len(declared):
            logger.warning(
                "%s — %d URLs de sitemap écartées par l'allowlist.",
                label,
                len(declared) - len(kept),
            )
        return kept

    def _fetch_all_from_sitemap(
        self,
        sitemap_url: str,
        label: str,
        url_pattern: str | None = COURSE_URL_PATTERN,
    ) -> list[NormalisedCourse]:
        """Template method: iterate sitemap URLs, call _fetch_course (overridden by subclass)."""
        logger.info("%s — fetching sitemap...", label)
        urls = self._fetch_sitemap_urls(sitemap_url, label, url_pattern)
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
