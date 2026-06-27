import json
import logging
import re

import httpx

from app.scrapers.base import BaseScraperAdapter, NormalisedCourse, register_scraper

logger = logging.getLogger(__name__)

_SITEMAP_URL = "https://www.orsys.fr/sitemapFRA.xml"


def _parse_iso_duration(duration_str: str | None) -> float | None:
    if not duration_str:
        return None
    m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?", duration_str.strip())
    if not m:
        return None
    hours = int(m.group(1)) if m.group(1) else 0
    minutes = int(m.group(2)) if m.group(2) else 0
    return hours + minutes / 60.0


def _extract_price(html: str) -> float | None:
    m = re.search(r"(\d[\d\s]*\d)\s*[€]", html)
    if m:
        cleaned = m.group(1).replace("\u202f", "").replace(" ", "")
        try:
            return float(cleaned)
        except ValueError:
            return None
    return None


@register_scraper("ORSYS")
class ORSYSScraperAdapter(BaseScraperAdapter):
    MAX_COURSES = 2500

    def fetch_all_courses(self) -> list[NormalisedCourse]:
        return self._fetch_all_from_sitemap(_SITEMAP_URL, "ORSYSScraperAdapter")

    def _fetch_course(self, url: str) -> NormalisedCourse | None:
        try:
            resp = self._http.get(url, timeout=30)
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning("ORSYSScraperAdapter — erreur HTTP %s : %s", url, exc)
            return None

        html = resp.text
        data = self._extract_jsonld(html)
        if not data:
            return None

        name = data.get("name") or ""
        description = data.get("description") or ""
        duration_hours = _parse_iso_duration(data.get("duration") or "")
        course_code = data.get("courseCode") or ""
        price = self._extract_jsonld_price(data) or _extract_price(html)
        category = self._extract_category(html)

        return NormalisedCourse(
            external_id=course_code or url.rstrip("/").split("/")[-1],
            title=name,
            url=url,
            description=description,
            duration_hours=duration_hours,
            price=price,
            category=category,
            format=None,
            certification=None,
        )

    @staticmethod
    def _extract_jsonld(html: str) -> dict | None:
        ld_match = re.search(
            r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>',
            html, re.DOTALL,
        )
        if not ld_match:
            logger.warning("ORSYSScraperAdapter — pas de JSON-LD")
            return None
        try:
            data = json.loads(ld_match.group(1).strip())
        except json.JSONDecodeError:
            logger.warning("ORSYSScraperAdapter — JSON-LD invalide")
            return None
        if not isinstance(data, dict) or data.get("@type") != "Course":
            logger.debug("ORSYSScraperAdapter — pas un Course schema")
            return None
        return data

    @staticmethod
    def _extract_jsonld_price(data: dict) -> float | None:
        offers = data.get("offers")
        if not isinstance(offers, list) or not offers:
            return None
        first = offers[0]
        if not isinstance(first, dict):
            return None
        raw = first.get("price")
        if raw is None:
            return None
        try:
            return float(raw)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _extract_category(html: str) -> str | None:
        bc = re.search(r'breadcrumb[^>]*>(.*?)</nav>', html, re.DOTALL | re.IGNORECASE)
        if bc:
            items = re.findall(r'>([^<]+)<', bc.group(1))
            cleaned = [i.strip() for i in items if i.strip() and i.strip() not in ("Accueil", "Formation")]
            if len(cleaned) >= 1:
                return cleaned[0]
        return None

