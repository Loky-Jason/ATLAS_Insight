"""Router dashboard — métriques et compteurs pour le tableau de bord."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.services import gap_service, scanner_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dashboard", tags=["Tableau de bord"])


@router.get("/counts")
async def get_dashboard_counts(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Retourne les compteurs pour les badges de navigation."""
    try:
        counts = await scanner_service.get_dashboard_counts(db)
    except Exception as exc:
        logger.error("Erreur get_dashboard_counts : %s", exc)
        raise HTTPException(status_code=500, detail="Erreur serveur.")

    try:
        closure = await gap_service.get_closure_candidates(db)
        creation = await gap_service.get_creation_suggestions(db)
        counts["closure_candidates"] = len(closure)
        counts["creation_suggestions"] = len(creation)
    except Exception as exc:
        logger.error("Erreur récupération gap counts : %s", exc)

    return counts
