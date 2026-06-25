"""Router scan_runs — historique des scans."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.security import get_current_user
from app.models.market_scan_run import MarketScanRun
from app.models.user import User
from app.schemas.market_scan_run import MarketScanRunList

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/scan-runs", tags=["Scans"])


@router.get("", response_model=list[MarketScanRunList])
async def list_scan_runs(
    school_id: int | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[MarketScanRun]:
    """Lister les scans, plus récents en premier."""
    stmt = select(MarketScanRun)
    if school_id is not None:
        stmt = stmt.where(MarketScanRun.school_registry_id == school_id)
    stmt = stmt.order_by(MarketScanRun.started_at.desc()).offset(skip).limit(limit)
    try:
        result = await db.execute(stmt)
        return list(result.scalars().all())
    except Exception as exc:
        logger.error("Erreur DB list_scan_runs : %s", exc)
        raise HTTPException(status_code=500, detail="Erreur serveur.")
