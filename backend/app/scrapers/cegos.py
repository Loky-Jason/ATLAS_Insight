import logging
import re
import unicodedata

import httpx

from app.scrapers.base import BaseScraperAdapter, NormalisedCourse, register_scraper

logger = logging.getLogger(__name__)

_SEARCH_URL = "https://www.cegos.fr/search"
_CATEGORY_KEYWORDS = [
    "python", "excel", "management", "communication", "achats",
    "assistant", "banque", "bureautique", "commercial", "digital",
    "finance", "informatique", "marketing", "qualite", "rh",
    "securite", "strategie", "projet", "leadership", "vente",
    "data", "ia", "developpement", "langues", "anglais",
]

_CATEGORY_MAPPING = {
    "python": "Numérique",
    "excel": "Bureautique",
    "management": "Management",
    "communication": "Communication",
    "achats": "Achats",
    "assistant": "Bureautique",
    "banque": "Finance",
    "bureautique": "Bureautique",
    "commercial": "Commerce",
    "digital": "Numérique",
    "finance": "Finance",
    "informatique": "Numérique",
    "marketing": "Marketing",
    "qualite": "Qualité",
    "rh": "Ressources Humaines",
    "securite": "Sécurité",
    "strategie": "Management",
    "projet": "Management",
    "leadership": "Management",
    "vente": "Commerce",
    "data": "Numérique",
    "ia": "Numérique",
    "developpement": "Numérique",
    "langues": "Langues",
    "anglais": "Langues",
}


def _slugify(title: str) -> str:
    normalized = unicodedata.normalize("NFKD", title)
    ascii_str = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-zA-Z0-9-]+", "-", ascii_str.lower()).strip("-")


@register_scraper("Cegos")
class CegosScraperAdapter(BaseScraperAdapter):
    MAX_COURSES = 2500

    def fetch_all_courses(self) -> list[NormalisedCourse]:
        logger.info(
            "CegosScraperAdapter.fetch_all_courses() — "
            "scraping catalogue via recherche par mots-clés..."
        )

        seen: set[str] = set()
        results: list[NormalisedCourse] = []

        for keyword in _CATEGORY_KEYWORDS:
            if len(results) >= self.MAX_COURSES:
                logger.warning("CegosScraperAdapter — borne MAX_COURSES atteinte.")
                break
            try:
                courses = self._search(keyword)
                for c in courses:
                    if c["external_id"] not in seen:
                        seen.add(c["external_id"])
                        results.append(c)
            except Exception:
                logger.exception("CegosScraperAdapter — erreur mot-clé %s", keyword)

        logger.info("CegosScraperAdapter — %d cours extraits.", len(results))
        return results

    def _search(self, keyword: str) -> list[NormalisedCourse]:
        try:
            resp = self._http.get(
                _SEARCH_URL, params={"q": keyword}, timeout=30,
            )
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning("CegosScraperAdapter — erreur search q=%s : %s", keyword, exc)
            return []

        card_blocks = self._find_card_blocks(resp.text)

        results: list[NormalisedCourse] = []
        for block in card_blocks:
            parsed = self._parse_card(block, keyword)
            if parsed:
                results.append(parsed)

        return results

    @staticmethod
    def _find_card_blocks(html: str) -> list[str]:
        raw = re.findall(
            r'(<div\s+class="card[^"]*card--result[^"]*">.*?</div>\s*</div>\s*</div>)',
            html,
            re.DOTALL,
        )
        if raw:
            return raw
        return re.findall(
            r'(<div\s+class="card[^"]*card--result[^"]*">.*?</div>\s*</article>)',
            html,
            re.DOTALL,
        )

    @staticmethod
    def _parse_card(block: str, keyword: str) -> NormalisedCourse | None:
        url_m = re.search(r'data-redirectlink="([^"]+)"', block)
        title_m = re.search(r'card__title[^>]*>(.*?)</h2>', block, re.DOTALL)
        desc_m = re.search(r'card__description[^>]*>(.*?)</p>', block, re.DOTALL)

        if not url_m or not title_m:
            return None

        url = url_m.group(1).strip()
        raw_title = title_m.group(1)
        title = re.sub(r"<[^>]+>", "", raw_title).strip()
        if not title:
            return None

        desc = None
        if desc_m:
            desc = re.sub(r"<[^>]+>", "", desc_m.group(1)).strip() or None

        ext_id = f"cegos-{_slugify(title)[:60]}"

        return NormalisedCourse(
            external_id=ext_id,
            title=title,
            url=url,
            description=desc,
            duration_hours=None,
            price=None,
            category=_CATEGORY_MAPPING.get(keyword, "Formation"),
            format=None,
            certification=None,
        )

