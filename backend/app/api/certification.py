"""Router certification — suggestions RNCP / open badge / certificat interne."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.services.certification_service import suggest_certifications

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/certification", tags=["Certification"])


# ---------------------------------------------------------------------------
# Schémas
# ---------------------------------------------------------------------------

class CertificationRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=512)
    category: str | None = Field(default=None, max_length=255)
    hours: float | None = Field(default=None, ge=0.0, description="Durée estimée en heures")


class CertificationSuggestion(BaseModel):
    type: str          # rncp | open_badge | internal
    label: str
    rationale: str
    confidence: float  # [0, 1]


class CertificationResponse(BaseModel):
    suggestions: list[CertificationSuggestion]
    total: int


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.post(
    "/suggest",
    response_model=CertificationResponse,
    summary="Suggestions de certification pour un cours proposé",
)
async def suggest_course_certifications(
    payload: CertificationRequest,
    _db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> Any:
    """
    Propose des pistes de certification (RNCP, open badge, certificat interne SCAP)
    à partir du titre, de la catégorie et de la durée d'un cours.

    Le référentiel de règles est embarqué dans le service (pas d'appel externe).
    Résultats triés par confiance décroissante.
    """
    try:
        suggestions = suggest_certifications(
            title=payload.title,
            category=payload.category,
            hours=payload.hours,
        )
    except Exception as exc:
        logger.error("Erreur service certification : %s", exc)
        raise HTTPException(status_code=500, detail="Erreur lors des suggestions de certification.")

    return {"suggestions": suggestions, "total": len(suggestions)}
