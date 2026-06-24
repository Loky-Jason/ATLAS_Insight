"""Router market_courses — CRUD veille marché."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.security import get_current_user, require_admin
from app.models.audit_log import AuditLog
from app.models.market_course import MarketCourse
from app.models.user import User
from app.schemas.market_course import MarketCourseCreate, MarketCourseRead, MarketCourseUpdate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/market-courses", tags=["Veille marché"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _get_market_course_or_404(market_course_id: int, db: AsyncSession) -> MarketCourse:
    try:
        result = await db.execute(select(MarketCourse).where(MarketCourse.id == market_course_id))
        mc = result.scalar_one_or_none()
    except Exception as exc:
        logger.error("Erreur DB récupération market_course %s : %s", market_course_id, exc)
        raise HTTPException(status_code=500, detail="Erreur serveur.")
    if mc is None:
        raise HTTPException(status_code=404, detail="Formation marché introuvable.")
    return mc


async def _write_audit(
    db: AsyncSession, user_id: int, action: str, target: str
) -> None:
    try:
        log = AuditLog(user_id=user_id, action=action, target=target)
        db.add(log)
        await db.flush()
    except Exception as exc:
        logger.error("Erreur écriture AuditLog : %s", exc)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("", response_model=list[MarketCourseRead])
async def list_market_courses(
    status_filter: str | None = Query(default=None, alias="status"),
    school: str | None = Query(default=None),
    search: str | None = Query(default=None, description="Recherche dans le titre"),
    min_relevance_score: float | None = Query(default=None, ge=0.0, le=1.0),
    db: AsyncSession = Depends(get_db),
) -> list[MarketCourse]:
    """Lister les formations du marché avec filtres optionnels."""
    stmt = select(MarketCourse)

    if status_filter:
        stmt = stmt.where(MarketCourse.status == status_filter)
    if school:
        stmt = stmt.where(MarketCourse.school.ilike(f"%{school}%"))
    if search:
        stmt = stmt.where(MarketCourse.title.ilike(f"%{search}%"))
    if min_relevance_score is not None:
        stmt = stmt.where(MarketCourse.relevance_score >= min_relevance_score)

    stmt = stmt.order_by(MarketCourse.discovered_at.desc())

    try:
        result = await db.execute(stmt)
        return list(result.scalars().all())
    except Exception as exc:
        logger.error("Erreur DB list_market_courses : %s", exc)
        raise HTTPException(status_code=500, detail="Erreur serveur.")


@router.post("", response_model=MarketCourseRead, status_code=status.HTTP_201_CREATED)
async def create_market_course(
    payload: MarketCourseCreate,
    db: AsyncSession = Depends(get_db),
) -> MarketCourse:
    """Créer une nouvelle formation issue de la veille marché."""
    mc = MarketCourse(**payload.model_dump())
    try:
        db.add(mc)
        await db.flush()
        await db.refresh(mc)
    except Exception as exc:
        logger.error("Erreur DB create_market_course : %s", exc)
        raise HTTPException(status_code=500, detail="Erreur lors de la création.")
    return mc


@router.get("/{market_course_id}", response_model=MarketCourseRead)
async def get_market_course(
    market_course_id: int,
    db: AsyncSession = Depends(get_db),
) -> MarketCourse:
    """Récupérer une formation marché par son identifiant."""
    return await _get_market_course_or_404(market_course_id, db)


@router.patch("/{market_course_id}", response_model=MarketCourseRead)
async def update_market_course(
    market_course_id: int,
    payload: MarketCourseUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MarketCourse:
    """Mettre à jour partiellement une formation marché."""
    mc = await _get_market_course_or_404(market_course_id, db)
    update_data = payload.model_dump(exclude_unset=True)
    for key, val in update_data.items():
        setattr(mc, key, val)
    try:
        await db.flush()
        await db.refresh(mc)
    except Exception as exc:
        logger.error("Erreur DB update_market_course %s : %s", market_course_id, exc)
        raise HTTPException(status_code=500, detail="Erreur lors de la mise à jour.")
    return mc


@router.delete("/{market_course_id}")
async def delete_market_course(
    market_course_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> Response:
    """Supprimer une formation marché (admin seulement)."""
    mc = await _get_market_course_or_404(market_course_id, db)
    await _write_audit(db, current_user.id, "delete_market_course", f"market_course:{market_course_id}")
    try:
        await db.delete(mc)
        await db.flush()
    except Exception as exc:
        logger.error("Erreur DB delete_market_course %s : %s", market_course_id, exc)
        raise HTTPException(status_code=500, detail="Erreur lors de la suppression.")
    logger.info("MarketCourse %s supprimé par user %s.", market_course_id, current_user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
