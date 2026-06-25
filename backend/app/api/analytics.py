"""Router analytics — popularité, top/flop, recalcul des scores."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.security import get_current_user, require_admin
from app.models.user import User
from app.services.analytics_service import (
    get_flop_courses,
    get_top_courses,
    get_totals,
    refresh_all_scores,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["Analytique"])


@router.get("/popularity", summary="Top et flop des cours par popularité")
async def get_popularity(
    limit: int = Query(default=10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Retourne les *limit* cours les plus populaires et les *limit* moins populaires.

    Formule : score = inscrits − (désistements × 1.5), normalisé sur [0, 100].
    """
    most_popular = await get_top_courses(db, limit=limit)
    least_popular = await get_flop_courses(db, limit=limit)
    totals = await get_totals(db)
    return {"most_popular": most_popular, "least_popular": least_popular, **totals}


@router.post(
    "/refresh-scores",
    summary="Recalculer les scores de popularité",
    status_code=200,
)
async def refresh_scores(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
) -> dict[str, Any]:
    """
    Recalcule et sauvegarde le popularity_score de tous les cours actifs.
    À appeler après un import ou une mise à jour de données.
    """
    updated = await refresh_all_scores(db)
    logger.info("Scores recalculés : %d cours mis à jour.", updated)
    return {"updated": updated, "message": f"{updated} cours mis à jour."}
