import logging

from app.scrapers.base import BaseScraperAdapter, NormalisedCourse, register_scraper

logger = logging.getLogger(__name__)

_STUB_DATA: list[NormalisedCourse] = [
    NormalisedCourse(
        external_id="stub-001",
        title="Excel avancé — tableaux croisés dynamiques",
        url="https://www.orsys.fr/formation-excel-avance.html",
        description="Formation Excel niveau avancé, TCD, macros, Power Query.",
        duration_hours=21.0,
        price=None,
        category="Bureautique",
        format="presentiel",
        certification=None,
    ),
    NormalisedCourse(
        external_id="stub-002",
        title="Python pour non-développeurs",
        url="https://elephant-in-the-room.fr/python-non-dev",
        description="Initiation Python : automatisation de tâches bureautiques.",
        duration_hours=35.0,
        price=None,
        category="Numérique",
        format="presentiel",
        certification=None,
    ),
    NormalisedCourse(
        external_id="stub-003",
        title="Management d'équipe à distance",
        url="https://www.cegos.fr/formation-management-a-distance",
        description="Piloter et animer une équipe en mode hybride / distanciel.",
        duration_hours=14.0,
        price=None,
        category="Management",
        format="distanciel",
        certification=None,
    ),
    NormalisedCourse(
        external_id="stub-004",
        title="Intelligence artificielle — usages pratiques",
        url="https://numa.co/formation-ia-pratique",
        description="Comprendre et utiliser l'IA générative dans son travail quotidien.",
        duration_hours=7.0,
        price=None,
        category="Numérique",
        format="presentiel",
        certification=None,
    ),
]


@register_scraper("stub")
class StubScraperAdapter(BaseScraperAdapter):
    def __init__(self, school_registry_id: int) -> None:
        super().__init__(school_registry_id)

    def fetch_all_courses(self) -> list[NormalisedCourse]:
        logger.info(
            "StubScraperAdapter.fetch_all_courses() — %d cours fictifs.",
            len(_STUB_DATA),
        )
        return list(_STUB_DATA)

    def close(self) -> None:
        pass
