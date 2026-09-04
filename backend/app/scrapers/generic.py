"""GenericScraperAdapter — scraper configurable sans code.

Modes
-----
sitemap
    Récupère les URLs depuis un sitemap XML (auto-détection ou URL fournie).
    Sur chaque page : extraction JSON-LD + sélecteurs CSS selon la config.

list
    Scrape une page liste unique, suit les liens vers chaque cours.

Config (stockée dans school_registries.config)
-------------------------------------------------
{
  "mode": "sitemap",
  "sitemap_url": "auto",
  "url_pattern": "/formation/",
  "list_url": "https://...",
  "course_link_selector": "a.card",
  "selectors": {
    "title": "h1",
    "description": "meta[name=description]::attr(content)",
    "duration": ".duration",
    "price": ".price",
    "category": ".category",
    "format": ".format",
    "certification": ".certification"
  },
  "use_jsonld": true,
  "max_courses": 500,
  "headers": {"Referer": "..."},
  "timeout": 30
}
"""

from __future__ import annotations

import json
import logging
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from app.scrapers.base import (
    COURSE_URL_PATTERN,
    BaseScraperAdapter,
    NormalisedCourse,
    register_scraper,
)

logger = logging.getLogger(__name__)

_SITEMAP_DISCOVERY_PATHS = ["/sitemap.xml", "/sitemap_index.xml"]


@register_scraper("generic")
class GenericScraperAdapter(BaseScraperAdapter):
    def __init__(self, school_registry_id: int, config: dict | None = None) -> None:
        super().__init__(school_registry_id, config)
        self._max_courses: int | None = None

    def fetch_all_courses(self) -> list[NormalisedCourse]:
        cfg = self.config
        mode = cfg.get("mode", "sitemap")
        self._configure_http(cfg)

        if mode == "list":
            return self._fetch_from_list_page(cfg)
        return self._fetch_from_sitemap(cfg)

    # ------------------------------------------------------------------
    # HTTP config
    # ------------------------------------------------------------------

    def _configure_http(self, cfg: dict) -> None:
        self._max_courses = cfg.get("max_courses")
        for key, val in (cfg.get("headers") or {}).items():
            self._http.headers[key] = val

    # ------------------------------------------------------------------
    # Sitemap mode
    # ------------------------------------------------------------------

    def _fetch_from_sitemap(self, cfg: dict) -> list[NormalisedCourse]:
        sitemap_url = self._resolve_sitemap_url(cfg)
        url_pattern = cfg.get("url_pattern", COURSE_URL_PATTERN)
        use_jsonld = cfg.get("use_jsonld", True)

        logger.info("Generic — sitemap: %s", sitemap_url)
        urls = self._fetch_sitemap_urls(sitemap_url, "generic", url_pattern)
        logger.info("Generic — %d URLs après filtre", len(urls))

        self._apply_max_courses(urls)

        results: list[NormalisedCourse] = []
        for url in urls:
            try:
                course = self._scrape_page(url, use_jsonld, cfg)
                if course:
                    results.append(course)
            except Exception:
                logger.exception("Generic — erreur sur %s", url)

        logger.info("Generic — %d cours extraits", len(results))
        return results

    def _resolve_sitemap_url(self, cfg: dict) -> str:
        explicit = cfg.get("sitemap_url")
        if explicit and explicit != "auto":
            return explicit

        base_url = self.config.get("_school_url", "")
        if not base_url:
            raise ValueError(
                "Impossible de déterminer l'URL du sitemap. "
                "Fournissez sitemap_url ou _school_url dans la config."
            )

        for path in _SITEMAP_DISCOVERY_PATHS:
            candidate = urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))
            try:
                resp = self._http.head(candidate, timeout=15)
                if resp.status_code < 400:
                    logger.info("Generic — sitemap détecté: %s", candidate)
                    return candidate
            except Exception:
                continue

        fallback = urljoin(base_url.rstrip("/") + "/", "sitemap.xml")
        logger.warning("Generic — auto-détection échouée, fallback: %s", fallback)
        return fallback

    # ------------------------------------------------------------------
    # List page mode
    # ------------------------------------------------------------------

    def _fetch_from_list_page(self, cfg: dict) -> list[NormalisedCourse]:
        list_url = cfg.get("list_url")
        if not list_url:
            raise ValueError("mode=list nécessite list_url dans la config")

        selector = cfg.get("course_link_selector", "a")
        use_jsonld = cfg.get("use_jsonld", True)

        logger.info("Generic — list page: %s", list_url)
        resp = self._http.get(list_url, timeout=30)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "lxml")
        links = soup.select(selector)
        urls = []
        for a in links:
            href = a.get("href")
            if href:
                urls.append(urljoin(list_url, href))

        urls = list(dict.fromkeys(urls))
        self._apply_max_courses(urls)
        logger.info("Generic — %d liens cours trouvés", len(urls))

        results: list[NormalisedCourse] = []
        for url in urls:
            try:
                course = self._scrape_page(url, use_jsonld, cfg)
                if course:
                    results.append(course)
            except Exception:
                logger.exception("Generic — erreur sur %s", url)

        return results

    # ------------------------------------------------------------------
    # Page scraping — JSON-LD + CSS selectors
    # ------------------------------------------------------------------

    def _scrape_page(
        self, url: str, use_jsonld: bool, cfg: dict
    ) -> NormalisedCourse | None:
        resp = self._http.get(url, timeout=30)
        resp.raise_for_status()
        html = resp.text

        data: dict[str, object] = {}
        if use_jsonld:
            data = self._extract_jsonld(html) or {}

        selectors = cfg.get("selectors") or {}
        fields = [
            "title", "description", "duration_hours", "price",
            "category", "format", "certification",
        ]

        for field in fields:
            if data.get(field) is not None:
                continue
            selector = selectors.get(field)
            if not selector:
                continue
            val = self._apply_selector(html, selector)
            if val is not None:
                data[field] = val

        title = data.get("title")
        if not title or not isinstance(title, str):
            title = self._extract_title_fallback(html)
        if not title:
            logger.warning("Generic — titre introuvable: %s", url)
            return None

        ext_id = url.rstrip("/").split("/")[-1]
        duration = self._normalize_duration(data.get("duration_hours"))
        price = self._normalize_price(data.get("price"))

        return NormalisedCourse(
            external_id=ext_id,
            title=str(title).strip(),
            url=url,
            description=str(data.get("description") or "").strip()[:2000] or None,
            duration_hours=duration,
            price=price,
            category=str(data.get("category") or "").strip() or None,
            format=str(data.get("format") or "").strip() or None,
            certification=str(data.get("certification") or "").strip() or None,
        )

    # ------------------------------------------------------------------
    # JSON-LD extraction
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_jsonld(html: str) -> dict | None:
        matches = re.findall(
            r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>',
            html, re.DOTALL | re.IGNORECASE
        )
        for match in matches:
            try:
                data = json.loads(match.strip())
            except json.JSONDecodeError:
                continue
            items = data if isinstance(data, list) else data.get("@graph") or [data]
            for item in items if isinstance(items, list) else [items]:
                if not isinstance(item, dict):
                    continue
                types = item.get("@type", "")
                if isinstance(types, str):
                    types = [types]
                if any("Course" in t for t in types):
                    return GenericScraperAdapter._normalize_jsonld(item)
        return None

    @staticmethod
    def _normalize_jsonld(item: dict) -> dict:
        def _get(obj: dict, *keys: str) -> object:
            curr: object = obj
            for key in keys:
                if not isinstance(curr, dict):
                    return None
                curr = curr.get(key)
            return curr

        def _first_dict(val: object) -> dict:
            if isinstance(val, dict):
                return val
            if isinstance(val, list) and val:
                return val[0] if isinstance(val[0], dict) else {}
            return {}

        offers = _first_dict(item.get("offers"))
        about = _first_dict(item.get("about"))

        return {
            "title": _get(item, "name"),
            "description": _get(item, "description"),
            "duration_hours": _get(item, "timeRequired"),
            "price": _get(offers, "price"),
            "category": _get(about, "name"),
            "format": _get(item, "courseMode"),
            "certification": _get(item, "educationalCredentialAwarded"),
        }

    # ------------------------------------------------------------------
    # CSS selector extractor
    # ------------------------------------------------------------------

    @staticmethod
    def _apply_selector(html: str, selector: str) -> str | None:
        attr_match = re.match(r"^([^:]+)::attr\((\w+)\)$", selector)
        soup = BeautifulSoup(html, "lxml")

        if attr_match:
            css_sel = attr_match.group(1).strip()
            attr_name = attr_match.group(2).strip()
            el = soup.select_one(css_sel)
            if el:
                val = el.get(attr_name)
                return str(val).strip() if val else None

        el = soup.select_one(selector)
        if el:
            return el.get_text(strip=True)
        return None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_title_fallback(html: str) -> str | None:
        m = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.DOTALL)
        if m:
            return re.sub(r"<[^>]+>", "", m.group(1)).strip()
        m = re.search(r'<meta property="og:title" content="([^"]*)"', html)
        if m:
            return m.group(1).strip()
        return None

    @staticmethod
    def _normalize_duration(val: object) -> float | None:
        if val is None:
            return None
        if isinstance(val, int | float):
            return float(val)
        s = str(val).strip().lower()
        m = re.search(r"(\d+(?:\.\d+)?)\s*h", s)
        if m:
            return float(m.group(1))
        m = re.search(r"(\d+(?:\.\d+)?)\s*jour", s)
        if m:
            return float(m.group(1)) * 7
        try:
            return float(s)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _normalize_price(val: object) -> float | None:
        if val is None:
            return None
        if isinstance(val, int | float):
            return float(val)
        s = str(val).strip().replace("\xa0", "").replace(" ", "")
        m = re.search(r"(\d+(?:[.,]\d{1,2})?)", s)
        if m:
            try:
                return float(m.group(1).replace(",", "."))
            except ValueError:
                return None
        return None

    def _apply_max_courses(self, urls: list[str]) -> None:
        if self._max_courses is not None and self._max_courses >= 0:
            urls[:] = urls[:self._max_courses]
