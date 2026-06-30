"""Router auth — register, login (pose cookie httpOnly), logout, me."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import get_db
from app.core.security import (
    _DUMMY_HASH,
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
    "samesite": "lax",  # Lax fonctionne pour les SPA en dev (127.0.0.1:5173 → 127.0.0.1:8000)
    "secure": settings.is_production,  # True en HTTPS production uniquement
}


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(payload: UserCreate, db: AsyncSession = Depends(get_db)) -> User:
    """Créer un nouveau compte utilisateur.

    Le premier compte créé (bootstrap) devient automatiquement admin.
    Tous les suivants reçoivent le rôle 'user', indépendamment de la requête.
    Un admin authentifié peut ensuite promouvoir via l'interface d'administration.
    """
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

    # Bootstrap : le premier compte devient admin, tous les suivants sont 'user'
    try:
        count_result = await db.execute(select(User))
        is_first_user = count_result.scalar_one_or_none() is None
    except Exception as exc:
        logger.error("Erreur DB register (count) : %s", exc)
        raise HTTPException(status_code=500, detail="Erreur serveur.")

    assigned_role = "admin" if is_first_user else "user"

    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=assigned_role,
    )
    try:
        db.add(user)
        await db.flush()
        await db.refresh(user)
    except Exception as exc:
        logger.error("Erreur DB register (insert) : %s", exc)
        raise HTTPException(status_code=500, detail="Erreur lors de la création du compte.")

    logger.info("Nouvel utilisateur créé : %s (id=%s, rôle=%s)", user.email, user.id, user.role)
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

    # Vérification constante en temps : si l'email est inconnu, on vérifie quand même
    # contre un hash bidon pour ne pas divulguer l'existence du compte par le timing (E2)
    hash_to_check = user.password_hash if user is not None else _DUMMY_HASH
    password_ok = verify_password(payload.password, hash_to_check)

    if user is None or not password_ok:
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
