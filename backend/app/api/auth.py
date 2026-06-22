"""Router auth — register, login (pose cookie httpOnly), logout, me."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.security import (
    COOKIE_NAME,
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.schemas.user import UserCreate, UserLogin, UserRead

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentification"])

_COOKIE_KWARGS = {
    "key": COOKIE_NAME,
    "httponly": True,
    "samesite": "lax",
    "secure": False,  # True en production HTTPS — régler via Settings
}


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(payload: UserCreate, db: AsyncSession = Depends(get_db)) -> User:
    """Créer un nouveau compte utilisateur."""
    try:
        result = await db.execute(select(User).where(User.email == payload.email))
        existing = result.scalar_one_or_none()
    except Exception as exc:
        logger.error("Erreur DB register (check email) : %s", exc)
        raise HTTPException(status_code=500, detail="Erreur serveur.")

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Un compte avec cet email existe déjà.",
        )

    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=payload.role,
    )
    try:
        db.add(user)
        await db.flush()
        await db.refresh(user)
    except Exception as exc:
        logger.error("Erreur DB register (insert) : %s", exc)
        raise HTTPException(status_code=500, detail="Erreur lors de la création du compte.")

    logger.info("Nouvel utilisateur créé : %s (id=%s)", user.email, user.id)
    return user


@router.post("/login", response_model=UserRead)
async def login(
    payload: UserLogin,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> User:
    """Authentifier et poser le cookie JWT httpOnly."""
    try:
        result = await db.execute(select(User).where(User.email == payload.email))
        user = result.scalar_one_or_none()
    except Exception as exc:
        logger.error("Erreur DB login : %s", exc)
        raise HTTPException(status_code=500, detail="Erreur serveur.")

    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect.",
        )

    token = create_access_token(user_id=user.id, role=user.role)
    response.set_cookie(value=token, **_COOKIE_KWARGS)
    logger.info("Connexion réussie : %s", user.email)
    return user


@router.post("/logout")
async def logout() -> Response:
    """Effacer le cookie JWT. Retourne 204 No Content."""
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    response.delete_cookie(key=COOKIE_NAME, httponly=True, samesite="lax")
    return response


@router.get("/me", response_model=UserRead)
async def me(current_user: User = Depends(get_current_user)) -> User:
    """Retourner le profil de l'utilisateur connecté."""
    return current_user
