"""Router estimation — estimation d'heures par similarité sur les cours SCAP."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.services.estimation_service import estimate_hours

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/estimate", tags=["Estimation"])


# ---------------------------------------------------------------------------
# Schémas
# ---------------------------------------------------------------------------

class EstimateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=512, description="Titre du cours à estimer")
    category: str | None = Field(default=None, max_length=255, description="Catégorie du cours")


class CourseBasisItem(BaseModel):
    id: int
    title: str
    category: str | None
    hours_estimated: float | None
    similarity: float | None


class EstimateResponse(BaseModel):
    estimated_hours: float | None
    method: str
    basis: list[CourseBasisItem]
    reason: str | None


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.post(
    "/hours",
    response_model=EstimateResponse,
    summary="Estimer le nombre d'heures d'un cours par similarité",
)
async def estimate_course_hours(
    payload: EstimateRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> Any:
    """
    Estime les heures d'un cours proposé par comparaison avec les cours SCAP existants.

    Méthode :
      1. Similarité de titre (token overlap) dans la même catégorie.
      2. Fallback : moyenne catégorie.
      3. Fallback : moyenne globale.
      4. Si aucune donnée : `estimated_hours` = null + raison.
    """
    try:
        result = await estimate_hours(db, title=payload.title, category=payload.category)
    except Exception as exc:
        logger.error("Erreur estimation heures : %s", exc)
        raise HTTPException(status_code=500, detail="Erreur lors de l'estimation.")

    return result
