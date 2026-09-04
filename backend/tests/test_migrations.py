"""Migrations Alembic — la base doit s'amorcer et s'adopter sans intervention.

Couvre les cas gérés par `init_db()` :
  - base vierge                      -> `upgrade head` crée tout le schéma
  - base déjà gérée                  -> `upgrade head` idempotent
  - base pré-Alembic                 -> réparation du schéma puis `stamp head`
  - base sur une révision inconnue   -> adoption sans « Can't locate revision »
"""

from __future__ import annotations

from pathlib import Path
from unittest import mock

import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.ext.asyncio import create_async_engine

from alembic.script import ScriptDirectory
from app.core import db as db_module
from app.core.config import settings
from app.core.db import Base, _alembic_config, _run_migrations_sync

# Tables métier attendues au schéma initial (hors `alembic_version`).
EXPECTED_TABLES = {
    "users",
    "courses",
    "market_courses",
    "course_proposals",
    "audit_logs",
    "favorites",
    "school_registries",
    "school_courses",
    "market_scan_runs",
    "gap_recommendations",
}


@pytest.fixture()
def db_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Base SQLite temporaire, câblée sur `settings` que lit `alembic/env.py`."""
    import app.models  # noqa: F401 — enregistre les modèles sur Base.metadata

    path = tmp_path / "atlas_test.db"
    monkeypatch.setattr(
        settings, "database_url", f"sqlite+aiosqlite:///{path.as_posix()}"
    )
    return path


def _table_names(path: Path) -> set[str]:
    engine = create_engine(f"sqlite:///{path.as_posix()}")
    try:
        return set(inspect(engine).get_table_names())
    finally:
        engine.dispose()


def _column_names(path: Path, table: str) -> set[str]:
    engine = create_engine(f"sqlite:///{path.as_posix()}")
    try:
        return {c["name"] for c in inspect(engine).get_columns(table)}
    finally:
        engine.dispose()


def _stamped_revision(path: Path) -> str | None:
    engine = create_engine(f"sqlite:///{path.as_posix()}")
    try:
        with engine.connect() as conn:
            row = conn.exec_driver_sql("SELECT version_num FROM alembic_version").first()
        return row[0] if row else None
    finally:
        engine.dispose()


def _head_revision() -> str:
    return ScriptDirectory.from_config(_alembic_config()).get_current_head()


def _write_stamp(path: Path, revision: str) -> None:
    """Tamponne la base sur une révision arbitraire (simule un historique réécrit)."""
    engine = create_engine(f"sqlite:///{path.as_posix()}")
    try:
        with engine.begin() as conn:
            conn.exec_driver_sql(
                "CREATE TABLE IF NOT EXISTS alembic_version "
                "(version_num VARCHAR(32) NOT NULL PRIMARY KEY)"
            )
            conn.exec_driver_sql("DELETE FROM alembic_version")
            conn.exec_driver_sql(
                "INSERT INTO alembic_version (version_num) VALUES (?)", (revision,)
            )
    finally:
        engine.dispose()


def _create_legacy_schema(path: Path) -> None:
    """Simule une base pré-Alembic : tables créées par l'ancien `create_all`."""
    engine = create_engine(f"sqlite:///{path.as_posix()}")
    try:
        Base.metadata.create_all(engine)
    finally:
        engine.dispose()


def test_fresh_database_gets_full_schema(db_file: Path) -> None:
    """Base vierge : `upgrade head` doit créer toutes les tables métier."""
    _run_migrations_sync(has_tables=False, stamped=None)

    tables = _table_names(db_file)
    assert EXPECTED_TABLES <= tables, f"tables manquantes : {EXPECTED_TABLES - tables}"
    assert "alembic_version" in tables


def test_fresh_database_has_previously_missing_columns(db_file: Path) -> None:
    """Régression : les 3 colonnes ajoutées à la main autrefois sont au schéma."""
    _run_migrations_sync(has_tables=False, stamped=None)

    engine = create_engine(f"sqlite:///{db_file.as_posix()}")
    try:
        inspector = inspect(engine)
        gap_cols = {c["name"] for c in inspector.get_columns("gap_recommendations")}
        school_cols = {c["name"] for c in inspector.get_columns("school_registries")}
        market_cols = {c["name"] for c in inspector.get_columns("market_courses")}
    finally:
        engine.dispose()

    assert "creation_key" in gap_cols
    assert "config" in school_cols
    assert "school_registry_id" in market_cols


def test_legacy_database_is_adopted_not_recreated(db_file: Path) -> None:
    """Base existante sans `alembic_version` : `stamp head` sans toucher aux tables."""
    _create_legacy_schema(db_file)
    before = _table_names(db_file)
    assert "alembic_version" not in before

    _run_migrations_sync(has_tables=True, stamped=None)

    after = _table_names(db_file)
    assert "alembic_version" in after
    assert EXPECTED_TABLES <= after


def test_managed_database_upgrade_is_idempotent(db_file: Path) -> None:
    """Deuxième passage sur une base déjà gérée : aucune erreur, schéma stable."""
    _run_migrations_sync(has_tables=False, stamped=None)
    first = _table_names(db_file)

    _run_migrations_sync(has_tables=True, stamped=_stamped_revision(db_file))

    assert _table_names(db_file) == first


def test_database_stamped_on_unknown_revision_is_adopted(db_file: Path) -> None:
    """Révision tamponnée absente de `versions/` (historique réécrit) : pas de crash.

    Cas réel : la base de dev portait `b6a77fe8f7bc`, supprimée lors de la
    reconstruction. `upgrade head` lèverait « Can't locate revision ».
    """
    _create_legacy_schema(db_file)
    _write_stamp(db_file, "b6a77fe8f7bc")

    _run_migrations_sync(has_tables=True, stamped="b6a77fe8f7bc")

    assert _stamped_revision(db_file) == _head_revision()
    assert EXPECTED_TABLES <= _table_names(db_file)


def test_legacy_database_missing_column_is_repaired(db_file: Path) -> None:
    """Colonne absente d'une base pré-Alembic : ajoutée, pas masquée par le stamp.

    Régression des colonnes réellement perdues en production (`school_registries.
    config`, `gap_recommendations.creation_key`, `market_courses.school_registry_id`)
    parce que `create_all` ne modifie jamais une table déjà existante.
    """
    _create_legacy_schema(db_file)
    engine = create_engine(f"sqlite:///{db_file.as_posix()}")
    try:
        with engine.begin() as conn:
            conn.exec_driver_sql("ALTER TABLE school_registries DROP COLUMN config")
            conn.exec_driver_sql(
                "ALTER TABLE gap_recommendations DROP COLUMN creation_key"
            )
    finally:
        engine.dispose()
    assert "config" not in _column_names(db_file, "school_registries")

    _run_migrations_sync(has_tables=True, stamped=None)

    assert "config" in _column_names(db_file, "school_registries")
    assert "creation_key" in _column_names(db_file, "gap_recommendations")
    assert _stamped_revision(db_file) == _head_revision()


def test_legacy_database_missing_table_is_created(db_file: Path) -> None:
    """Table absente d'une base pré-Alembic : créée avant le stamp."""
    _create_legacy_schema(db_file)
    engine = create_engine(f"sqlite:///{db_file.as_posix()}")
    try:
        with engine.begin() as conn:
            conn.exec_driver_sql("DROP TABLE favorites")
    finally:
        engine.dispose()

    _run_migrations_sync(has_tables=True, stamped=None)

    assert EXPECTED_TABLES <= _table_names(db_file)


@pytest.mark.asyncio
async def test_init_db_bootstraps_fresh_database(db_file: Path) -> None:
    """Bout-en-bout : le démarrage applique bien les migrations (pas `create_all`).

    Couvre le calcul de `has_tables` / révision tamponnée fait par `init_db()`.
    """
    calls: list[tuple[bool, str | None]] = []
    real_engine = create_async_engine(settings.database_url)

    async def _fake_thread(func, *args):  # noqa: ANN001 — signature asyncio.to_thread
        calls.append(args)
        return func(*args)

    with (
        mock.patch.object(db_module, "engine", real_engine),
        mock.patch.object(db_module.asyncio, "to_thread", _fake_thread),
    ):
        try:
            await db_module.init_db()
        finally:
            await real_engine.dispose()

    assert calls == [(False, None)], "base vierge : upgrade attendu, pas stamp"
    assert EXPECTED_TABLES <= _table_names(db_file)
    assert _stamped_revision(db_file) == _head_revision()
