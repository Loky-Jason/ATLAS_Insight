"""Router export — génération de documents à partir des propositions de cours."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.security import get_current_user
from app.models.audit_log import AuditLog
from app.models.course_proposal import CourseProposal
from app.models.user import User
from app.services.export_service import (
    build_proposal_filename,
    render_proposal_docx,
    render_proposal_pdf,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/export", tags=["Export"])

DOCX_MEDIA_TYPE = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)


async def _load_proposal(proposal_id: int, db: AsyncSession) -> CourseProposal:
    try:
        result = await db.execute(
            select(CourseProposal).where(CourseProposal.id == proposal_id)
        )
        proposal = result.scalar_one_or_none()
    except Exception as exc:
        logger.error("Erreur DB export proposition %s : %s", proposal_id, exc)
        raise HTTPException(status_code=500, detail="Erreur serveur.")

    if proposal is None:
        raise HTTPException(status_code=404, detail="Proposition introuvable.")
    return proposal


async def _trace_export(
    db: AsyncSession, user_id: int, action: str, proposal_id: int
) -> None:
    """Trace la sortie de données ; un échec de journalisation ne bloque pas l'export."""
    try:
        db.add(
            AuditLog(
                user_id=user_id,
                action=action,
                target=f"course_proposal:{proposal_id}",
            )
        )
        await db.flush()
    except Exception as exc:
        logger.error("Erreur écriture AuditLog export %s : %s", proposal_id, exc)


def _attachment(content: bytes, media_type: str, filename: str) -> Response:
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/proposals/{proposal_id}.pdf",
    response_class=Response,
    responses={200: {"content": {"application/pdf": {}}}},
)
async def export_proposal_pdf(
    proposal_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    """Exporter une proposition de cours en PDF.

    Méthode sûre : ne modifie pas la proposition. Le passage au statut
    `exported` reste une action explicite de l'utilisateur — muter un état
    métier sur un GET casserait l'idempotence.
    """
    proposal = await _load_proposal(proposal_id, db)

    try:
        pdf_bytes = render_proposal_pdf(proposal)
    except RuntimeError as exc:
        logger.error("Export PDF impossible pour %s : %s", proposal_id, exc)
        raise HTTPException(status_code=500, detail="Échec de la génération du PDF.")

    # Sortie de données : tracée, comme les autres actions non destructives du projet.
    await _trace_export(db, current_user.id, "export_proposal_pdf", proposal_id)

    return _attachment(
        pdf_bytes, "application/pdf", build_proposal_filename(proposal, "pdf")
    )


@router.get(
    "/proposals/{proposal_id}.docx",
    response_class=Response,
    responses={200: {"content": {DOCX_MEDIA_TYPE: {}}}},
)
async def export_proposal_docx(
    proposal_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    """Exporter une proposition de cours en document Word éditable.

    Même contenu que le PDF (source unique `build_proposal_content`), même
    méthode sûre : aucune modification de la proposition.
    """
    proposal = await _load_proposal(proposal_id, db)

    try:
        docx_bytes = render_proposal_docx(proposal)
    except RuntimeError as exc:
        logger.error("Export Word impossible pour %s : %s", proposal_id, exc)
        raise HTTPException(
            status_code=500, detail="Échec de la génération du document Word."
        )

    await _trace_export(db, current_user.id, "export_proposal_docx", proposal_id)

    return _attachment(
        docx_bytes, DOCX_MEDIA_TYPE, build_proposal_filename(proposal, "docx")
    )
