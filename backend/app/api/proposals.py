"""Router proposals — CRUD propositions de formation."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.security import get_current_user, require_admin
from app.models.audit_log import AuditLog
from app.models.course_proposal import CourseProposal
from app.models.user import User
from app.schemas.course_proposal import CourseProposalCreate, CourseProposalRead, CourseProposalUpdate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/proposals", tags=["Propositions"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _get_proposal_or_404(proposal_id: int, db: AsyncSession) -> CourseProposal:
    try:
        result = await db.execute(select(CourseProposal).where(CourseProposal.id == proposal_id))
        proposal = result.scalar_one_or_none()
    except Exception as exc:
        logger.error("Erreur DB récupération proposal %s : %s", proposal_id, exc)
        raise HTTPException(status_code=500, detail="Erreur serveur.")
    if proposal is None:
        raise HTTPException(status_code=404, detail="Proposition introuvable.")
    return proposal


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


@router.get("", response_model=list[CourseProposalRead])
async def list_proposals(
    status_filter: str | None = Query(default=None, alias="status"),
    search: str | None = Query(default=None, description="Recherche dans le titre"),
    db: AsyncSession = Depends(get_db),
) -> list[CourseProposal]:
    """Lister les propositions de formation avec filtres optionnels."""
    stmt = select(CourseProposal)

    if status_filter:
        stmt = stmt.where(CourseProposal.status == status_filter)
    if search:
        stmt = stmt.where(CourseProposal.title.ilike(f"%{search}%"))

    stmt = stmt.order_by(CourseProposal.created_at.desc())

    try:
        result = await db.execute(stmt)
        return list(result.scalars().all())
    except Exception as exc:
        logger.error("Erreur DB list_proposals : %s", exc)
        raise HTTPException(status_code=500, detail="Erreur serveur.")


@router.post("", response_model=CourseProposalRead, status_code=status.HTTP_201_CREATED)
async def create_proposal(
    payload: CourseProposalCreate,
    db: AsyncSession = Depends(get_db),
) -> CourseProposal:
    """Créer une nouvelle proposition de formation."""
    proposal = CourseProposal(**payload.model_dump())
    try:
        db.add(proposal)
        await db.flush()
        await db.refresh(proposal)
    except Exception as exc:
        logger.error("Erreur DB create_proposal : %s", exc)
        raise HTTPException(status_code=500, detail="Erreur lors de la création.")
    return proposal


@router.get("/{proposal_id}", response_model=CourseProposalRead)
async def get_proposal(
    proposal_id: int,
    db: AsyncSession = Depends(get_db),
) -> CourseProposal:
    """Récupérer une proposition par son identifiant."""
    return await _get_proposal_or_404(proposal_id, db)


@router.patch("/{proposal_id}", response_model=CourseProposalRead)
async def update_proposal(
    proposal_id: int,
    payload: CourseProposalUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CourseProposal:
    """Mettre à jour partiellement une proposition."""
    proposal = await _get_proposal_or_404(proposal_id, db)
    update_data = payload.model_dump(exclude_unset=True)
    for key, val in update_data.items():
        setattr(proposal, key, val)
    try:
        await db.flush()
        await db.refresh(proposal)
    except Exception as exc:
        logger.error("Erreur DB update_proposal %s : %s", proposal_id, exc)
        raise HTTPException(status_code=500, detail="Erreur lors de la mise à jour.")
    return proposal


@router.delete("/{proposal_id}")
async def delete_proposal(
    proposal_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> Response:
    """Supprimer une proposition (admin seulement)."""
    proposal = await _get_proposal_or_404(proposal_id, db)
    await _write_audit(db, current_user.id, "delete_proposal", f"proposal:{proposal_id}")
    try:
        await db.delete(proposal)
        await db.flush()
    except Exception as exc:
        logger.error("Erreur DB delete_proposal %s : %s", proposal_id, exc)
        raise HTTPException(status_code=500, detail="Erreur lors de la suppression.")
    logger.info("Proposal %s supprimé par user %s.", proposal_id, current_user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
