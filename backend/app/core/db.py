"""SQLAlchemy 2.0 async engine, session factory, base model, and get_db dependency."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncGenerator
from pathlib import Path

from sqlalchemy import Connection, create_engine, event, inspect
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from alembic import command
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory
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


# Per-connection PRAGMAs (must run on every new connection from the pool).
# busy_timeout avoids SQLITE_BUSY during long concurrent scans.
# foreign_keys enables FK constraints (off by default in SQLite).
@event.listens_for(engine.sync_engine, "connect")
def _set_sqlite_pragmas(dbapi_connection, _connection_record):
    cur = dbapi_connection.cursor()
    try:
        cur.execute("PRAGMA busy_timeout=30000")
        cur.execute("PRAGMA foreign_keys=ON")
    finally:
        cur.close()


SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


class Base(DeclarativeBase):
    """Shared declarative base for all SQLAlchemy models."""


ALEMBIC_INI = Path(__file__).resolve().parents[2] / "alembic.ini"


def _alembic_config() -> Config:
    """Config Alembic ; l'URL réelle est résolue par `alembic/env.py` via settings."""
    return Config(str(ALEMBIC_INI))


def _sync_url() -> str:
    """URL sync équivalente à `settings.database_url` (Alembic ne parle pas async)."""
    return settings.database_url.replace("sqlite+aiosqlite://", "sqlite://")


def _known_revisions(cfg: Config) -> set[str]:
    """Révisions présentes dans `alembic/versions/`."""
    return {rev.revision for rev in ScriptDirectory.from_config(cfg).walk_revisions()}


def _repair_legacy_schema(connection: Connection) -> None:
    """Aligne une base pré-Alembic sur les modèles avant de la tamponner.

    Sans cela, `stamp head` déclarerait « à jour » une base à qui il manque une
    colonne — exactement le bug que les migrations doivent supprimer (la base de
    dev a réellement perdu `market_courses.school_registry_id` de cette façon).

    Ajouts non destructifs uniquement : tables manquantes puis colonnes
    manquantes. Une colonne NOT NULL sans défaut ne peut pas être ajoutée à une
    table peuplée : on échoue explicitement plutôt que de corrompre les données.
    """
    import app.models  # noqa: F401 — enregistre les modèles sur Base.metadata

    Base.metadata.create_all(connection)  # ne crée que les tables absentes

    inspector = inspect(connection)
    operations = Operations(MigrationContext.configure(connection))
    blocking: list[str] = []

    for table in Base.metadata.sorted_tables:
        present = {col["name"] for col in inspector.get_columns(table.name)}
        for column in table.columns:
            if column.name in present:
                continue
            if not column.nullable and column.server_default is None:
                blocking.append(f"{table.name}.{column.name}")
                continue
            logger.warning(
                "Colonne manquante ajoutée à la base existante : %s.%s",
                table.name,
                column.name,
            )
            operations.add_column(table.name, column._copy())

    if blocking:
        raise RuntimeError(
            "Colonnes NOT NULL sans valeur par défaut absentes de la base "
            f"existante : {', '.join(sorted(blocking))}. "
            "Migration manuelle requise avant démarrage."
        )


def _run_migrations_sync(has_tables: bool, stamped: str | None) -> None:
    """Amène la base au dernier schéma (appelé dans un thread, Alembic est sync).

    - base vierge                    -> `upgrade head` crée tout le schéma
    - base gérée, révision connue    -> `upgrade head` applique les migrations dues
    - base non gérée OU tamponnée sur une révision inconnue (historique réécrit)
                                     -> réparation du schéma puis `stamp head`
    """
    cfg = _alembic_config()

    if not has_tables:
        command.upgrade(cfg, "head")
        return

    if stamped is not None and stamped in _known_revisions(cfg):
        command.upgrade(cfg, "head")
        return

    reason = (
        "sans table alembic_version"
        if stamped is None
        else f"tamponnée sur une révision inconnue ({stamped})"
    )
    logger.warning("Base existante %s : adoption après vérification du schéma.", reason)

    engine_sync = create_engine(_sync_url())
    try:
        with engine_sync.begin() as connection:
            _repair_legacy_schema(connection)
    finally:
        engine_sync.dispose()

    # purge : la révision courante peut être inconnue (historique réécrit) ;
    # sans cela `stamp` tente de la résoudre et lève « Can't locate revision ».
    command.stamp(cfg, "head", purge=True)


async def init_db() -> None:
    """Applique les migrations Alembic. Appelé au démarrage de l'application."""
    try:
        async with engine.begin() as conn:
            # File-level PRAGMAs (persistent in the DB file, applied once).
            await conn.exec_driver_sql("PRAGMA journal_mode=WAL")
            await conn.exec_driver_sql("PRAGMA synchronous=NORMAL")
            inspected = await conn.run_sync(
                lambda sync_conn: inspect(sync_conn).get_table_names()
            )
            stamped: str | None = None
            if "alembic_version" in inspected:
                result = await conn.exec_driver_sql(
                    "SELECT version_num FROM alembic_version"
                )
                row = result.first()
                stamped = row[0] if row else None

        has_tables = any(name != "alembic_version" for name in inspected)
        await asyncio.to_thread(_run_migrations_sync, has_tables, stamped)
        logger.info("Schéma de base à jour (Alembic, WAL activé).")
    except Exception as exc:
        logger.error("Erreur lors de la migration de la base : %s", exc)
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
