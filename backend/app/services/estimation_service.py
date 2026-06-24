"""Service d'estimation du nombre d'heures d'un cours proposé par similarité.

Méthode :
  1. Récupère les cours SCAP actifs avec hours_estimated renseigné.
  2. Filtre sur la même catégorie (si fournie), calcule un score de similarité
     de titre par token-overlap (difflib SequenceMatcher).
  3. Retourne la moyenne pondérée par score de similarité (poids min = 0.2).
  Fallbacks :
    - Si aucun cours similaire (score > seuil) dans la catégorie → moyenne
      globale de la catégorie.
    - Si pas de cours dans la catégorie avec heures → moyenne globale tous
      cours SCAP.
    - Si aucune donnée en base → None + raison.
"""

from __future__ import annotations

import logging
from difflib import SequenceMatcher
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.course import Course

logger = logging.getLogger(__name__)

# Score de similarité minimum pour qu'un cours soit considéré « similaire »
_MIN_SIMILARITY = 0.35
# Poids minimal appliqué à chaque cours retenu (évite poids nul)
_MIN_WEIGHT = 0.05
# Nombre max de cours de référence retournés dans `basis` (les plus similaires)
_MAX_BASIS = 5


def _token_overlap(a: str, b: str) -> float:
    """Score de similarité [0, 1] entre deux chaînes (insensible à la casse)."""
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()


def _weighted_mean(values: list[tuple[float, float]]) -> float:
    """Moyenne pondérée à partir de paires (valeur, poids)."""
    total_weight = sum(w for _, w in values)
    if total_weight == 0:
        return sum(v for v, _ in values) / len(values)
    return sum(v * w for v, w in values) / total_weight


async def estimate_hours(
    db: AsyncSession,
    title: str,
    category: str | None,
) -> dict[str, Any]:
    """
    Estime les heures d'un cours à partir des données SCAP.

    Returns
    -------
    dict avec :
      - estimated_hours : float | None
      - method : str (méthode utilisée)
      - basis : list[dict] (cours de référence utilisés)
      - reason : str | None (si estimation impossible)
    """
    try:
        result = await db.execute(
            select(Course).where(
                Course.status == "active",
                Course.hours_estimated.is_not(None),
            )
        )
        all_courses: list[Course] = list(result.scalars().all())
    except Exception as exc:
        logger.error("Erreur DB estimation_service : %s", exc)
        raise

    if not all_courses:
        return {
            "estimated_hours": None,
            "method": "none",
            "basis": [],
            "reason": "Aucune donnée de cours disponible en base.",
        }

    # --- Étape 1 : similarité titre dans la même catégorie ---
    same_cat = [
        c for c in all_courses
        if category and c.category and c.category.lower() == category.lower()
    ] if category else []

    pool_for_similarity = same_cat if same_cat else all_courses

    scored: list[tuple[Course, float]] = []
    for c in pool_for_similarity:
        sim = _token_overlap(title, c.title)
        if sim >= _MIN_SIMILARITY:
            scored.append((c, max(sim, _MIN_WEIGHT)))

    if scored:
        # Garde les N cours les plus similaires (référence bornée + cohérente avec `basis`)
        scored.sort(key=lambda cw: cw[1], reverse=True)
        scored = scored[:_MAX_BASIS]
        values = [(c.hours_estimated, w) for c, w in scored]  # type: ignore[misc]
        est = _weighted_mean(values)
        basis = [
            {
                "id": c.id,
                "title": c.title,
                "category": c.category,
                "hours_estimated": c.hours_estimated,
                "similarity": round(w, 3),
            }
            for c, w in scored
        ]
        method = "similarity_same_category" if same_cat else "similarity_all"
        return {
            "estimated_hours": round(est, 1),
            "method": method,
            "basis": basis,
            "reason": None,
        }

    # --- Fallback 1 : moyenne catégorie ---
    if same_cat:
        cat_hours = [c.hours_estimated for c in same_cat if c.hours_estimated is not None]
        if cat_hours:
            est = sum(cat_hours) / len(cat_hours)
            basis = [
                {"id": c.id, "title": c.title, "category": c.category,
                 "hours_estimated": c.hours_estimated, "similarity": None}
                for c in same_cat if c.hours_estimated is not None
            ][:_MAX_BASIS]
            return {
                "estimated_hours": round(est, 1),
                "method": "category_average",
                "basis": basis,
                "reason": None,
            }

    # --- Fallback 2 : moyenne globale ---
    global_hours = [c.hours_estimated for c in all_courses if c.hours_estimated is not None]
    if global_hours:
        est = sum(global_hours) / len(global_hours)
        basis = [
            {"id": c.id, "title": c.title, "category": c.category,
             "hours_estimated": c.hours_estimated, "similarity": None}
            for c in all_courses if c.hours_estimated is not None
        ][:_MAX_BASIS]
        return {
            "estimated_hours": round(est, 1),
            "method": "global_average",
            "basis": basis,
            "reason": None,
        }

    return {
        "estimated_hours": None,
        "method": "none",
        "basis": [],
        "reason": "Aucun cours avec heures renseignées disponible.",
    }
