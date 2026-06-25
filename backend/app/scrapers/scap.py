import html as html_mod
import logging
import re

import httpx

from app.scrapers.base import BaseScraperAdapter, NormalisedCourse, register_scraper

logger = logging.getLogger(__name__)

_SEARCH_FIELDS: dict = {
    "DomainsIds": [],
    "Keywords": "",
    "PeriodicityIds": [],
    "CourseTypeIds": [],
    "District": "",
    "InstitutionId": "",
    "Disponibilities": [],
    "TimeSlots": [],
    "OnlyOpened": "false",
    "PageIndex": 0,
    "RegistrationStart": "",
    "RegistrationEnd": "",
}


@register_scraper("SCAP")
class SCAPScraperAdapter(BaseScraperAdapter):
    SEARCH_URL = "https://scap.paris.fr/Search/Elements"

    def __init__(self, school_registry_id: int) -> None:
        super().__init__(school_registry_id)
        self._http = httpx.Client()
        self._http.headers.update({"User-Agent": "ATLAS-Insight/1.0"})

    def fetch_all_courses(self) -> list[NormalisedCourse]:
        logger.info("SCAPScraperAdapter.fetch_all_courses() — scraping catalogue SCAP...")
        results: list[NormalisedCourse] = []
        page = 0

        while True:
            html_text = self._fetch_page(page)
            courses = self._parse_page(html_text)
            if not courses:
                break
            results.extend(courses)
            if not self._has_next(html_text):
                break
            page += 1

        logger.info("SCAPScraperAdapter — %d cours extraits.", len(results))
        return results

    def _fetch_page(self, page: int) -> str:
        payload = dict(_SEARCH_FIELDS)
        payload["PageIndex"] = page
        resp = self._http.post(self.SEARCH_URL, data=payload, timeout=30)
        resp.raise_for_status()
        return resp.text

    def _parse_page(self, html_text: str) -> list[NormalisedCourse]:
        blocks = re.findall(
            r'accordionElement(\d+)[^>]*>.*?<h4>(.*?)</h4>\s*<p>(.*?)</p>.*?'
            r'<h5>Objectif\s*:</h5>\s*<p>(.*?)</p>',
            html_text,
            re.DOTALL,
        )
        if not blocks and re.search(
            r'<h3>\s*\d+\s*r[eé]sultats?\s*</h3>', html_text, re.IGNORECASE
        ):
            logger.warning(
                "SCAPScraperAdapter._parse_page — page with announced results "
                "but no parsed courses (SCAP template may have changed)."
            )
        results: list[NormalisedCourse] = []
        for course_id, title, detail, objective in blocks:
            title = html_mod.unescape(title.strip())
            objective = html_mod.unescape(re.sub(r"&#xD;&#xA;", "\n", objective.strip()))
            detail_text = html_mod.unescape(detail.strip())
            duration = None
            m = re.search(r"(\d+(?:[.,]\d+)?)\s*h(?:eure)?s?", detail_text, re.IGNORECASE)
            if m:
                duration = float(m.group(1).replace(",", "."))
            results.append(
                NormalisedCourse(
                    external_id=course_id,
                    title=title,
                    url=f"https://scap.paris.fr/Element/Details/{course_id}",
                    description=objective,
                    duration_hours=duration,
                    price=None,
                    category=None,
                    format=None,
                    certification=None,
                )
            )
        return results

    @staticmethod
    def _has_next(html_text: str) -> bool:
        pages = re.findall(r"changePage\(\s*(\d+)\s*\)", html_text)
        if not pages:
            return False
        max_page = max(int(p) for p in pages)
        current = re.search(
            r'page-item\s+active[^>]*>.*?changePage\(\s*(\d+)\s*\)',
            html_text,
            re.DOTALL,
        )
        if not current:
            return False
        return int(current.group(1)) < max_page

    def close(self) -> None:
        self._http.close()
