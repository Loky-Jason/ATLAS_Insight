"""SQLAlchemy 2.0 async engine, session factory, base model, and get_db dependency."""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

logger = logging.getLogger(__name__)

# Ensure the data directory exists before SQLite creates the file
_db_path_str = settings.database_url.replace("sqlite+aiosqlite:///", "")
_db_path = Path(_db_path_str)
try:
    _db_path.parent.mkdir(parents=True, exist_ok=True)
except OSError as exc:
    logger.error("Impossible de créer le répertoire de la base de données : %s", exc)

engine = create_async_engine(
    settings.database_url,
    echo=settings.environment == "development",
    connect_args={"check_same_thread": False},
)

SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


class Base(DeclarativeBase):
    """Shared declarative base for all SQLAlchemy models."""


async def init_db() -> None:
    """Create all tables. Called at application startup."""
    try:
        async with engine.begin() as conn:
            # Import models so they register on Base.metadata
            import app.models  # noqa: F401  # side-effect import

            await conn.run_sync(Base.metadata.create_all)
        logger.info("Tables créées / vérifiées avec succès.")
    except Exception as exc:
        logger.error("Erreur lors de la création des tables : %s", exc)
        raise


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an async DB session."""
    async with SessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
