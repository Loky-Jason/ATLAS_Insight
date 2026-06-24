"""Router favorites — CRUD favoris utilisateur."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.security import get_current_user, require_admin
from app.models.favorite import Favorite
from app.models.user import User
from app.schemas.favorite import FavoriteCreate, FavoriteRead

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/favorites", tags=["Favoris"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _get_favorite_or_404(favorite_id: int, db: AsyncSession) -> Favorite:
    try:
        result = await db.execute(select(Favorite).where(Favorite.id == favorite_id))
        fav = result.scalar_one_or_none()
    except Exception as exc:
        logger.error("Erreur DB récupération favorite %s : %s", favorite_id, exc)
        raise HTTPException(status_code=500, detail="Erreur serveur.")
    if fav is None:
        raise HTTPException(status_code=404, detail="Favori introuvable.")
    return fav


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("", response_model=list[FavoriteRead])
async def list_favorites(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Favorite]:
    """Lister les favoris de l'utilisateur connecté."""
    stmt = (
        select(Favorite)
        .where(Favorite.user_id == current_user.id)
        .order_by(Favorite.created_at.desc())
    )
    try:
        result = await db.execute(stmt)
        return list(result.scalars().all())
    except Exception as exc:
        logger.error("Erreur DB list_favorites : %s", exc)
        raise HTTPException(status_code=500, detail="Erreur serveur.")


@router.post("", response_model=FavoriteRead, status_code=status.HTTP_201_CREATED)
async def create_favorite(
    payload: FavoriteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Favorite:
    """Ajouter un favori (formation SCAP ou veille marché)."""
    fav = Favorite(
        user_id=current_user.id,
        course_id=payload.course_id,
        market_course_id=payload.market_course_id,
    )
    try:
        db.add(fav)
        await db.flush()
        await db.refresh(fav)
    except Exception as exc:
        logger.error("Erreur DB create_favorite : %s", exc)
        raise HTTPException(status_code=500, detail="Erreur lors de l'ajout du favori.")
    return fav


@router.delete("/{favorite_id}")
async def delete_favorite(
    favorite_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    """Supprimer un favori (propriétaire ou admin)."""
    fav = await _get_favorite_or_404(favorite_id, db)
    if fav.user_id != current_user.id and getattr(current_user, "role", None) != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vous ne pouvez pas supprimer un favori qui ne vous appartient pas.",
        )
    try:
        await db.delete(fav)
        await db.flush()
    except Exception as exc:
        logger.error("Erreur DB delete_favorite %s : %s", favorite_id, exc)
        raise HTTPException(status_code=500, detail="Erreur lors de la suppression.")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
