"""Service analytique — calcul du popularity_score et agrégations dashboard.

Formule popularity_score :
    score = enrolled_count - (dropout_count * 1.5)
    Normalisé sur [0, 100] par rapport au maximum de la liste analysée.
    Un score négatif brut est ramené à 0.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.course import Course

logger = logging.getLogger(__name__)

_DROPOUT_WEIGHT = 1.5


def compute_raw_score(enrolled: int, dropout: int) -> float:
    """Return the raw (non-normalised) popularity score."""
    return max(0.0, enrolled - dropout * _DROPOUT_WEIGHT)


async def refresh_all_scores(db: AsyncSession) -> int:
    """
    Recompute popularity_score for every active course.
    Returns number of updated rows.
    """
    try:
        result = await db.execute(
            select(Course).where(Course.status == "active")
        )
        courses: list[Course] = list(result.scalars().all())
    except Exception as exc:
        logger.error("Erreur DB lors du calcul des scores : %s", exc)
        raise

    if not courses:
        return 0

    raw_scores = [compute_raw_score(c.enrolled_count, c.dropout_count) for c in courses]
    max_raw = max(raw_scores) if raw_scores else 1.0
    if max_raw == 0:
        max_raw = 1.0  # avoid division by zero

    for course, raw in zip(courses, raw_scores):
        course.popularity_score = round(raw / max_raw * 100, 2)

    try:
        await db.flush()
    except Exception as exc:
        logger.error("Erreur DB lors de la sauvegarde des scores : %s", exc)
        raise

    return len(courses)


async def get_top_courses(
    db: AsyncSession, limit: int = 10
) -> list[dict[str, Any]]:
    """Return the *limit* most popular active courses."""
    try:
        result = await db.execute(
            select(Course)
            .where(Course.status == "active")
            .order_by(Course.popularity_score.desc().nulls_last())
            .limit(limit)
        )
        courses = list(result.scalars().all())
    except Exception as exc:
        logger.error("Erreur DB get_top_courses : %s", exc)
        raise

    return [
        {
            "id": c.id,
            "title": c.title,
            "category": c.category,
            "enrolled_count": c.enrolled_count,
            "dropout_count": c.dropout_count,
            "popularity_score": c.popularity_score,
        }
        for c in courses
    ]


async def get_flop_courses(
    db: AsyncSession, limit: int = 10
) -> list[dict[str, Any]]:
    """Return the *limit* least popular active courses."""
    try:
        result = await db.execute(
            select(Course)
            .where(Course.status == "active")
            .order_by(Course.popularity_score.asc().nulls_last())
            .limit(limit)
        )
        courses = list(result.scalars().all())
    except Exception as exc:
        logger.error("Erreur DB get_flop_courses : %s", exc)
        raise

    return [
        {
            "id": c.id,
            "title": c.title,
            "category": c.category,
            "enrolled_count": c.enrolled_count,
            "dropout_count": c.dropout_count,
            "popularity_score": c.popularity_score,
        }
        for c in courses
    ]
