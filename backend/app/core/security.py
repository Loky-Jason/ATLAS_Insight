"""Security utilities: argon2 password hashing, JWT creation/decode, auth dependency."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHashError
from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import get_db

logger = logging.getLogger(__name__)

# --- Argon2 configuration ---
_ph = PasswordHasher(
    time_cost=2,
    memory_cost=65536,  # 64 MiB
    parallelism=2,
    hash_len=32,
    salt_len=16,
)

ALGORITHM = "HS256"
COOKIE_NAME = "access_token"


# ---------------------------------------------------------------------------
# Password helpers
# ---------------------------------------------------------------------------

def hash_password(plain: str) -> str:
    """Return argon2 hash of *plain* password. Never store *plain*."""
    return _ph.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """
    Return True if *plain* matches *hashed*.
    Raises nothing — returns False on any mismatch or error.
    """
    try:
        return _ph.verify(hashed, plain)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False
    except Exception as exc:
        logger.error("Erreur inattendue lors de la vérification du mot de passe : %s", exc)
        return False


def needs_rehash(hashed: str) -> bool:
    """Return True if the stored hash should be upgraded (argon2 params changed)."""
    return _ph.check_needs_rehash(hashed)


# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------

def create_access_token(user_id: int, role: str) -> str:
    """Create a signed JWT containing *user_id* and *role*."""
    now = datetime.now(tz=timezone.utc)
    expire = now + timedelta(seconds=settings.jwt_expire_seconds)
    payload: dict = {
        "sub": str(user_id),
        "role": role,
        "iat": now,
        "exp": expire,
    }
    try:
        return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)
    except Exception as exc:
        logger.error("Erreur lors de la création du token JWT : %s", exc)
        raise


def decode_access_token(token: str) -> dict:
    """
    Decode and validate *token*.
    Raises HTTPException 401 on any failure.
    """
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expiré.",
        )
    except jwt.InvalidTokenError as exc:
        logger.warning("Token JWT invalide : %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalide.",
        )


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------

async def get_current_user(
    access_token: Annotated[str | None, Cookie(alias=COOKIE_NAME)] = None,
    db: AsyncSession = Depends(get_db),
) -> "User":  # type: ignore[name-defined]  # forward ref
    """
    Dependency that resolves the authenticated user from the httpOnly JWT cookie.
    Raises 401 if missing/invalid, 404 if user no longer exists.
    """
    from app.models.user import User  # local import avoids circular deps

    if access_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Non authentifié.",
        )

    payload = decode_access_token(access_token)
    user_id_str: str | None = payload.get("sub")

    if user_id_str is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token malformé.",
        )

    try:
        result = await db.execute(select(User).where(User.id == int(user_id_str)))
        user = result.scalar_one_or_none()
    except Exception as exc:
        logger.error("Erreur DB lors de la récupération de l'utilisateur : %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur serveur.",
        )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Utilisateur introuvable.",
        )

    return user
