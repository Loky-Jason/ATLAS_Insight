"""Router schools — CRUD établissements + scan + diff."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.security import get_current_user, require_admin
from app.models.audit_log import AuditLog
from app.models.school_registry import SchoolRegistry
from app.models.user import User
from app.schemas.school_registry import (
    SchoolRegistryCreate,
    SchoolRegistryList,
    SchoolRegistryRead,
    SchoolRegistryUpdate,
)
from app.scrapers import list_scrapers
from app.services import scanner_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/schools", tags=["Écoles"])


async def _get_school_or_404(school_id: int, db: AsyncSession) -> SchoolRegistry:
    try:
        school = await db.get(SchoolRegistry, school_id)
    except Exception as exc:
        logger.error("Erreur DB récupération school %s : %s", school_id, exc)
        raise HTTPException(status_code=500, detail="Erreur serveur.")
    if school is None:
        raise HTTPException(status_code=404, detail="École introuvable.")
    return school


async def _write_audit(
    db: AsyncSession, user_id: int, action: str, target: str
) -> None:
    try:
        log = AuditLog(user_id=user_id, action=action, target=target)
        db.add(log)
        await db.flush()
    except Exception as exc:
        logger.error("Erreur écriture AuditLog : %s", exc)


@router.get("", response_model=list[SchoolRegistryList])
async def list_schools(
    active: bool | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[SchoolRegistry]:
    """Lister les écoles. Filtre optionnel ?active=true/false."""
    stmt = select(SchoolRegistry).order_by(SchoolRegistry.name)
    if active is not None:
        stmt = stmt.where(SchoolRegistry.active == active)
    try:
        result = await db.execute(stmt)
        return list(result.scalars().all())
    except Exception as exc:
        logger.error("Erreur DB list_schools : %s", exc)
        raise HTTPException(status_code=500, detail="Erreur serveur.")


@router.get("/strategies", response_model=list[str])
async def list_scraper_strategies(
    _: User = Depends(get_current_user),
) -> list[str]:
    """Lister les stratégies de scraper disponibles (alimenté par @register_scraper)."""
    try:
        return sorted(list_scrapers())
    except Exception as exc:
        logger.error("Erreur list_scraper_strategies : %s", exc)
        raise HTTPException(status_code=500, detail="Erreur serveur.")


@router.post("", response_model=SchoolRegistryRead, status_code=status.HTTP_201_CREATED)
async def create_school(
    payload: SchoolRegistryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> SchoolRegistry:
    """Créer une nouvelle école (admin)."""
    school = SchoolRegistry(**payload.model_dump())
    try:
        db.add(school)
        await db.flush()
        await db.refresh(school)
    except Exception as exc:
        logger.error("Erreur DB create_school : %s", exc)
        raise HTTPException(status_code=500, detail="Erreur lors de la création.")
    await _write_audit(db, current_user.id, f"create_school:{school.id}", school.name)
    logger.info("École créée %s (id=%s) par user %s.", school.name, school.id, current_user.id)
    return school


@router.get("/{school_id}", response_model=SchoolRegistryRead)
async def get_school(
    school_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> SchoolRegistry:
    """Récupérer une école par son identifiant."""
    return await _get_school_or_404(school_id, db)


@router.patch("/{school_id}", response_model=SchoolRegistryRead)
async def update_school(
    school_id: int,
    payload: SchoolRegistryUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> SchoolRegistry:
    """Mettre à jour partiellement une école (admin)."""
    school = await _get_school_or_404(school_id, db)
    update_data = payload.model_dump(exclude_unset=True)
    for key, val in update_data.items():
        setattr(school, key, val)
    try:
        await db.flush()
        await db.refresh(school)
    except Exception as exc:
        logger.error("Erreur DB update_school %s : %s", school_id, exc)
        raise HTTPException(status_code=500, detail="Erreur lors de la mise à jour.")
    await _write_audit(db, current_user.id, f"update_school:{school.id}", school.name)
    logger.info("École %s mise à jour par user %s.", school_id, current_user.id)
    return school


@router.delete("/{school_id}")
async def delete_school(
    school_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> Response:
    """Supprimer une école (admin)."""
    school = await _get_school_or_404(school_id, db)
    await _write_audit(db, current_user.id, f"delete_school:{school.id}", school.name)
    try:
        await db.delete(school)
        await db.flush()
    except Exception as exc:
        logger.error("Erreur DB delete_school %s : %s", school_id, exc)
        raise HTTPException(status_code=500, detail="Erreur lors de la suppression.")
    logger.info("École %s supprimée par user %s.", school.name, current_user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{school_id}/scan")
async def trigger_scan(
    school_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> dict[str, Any]:
    """Déclencher un scan pour une école (admin)."""
    school = await _get_school_or_404(school_id, db)
    await _write_audit(db, current_user.id, f"scan_school:{school_id}", school.name)
    try:
        summary = await scanner_service.run_school_scan(db, school_id, current_user.id)
    except Exception as exc:
        logger.error("Erreur scan school %s : %s", school_id, exc)
        raise HTTPException(status_code=500, detail="Erreur lors du scan.")
    return summary


@router.get("/{school_id}/diff")
async def get_school_diff(
    school_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Récupérer le dernier diff de scan pour une école."""
    await _get_school_or_404(school_id, db)
    try:
        diff = await scanner_service.get_school_diff(db, school_id)
    except Exception as exc:
        logger.error("Erreur get_school_diff %s : %s", school_id, exc)
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération du diff.")
    return diff
