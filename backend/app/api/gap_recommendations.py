"""Router gap recommendations — analyse d'écarts marché/offre."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.security import get_current_user, require_admin
from app.models.audit_log import AuditLog
from app.models.gap_recommendation import GapRecommendation
from app.models.user import User
from app.schemas.gap_recommendation import GapRecommendationList, GapRecommendationRead
from app.services import gap_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/gap-recommendations", tags=["Recommandations"])


@router.get("", response_model=list[GapRecommendationList])
async def list_recommendations(
    recommendation_type: str | None = Query(
        default=None, alias="type", pattern=r"^(closure|creation)$"
    ),
    status_filter: str | None = Query(
        default=None, alias="status", pattern=r"^(draft|approved)$"
    ),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[GapRecommendation]:
    """Lister les recommandations. Filtres : type, status, pagination."""
    stmt = select(GapRecommendation).order_by(GapRecommendation.score.desc())
    if recommendation_type is not None:
        stmt = stmt.where(
            GapRecommendation.recommendation_type == recommendation_type
        )
    if status_filter is not None:
        stmt = stmt.where(GapRecommendation.status == status_filter)
    stmt = stmt.offset(skip).limit(limit)
    try:
        result = await db.execute(stmt)
        return list(result.scalars().all())
    except Exception as exc:
        logger.error("Erreur list_recommendations : %s", exc)
        raise HTTPException(status_code=500, detail="Erreur serveur.")


@router.get("/closure-candidates", response_model=list[GapRecommendationRead])
async def closure_candidates(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[GapRecommendation]:
    """Recommandations de fermeture de cours."""
    try:
        return await gap_service.get_closure_candidates(db)
    except Exception as exc:
        logger.error("Erreur closure_candidates : %s", exc)
        raise HTTPException(status_code=500, detail="Erreur serveur.")


@router.get("/creation-suggestions", response_model=list[GapRecommendationRead])
async def creation_suggestions(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[GapRecommendation]:
    """Suggestions de création de cours."""
    try:
        return await gap_service.get_creation_suggestions(db)
    except Exception as exc:
        logger.error("Erreur creation_suggestions : %s", exc)
        raise HTTPException(status_code=500, detail="Erreur serveur.")


@router.post("/analyze", status_code=status.HTTP_201_CREATED)
async def trigger_analysis(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> dict[str, Any]:
    """Déclencher une analyse complète des écarts (admin)."""
    try:
        summary = await gap_service.run_gap_analysis(db, current_user.id)
        db.add(
            AuditLog(
                user_id=current_user.id,
                action="run_gap_analysis",
                target="gap_recommendations",
            )
        )
        await db.flush()
    except Exception as exc:
        logger.error("Erreur gap analysis : %s", exc)
        raise HTTPException(status_code=500, detail="Erreur lors de l'analyse.")
    return summary


@router.get("/{rec_id}", response_model=GapRecommendationRead)
async def get_recommendation(
    rec_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> GapRecommendation:
    """Détail d'une recommandation."""
    stmt = select(GapRecommendation).where(GapRecommendation.id == rec_id)
    try:
        result = await db.execute(stmt)
        rec = result.scalar_one_or_none()
    except SQLAlchemyError as exc:
        logger.error("Erreur DB get_recommendation %s : %s", rec_id, exc)
        raise HTTPException(status_code=500, detail="Erreur serveur.")
    if not rec:
        raise HTTPException(status_code=404, detail="Recommandation introuvable.")
    return rec


@router.post("/{rec_id}/approve")
async def approve_recommendation(
    rec_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> dict[str, Any]:
    """Approuver une recommandation (admin)."""
    try:
        result = await gap_service.approve_recommendation(db, rec_id, current_user.id)
    except ValueError as exc:
        detail = str(exc)
        status_code = 404 if "introuvable" in detail else 409
        raise HTTPException(status_code=status_code, detail=detail)
    except Exception as exc:
        logger.error("Erreur approve_recommendation %s : %s", rec_id, exc)
        raise HTTPException(status_code=500, detail="Erreur serveur.")
    return result


@router.post("/{rec_id}/reject")
async def reject_recommendation(
    rec_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> dict[str, Any]:
    """Rejeter une recommandation (admin)."""
    try:
        result = await gap_service.reject_recommendation(db, rec_id, current_user.id)
    except ValueError as exc:
        detail = str(exc)
        status_code = 404 if "introuvable" in detail else 409
        raise HTTPException(status_code=status_code, detail=detail)
    except Exception as exc:
        logger.error("Erreur reject_recommendation %s : %s", rec_id, exc)
        raise HTTPException(status_code=500, detail="Erreur serveur.")
    return result
