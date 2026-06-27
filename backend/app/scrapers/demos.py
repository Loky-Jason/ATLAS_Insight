import json
import logging
import re

import httpx

from app.scrapers.base import BaseScraperAdapter, NormalisedCourse, register_scraper

logger = logging.getLogger(__name__)

_SITEMAP_URL = "https://www.demos.fr/formation-sitemap.xml"


@register_scraper("Demos")
class DemosScraperAdapter(BaseScraperAdapter):
    MAX_COURSES = 1200

    def fetch_all_courses(self) -> list[NormalisedCourse]:
        return self._fetch_all_from_sitemap(_SITEMAP_URL, "DemosScraperAdapter")

    def _fetch_course(self, url: str) -> NormalisedCourse | None:
        try:
            resp = self._http.get(url, timeout=30)
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning("DemosScraperAdapter — erreur HTTP %s : %s", url, exc)
            return None

        html = resp.text
        title = self._extract_title(html) or ""
        description = self._extract_description(html)
        category = self._extract_category(html)
        duration_hours = self._extract_duration(html)
        external_id = url.rstrip("/").split("/")[-1]

        return NormalisedCourse(
            external_id=external_id,
            title=title,
            url=url,
            description=description,
            duration_hours=duration_hours,
            price=None,
            category=category,
            format=None,
            certification=None,
        )

    @staticmethod
    def _extract_title(html: str) -> str | None:
        m = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.DOTALL)
        if m:
            return re.sub(r"<[^>]+>", "", m.group(1)).strip()
        m = re.search(r'<meta property="og:title" content="([^"]*)"', html)
        if m:
            return m.group(1).strip()
        return None

    @staticmethod
    def _extract_description(html: str) -> str | None:
        m = re.search(r'<meta name="description" content="([^"]*)"', html)
        if m:
            return m.group(1).strip()
        m = re.search(r'<meta property="og:description" content="([^"]*)"', html)
        if m:
            return m.group(1).strip()
        return None

    @staticmethod
    def _extract_category(html: str) -> str | None:
        lds = re.findall(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', html, re.DOTALL)
        for ld in lds:
            try:
                data = json.loads(ld.strip())
            except json.JSONDecodeError:
                continue
            graph = data.get("@graph") if isinstance(data, dict) else None
            if not graph:
                continue
            for item in graph:
                if isinstance(item, dict) and item.get("@type") == "BreadcrumbList":
                    elements = item.get("itemListElement", [])
                    if len(elements) >= 2:
                        second = elements[1]
                        if isinstance(second, dict):
                            return second.get("name")
        return None

    @staticmethod
    def _extract_duration(html: str) -> float | None:
        durs = re.findall(r"(\d+)\s*h\b", html[:150000], re.IGNORECASE)
        if durs:
            try:
                return float(durs[0])
            except ValueError:
                return None
        durs = re.findall(r"(\d+)\s*jours?", html[:150000], re.IGNORECASE)
        if durs:
            try:
                return float(durs[0]) * 7
            except ValueError:
                return None
        return None

