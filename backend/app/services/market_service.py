"""Service de veille marché — abstraction provider + scoring + persistance.

Architecture :
  MarketSearchProvider (ABC) — interface à implémenter pour tout provider réel.
  StubMarketProvider          — données déterministes (tests / démo).

POINT D'INTÉGRATION RÉEL :
  Pour brancher un vrai provider (ex. WebSearch via Bing/DuckDuckGo, ou un LLM
  qui retourne des formations marché en JSON) :
    1. Créer une classe héritant de MarketSearchProvider.
    2. Implémenter la méthode `search(query) -> list[RawMarketResult]`.
    3. Dans app/core/config.py, ajouter un paramètre MARKET_PROVIDER
       (valeurs : "stub" | "web" | "llm").
    4. Modifier get_market_provider() ci-dessous pour instancier le bon provider.
  Le reste du pipeline (scoring, déduplication, persistance) est inchangé.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, TypedDict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.course import Course
from app.models.market_course import MarketCourse

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

class RawMarketResult(TypedDict):
    """Structure retournée par un provider de veille marché."""
    title: str
    school: str
    source_url: str
    summary: str
    category: str | None


# ---------------------------------------------------------------------------
# Interface provider
# ---------------------------------------------------------------------------

class MarketSearchProvider(ABC):
    """Interface abstraite pour tout provider de recherche marché."""

    @abstractmethod
    def search(self, query: str) -> list[RawMarketResult]:
        """
        Recherche des formations marché correspondant à *query*.

        Parameters
        ----------
        query : termes de recherche (ex. "formations bureautique Paris 2025")

        Returns
        -------
        list[RawMarketResult] — résultats bruts, non scorés.
        """


# ---------------------------------------------------------------------------
# Implémentation Stub (démo / tests)
# ---------------------------------------------------------------------------

_STUB_DATA: list[RawMarketResult] = [
    {
        "title": "Excel avancé — tableaux croisés dynamiques",
        "school": "ORSYS",
        "source_url": "https://www.orsys.fr/formation-excel-avance.html",
        "summary": "Formation Excel niveau avancé, TCD, macros, Power Query.",
        "category": "Bureautique",
    },
    {
        "title": "Management d'équipe à distance",
        "school": "Cegos",
        "source_url": "https://www.cegos.fr/formation-management-a-distance",
        "summary": "Piloter et animer une équipe en mode hybride / distanciel.",
        "category": "Management",
    },
    {
        "title": "Python pour non-développeurs",
        "school": "Elephant In The Room",
        "source_url": "https://elephant-in-the-room.fr/python-non-dev",
        "summary": "Initiation Python : automatisation de tâches bureautiques.",
        "category": "Numérique",
    },
    {
        "title": "Intelligence artificielle — usages pratiques",
        "school": "Numa",
        "source_url": "https://numa.co/formation-ia-pratique",
        "summary": "Comprendre et utiliser l'IA générative dans son travail quotidien.",
        "category": "Numérique",
    },
    {
        "title": "Prise de parole en public",
        "school": "IFOCOP",
        "source_url": "https://www.ifocop.fr/formation-prise-de-parole",
        "summary": "Techniques de communication orale, assertivité, gestion du trac.",
        "category": "Communication",
    },
    {
        "title": "Gestion du stress et des émotions",
        "school": "Demos",
        "source_url": "https://www.demos.fr/formation-stress-emotions",
        "summary": "Outils pratiques pour gérer le stress professionnel et les émotions au travail.",
        "category": "Bien-être",
    },
    {
        "title": "Marchés publics — fondamentaux",
        "school": "EFE",
        "source_url": "https://www.efe.fr/formation-marches-publics",
        "summary": "Maîtriser le cadre réglementaire des marchés publics (code de la commande publique).",
        "category": "Réglementaire",
    },
    {
        "title": "Accessibilité numérique — RGAA 4",
        "school": "Access42",
        "source_url": "https://access42.net/formation-rgaa",
        "summary": "Audit et mise en conformité RGAA 4 pour les sites de services publics.",
        "category": "Numérique",
    },
]


class StubMarketProvider(MarketSearchProvider):
    """
    Provider de démonstration renvoyant des données déterministes.
    Utilisé par défaut quand aucun provider réel n'est configuré.
    """

    def search(self, query: str) -> list[RawMarketResult]:  # noqa: ARG002
        logger.info("StubMarketProvider.search() — retourne %d résultats fictifs.", len(_STUB_DATA))
        return list(_STUB_DATA)


# ---------------------------------------------------------------------------
# Factory provider
# ---------------------------------------------------------------------------

def get_market_provider() -> MarketSearchProvider:
    """
    Retourne le provider configuré.

    POINT D'EXTENSION : lire ici la config (ex. settings.market_provider)
    pour instancier le bon provider (WebSearchProvider, LLMProvider…).
    Actuellement, seul StubMarketProvider est disponible.
    """
    return StubMarketProvider()


# ---------------------------------------------------------------------------
# Logique de scoring
# ---------------------------------------------------------------------------

def _category_overlap(cat_a: str | None, cat_b: str | None) -> float:
    """Score [0, 1] de recouvrement catégorie (exact = 1.0, partiel = 0.5, aucun = 0.0)."""
    if not cat_a or not cat_b:
        return 0.0
    a = cat_a.lower().strip()
    b = cat_b.lower().strip()
    if a == b:
        return 1.0
    if a in b or b in a:
        return 0.5
    return 0.0


def _compute_relevance(
    raw: RawMarketResult,
    existing_titles: list[str],
    existing_categories: list[str],
) -> float:
    """
    Score de pertinence [0, 1] pour une formation marché.

    Critères :
      +0.5 si la catégorie est présente chez SCAP (catégorie porteuse)
      +0.3 si le titre est proche d'une demande existante (non encore couverte)
      -0.4 si un cours SCAP très similaire existe déjà (doublon inutile)
    """
    from difflib import SequenceMatcher

    score = 0.5  # base neutre

    raw_cat = (raw.get("category") or "").lower()

    # Bonus catégorie présente chez SCAP
    for ec in existing_categories:
        if raw_cat and ec and (raw_cat in ec.lower() or ec.lower() in raw_cat):
            score += 0.3
            break

    # Pénalité si cours très similaire déjà en base
    raw_title = raw["title"].lower()
    for et in existing_titles:
        sim = SequenceMatcher(None, raw_title, et.lower()).ratio()
        if sim > 0.75:
            score -= 0.4
            break

    return round(max(0.0, min(1.0, score)), 2)


# ---------------------------------------------------------------------------
# Fonction principale
# ---------------------------------------------------------------------------

async def run_market_scan(
    db: AsyncSession,
    user_id: int,
    query: str = "formations professionnelles Paris 2025",
) -> dict[str, Any]:
    """
    Déclenche une veille marché : recherche → scoring → persistance.

    Returns
    -------
    dict {inserted, skipped, results: list[dict]}
    """
    provider = get_market_provider()

    try:
        raw_results = provider.search(query)
    except Exception as exc:
        logger.error("Erreur provider veille marché : %s", exc)
        raise

    # Chargement données SCAP existantes
    try:
        course_result = await db.execute(
            select(Course.title, Course.category).where(Course.status == "active")
        )
        scap_rows = course_result.all()
        existing_titles = [r[0] for r in scap_rows]
        existing_categories = [r[1] for r in scap_rows if r[1]]

        # Titres déjà en MarketCourse (évite doublons dans la table)
        mc_result = await db.execute(select(MarketCourse.title))
        existing_mc_titles = {r[0].lower() for r in mc_result.all()}
    except Exception as exc:
        logger.error("Erreur DB lors du chargement données SCAP : %s", exc)
        raise

    inserted: list[dict[str, Any]] = []
    skipped = 0

    for raw in raw_results:
        if raw["title"].lower() in existing_mc_titles:
            skipped += 1
            continue

        relevance = _compute_relevance(raw, existing_titles, existing_categories)

        why_parts: list[str] = []
        if relevance >= 0.7:
            why_parts.append("Formation très pertinente pour le catalogue SCAP.")
        elif relevance >= 0.5:
            why_parts.append("Formation potentiellement complémentaire au catalogue SCAP.")
        else:
            why_parts.append("Formation déjà bien couverte ou peu pertinente.")

        why = " ".join(why_parts) + f" (score: {relevance})"

        mc = MarketCourse(
            title=raw["title"],
            school=raw.get("school"),
            source_url=raw.get("source_url"),
            summary=raw.get("summary"),
            relevance_score=relevance,
            why_it_works=why,
            status="candidate",
        )
        db.add(mc)
        existing_mc_titles.add(raw["title"].lower())

        inserted.append(
            {
                "title": raw["title"],
                "school": raw.get("school"),
                "source_url": raw.get("source_url"),
                "relevance_score": relevance,
                "why_it_works": why,
            }
        )

    try:
        await db.flush()
    except Exception as exc:
        logger.error("Erreur DB flush market scan : %s", exc)
        raise

    logger.info(
        "Veille marché : %d insérés, %d ignorés (doublons). user_id=%s",
        len(inserted),
        skipped,
        user_id,
    )

    return {
        "inserted": len(inserted),
        "skipped": skipped,
        "provider": type(provider).__name__,
        "results": inserted,
    }
