"""Router school_courses — consultation cours bruts par école."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.security import get_current_user
from app.models.school_course import SchoolCourse
from app.models.user import User
from app.schemas.school_course import SchoolCourseList

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/school-courses", tags=["Cours bruts"])


@router.get("", response_model=list[SchoolCourseList])
async def list_school_courses(
    school_id: int | None = Query(default=None),
    is_removed: bool | None = Query(default=None),
    q: str | None = Query(default=None, description="Recherche dans le titre"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[SchoolCourse]:
    """Lister les cours bruts avec filtres et pagination."""
    stmt = select(SchoolCourse)

    if school_id is not None:
        stmt = stmt.where(SchoolCourse.school_registry_id == school_id)
    if is_removed is not None:
        stmt = stmt.where(SchoolCourse.is_removed == is_removed)
    if q:
        stmt = stmt.where(SchoolCourse.title.ilike(f"%{q}%"))

    stmt = stmt.order_by(SchoolCourse.last_seen_at.desc()).offset(skip).limit(limit)

    try:
        result = await db.execute(stmt)
        return list(result.scalars().all())
    except Exception as exc:
        logger.error("Erreur DB list_school_courses : %s", exc)
        raise HTTPException(status_code=500, detail="Erreur serveur.")
