"""Router audit_logs — consultation des logs (read-only, admin)."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.security import require_admin
from app.models.audit_log import AuditLog
from app.schemas.audit_log import AuditLogRead

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/audit-logs", tags=["Audit"])


@router.get("", response_model=list[AuditLogRead])
async def list_audit_logs(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=500),
    action_filter: str | None = Query(default=None, alias="action"),
    user_id: int | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _: object = Depends(require_admin),
) -> list[AuditLog]:
    """Lister les logs d'audit (admin seulement)."""
    stmt = select(AuditLog)

    if action_filter:
        stmt = stmt.where(AuditLog.action == action_filter)
    if user_id is not None:
        stmt = stmt.where(AuditLog.user_id == user_id)

    stmt = stmt.order_by(AuditLog.timestamp.desc()).offset(skip).limit(limit)

    try:
        result = await db.execute(stmt)
        return list(result.scalars().all())
    except Exception as exc:
        logger.error("Erreur DB list_audit_logs : %s", exc)
        raise HTTPException(status_code=500, detail="Erreur serveur.")
