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
from app.services.export_service import build_proposal_filename, render_proposal_pdf

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/export", tags=["Export"])


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

    try:
        pdf_bytes = render_proposal_pdf(proposal)
    except RuntimeError as exc:
        logger.error("Export PDF impossible pour %s : %s", proposal_id, exc)
        raise HTTPException(status_code=500, detail="Échec de la génération du PDF.")

    # Sortie de données : tracée, comme les autres actions non destructives du projet.
    try:
        db.add(
            AuditLog(
                user_id=current_user.id,
                action="export_proposal",
                target=f"course_proposal:{proposal_id}",
            )
        )
        await db.flush()
    except Exception as exc:
        logger.error("Erreur écriture AuditLog export %s : %s", proposal_id, exc)

    filename = build_proposal_filename(proposal)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
