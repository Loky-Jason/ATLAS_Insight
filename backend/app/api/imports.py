"""Router imports — upload Excel/CSV et insertion en base."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.security import get_current_user
from app.models.audit_log import AuditLog
from app.models.course import Course
from app.models.user import User
from app.services.import_service import parse_upload

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/imports", tags=["Import"])

_MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MiB
_ALLOWED_EXTENSIONS = {".xlsx", ".xls", ".csv"}
_ALLOWED_CONTENT_TYPES = {
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-excel",
    "text/csv",
    "text/plain",
    "application/octet-stream",  # navigateurs moins stricts
}


@router.post("", status_code=status.HTTP_200_OK)
async def import_courses(
    file: UploadFile = File(..., description="Fichier Excel (.xlsx/.xls) ou CSV"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Importer des cours depuis un fichier Excel ou CSV.

    Retourne un résumé : nombre de lignes insérées, erreurs éventuelles.
    """
    # --- Validation du type de fichier ---
    filename = file.filename or "upload"
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in _ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Extension '{ext}' non supportée. Formats acceptés : xlsx, xls, csv.",
        )

    # --- Lecture bornée : on lit par chunks pour rejeter AVANT d'allouer tout en RAM (E3a) ---
    _CHUNK = 64 * 1024  # 64 KiB
    chunks: list[bytes] = []
    total = 0
    try:
        while True:
            chunk = await file.read(_CHUNK)
            if not chunk:
                break
            total += len(chunk)
            if total > _MAX_FILE_SIZE:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail="Fichier trop volumineux (max 10 Mo).",
                )
            chunks.append(chunk)
        content = b"".join(chunks)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Erreur lecture fichier upload : %s", exc)
        raise HTTPException(status_code=500, detail="Impossible de lire le fichier.")

    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Le fichier est vide.",
        )

    # --- Parse ---
    try:
        rows, parse_errors = parse_upload(content, filename)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )
    except Exception as exc:
        logger.error("Erreur inattendue parse_upload : %s", exc)
        raise HTTPException(status_code=500, detail="Erreur lors de l'analyse du fichier.")

    if not rows:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Aucune ligne valide trouvée dans le fichier.",
        )

    # --- Insertion en base ---
    inserted = 0
    db_errors: list[str] = []
    for row in rows:
        try:
            course = Course(**row)
            db.add(course)
            inserted += 1
        except Exception as exc:
            # F2 : message générique côté client, détail complet uniquement en log
            logger.warning("Erreur insertion cours '%s' : %s", row.get("title", "?"), exc)
            db_errors.append(f"Impossible d'insérer le cours '{row.get('title', '?')}'.")

    try:
        await db.flush()
    except Exception as exc:
        logger.error("Erreur DB flush import : %s", exc)
        raise HTTPException(status_code=500, detail="Erreur lors de l'enregistrement en base.")

    # AuditLog — traçabilité de l'import (M1)
    try:
        audit = AuditLog(
            user_id=current_user.id,
            action="import_courses",
            target=f"file:{filename} rows:{inserted}",
        )
        db.add(audit)
        await db.flush()
    except Exception as exc:
        logger.error("Erreur écriture AuditLog import : %s", exc)

    logger.info(
        "Import fichier '%s' par user %s : %d insérés, %d erreurs.",
        filename,
        current_user.id,
        inserted,
        len(parse_errors) + len(db_errors),
    )

    return {
        "inserted": inserted,
        "errors": parse_errors + db_errors,
        "filename": filename,
    }
