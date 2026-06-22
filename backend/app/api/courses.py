"""Router courses — CRUD, archivage soft-delete, filtre/recherche."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.security import get_current_user, require_admin
from app.models.audit_log import AuditLog
from app.models.course import Course
from app.models.user import User
from app.schemas.course import CourseCreate, CourseRead, CourseUpdate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/courses", tags=["Cours"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _get_course_or_404(course_id: int, db: AsyncSession) -> Course:
    try:
        result = await db.execute(select(Course).where(Course.id == course_id))
        course = result.scalar_one_or_none()
    except Exception as exc:
        logger.error("Erreur DB récupération cours %s : %s", course_id, exc)
        raise HTTPException(status_code=500, detail="Erreur serveur.")
    if course is None:
        raise HTTPException(status_code=404, detail="Cours introuvable.")
    return course


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

@router.get("", response_model=list[CourseRead])
async def list_courses(
    status_filter: str | None = Query(default=None, alias="status"),
    category: str | None = Query(default=None),
    search: str | None = Query(default=None, description="Recherche dans le titre"),
    year: int | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[Course]:
    """Lister les cours avec filtres optionnels."""
    stmt = select(Course)

    if status_filter:
        stmt = stmt.where(Course.status == status_filter)
    if category:
        stmt = stmt.where(Course.category == category)
    if year:
        stmt = stmt.where(Course.year == year)
    if search:
        stmt = stmt.where(Course.title.ilike(f"%{search}%"))

    stmt = stmt.order_by(Course.created_at.desc())

    try:
        result = await db.execute(stmt)
        return list(result.scalars().all())
    except Exception as exc:
        logger.error("Erreur DB list_courses : %s", exc)
        raise HTTPException(status_code=500, detail="Erreur serveur.")


@router.post("", response_model=CourseRead, status_code=status.HTTP_201_CREATED)
async def create_course(
    payload: CourseCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Course:
    """Créer un nouveau cours."""
    course = Course(**payload.model_dump())
    try:
        db.add(course)
        await db.flush()
        await db.refresh(course)
    except Exception as exc:
        logger.error("Erreur DB create_course : %s", exc)
        raise HTTPException(status_code=500, detail="Erreur lors de la création du cours.")
    return course


@router.get("/{course_id}", response_model=CourseRead)
async def get_course(
    course_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> Course:
    """Récupérer un cours par son identifiant."""
    return await _get_course_or_404(course_id, db)


@router.patch("/{course_id}", response_model=CourseRead)
async def update_course(
    course_id: int,
    payload: CourseUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Course:
    """Mettre à jour partiellement un cours."""
    course = await _get_course_or_404(course_id, db)
    update_data = payload.model_dump(exclude_unset=True)
    for key, val in update_data.items():
        setattr(course, key, val)
    try:
        await db.flush()
        await db.refresh(course)
    except Exception as exc:
        logger.error("Erreur DB update_course %s : %s", course_id, exc)
        raise HTTPException(status_code=500, detail="Erreur lors de la mise à jour.")
    return course


@router.post("/{course_id}/archive", response_model=CourseRead)
async def archive_course(
    course_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> Course:
    """Archiver un cours (soft-delete : status → archived)."""
    course = await _get_course_or_404(course_id, db)
    course.status = "archived"
    await _write_audit(db, current_user.id, "archive_course", f"course:{course_id}")
    try:
        await db.flush()
        await db.refresh(course)
    except Exception as exc:
        logger.error("Erreur DB archive_course %s : %s", course_id, exc)
        raise HTTPException(status_code=500, detail="Erreur lors de l'archivage.")
    logger.info("Cours %s archivé par user %s.", course_id, current_user.id)
    return course


@router.post("/{course_id}/restore", response_model=CourseRead)
async def restore_course(
    course_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> Course:
    """Restaurer un cours archivé (status → active)."""
    course = await _get_course_or_404(course_id, db)
    course.status = "active"
    await _write_audit(db, current_user.id, "restore_course", f"course:{course_id}")
    try:
        await db.flush()
        await db.refresh(course)
    except Exception as exc:
        logger.error("Erreur DB restore_course %s : %s", course_id, exc)
        raise HTTPException(status_code=500, detail="Erreur lors de la restauration.")
    return course
