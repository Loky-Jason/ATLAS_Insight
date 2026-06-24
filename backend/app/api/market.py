"""Router market — déclenchement de la veille marché (admin only)."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.security import require_admin
from app.models.audit_log import AuditLog
from app.models.user import User
from app.services.market_service import run_market_scan

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/market", tags=["Veille marché — scan"])


# ---------------------------------------------------------------------------
# Schémas
# ---------------------------------------------------------------------------

class MarketScanResultItem(BaseModel):
    title: str
    school: str | None
    source_url: str | None
    relevance_score: float
    why_it_works: str | None


class MarketScanResponse(BaseModel):
    inserted: int
    skipped: int
    provider: str
    results: list[MarketScanResultItem]
    message: str


# ---------------------------------------------------------------------------
# Helper audit
# ---------------------------------------------------------------------------

async def _write_audit(db: AsyncSession, user_id: int, action: str, target: str) -> None:
    try:
        log = AuditLog(user_id=user_id, action=action, target=target)
        db.add(log)
        await db.flush()
    except Exception as exc:
        logger.error("Erreur écriture AuditLog (market scan) : %s", exc)


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.post(
    "/scan",
    response_model=MarketScanResponse,
    summary="Déclencher une veille marché (admin)",
    status_code=201,
)
async def trigger_market_scan(
    query: str = Query(
        default="formations professionnelles Paris 2025",
        min_length=3,
        max_length=512,
        description="Termes de recherche transmis au provider de veille",
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> Any:
    """
    Déclenche un scan de veille marché via le provider configuré (Stub par défaut).

    - Insère les nouvelles formations trouvées comme MarketCourse (status=candidate).
    - Ignore les doublons (même titre déjà présent).
    - Calcule un score de pertinence vs le catalogue SCAP existant.
    - Journalise l'action dans AuditLog.

    NOTE : Le provider Stub renvoie des données déterministes de démonstration.
    Pour une recherche web réelle, brancher un MarketSearchProvider concret
    dans `app/services/market_service.py` → `get_market_provider()`.
    """
    try:
        result = await run_market_scan(db, user_id=current_user.id, query=query)
    except Exception as exc:
        logger.error("Erreur scan marché : %s", exc)
        raise HTTPException(status_code=500, detail="Erreur lors du scan marché.")

    await _write_audit(
        db,
        user_id=current_user.id,
        action="market_scan",
        target=f"query='{query}' inserted={result['inserted']} skipped={result['skipped']}",
    )

    return {
        **result,
        "message": (
            f"{result['inserted']} formation(s) insérée(s), "
            f"{result['skipped']} ignorée(s) (doublons). "
            f"Provider : {result['provider']}."
        ),
    }
