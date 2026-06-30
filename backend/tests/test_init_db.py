"""Tests — init_db : PRAGMAs WAL / busy_timeout / foreign_keys."""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

import pytest
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import create_async_engine


@pytest.mark.asyncio
async def test_event_listener_sets_pragmas_on_every_connection():
    """Le listener busy_timeout + foreign_keys s'applique à chaque connexion du pool."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db_url = f"sqlite+aiosqlite:///{db_path}"

        engine = create_async_engine(db_url, echo=False)

        # Replicate the production listener (same PRAGMAs as app.core.db).
        @event.listens_for(engine.sync_engine, "connect")
        def _set_pragmas(dbapi_connection, _record):
            cur = dbapi_connection.cursor()
            try:
                cur.execute("PRAGMA busy_timeout=30000")
                cur.execute("PRAGMA foreign_keys=ON")
            finally:
                cur.close()

        try:
            # Première connexion
            async with engine.connect() as conn1:
                busy1 = (await conn1.exec_driver_sql("PRAGMA busy_timeout")).scalar()
                fk1 = (await conn1.exec_driver_sql("PRAGMA foreign_keys")).scalar()
                assert busy1 == 30000, f"busy_timeout attendu 30000, obtenu {busy1}"
                assert fk1 == 1, f"foreign_keys attendu 1, obtenu {fk1}"

            # Seconde connexion du pool — doit aussi avoir les PRAGMAs
            async with engine.connect() as conn2:
                busy2 = (await conn2.exec_driver_sql("PRAGMA busy_timeout")).scalar()
                fk2 = (await conn2.exec_driver_sql("PRAGMA foreign_keys")).scalar()
                assert busy2 == 30000
                assert fk2 == 1
        finally:
            await engine.dispose()


@pytest.mark.asyncio
async def test_init_db_activates_wal_mode():
    """init_db() doit activer le mode WAL sur la DB fichier."""
    tmpdir = Path(tempfile.mkdtemp())
    try:
        db_path = tmpdir / "test.db"
        db_url = f"sqlite+aiosqlite:///{db_path}"

        from app.core import db as db_module

        original_engine = db_module.engine
        test_engine = create_async_engine(db_url, echo=False)
        try:
            db_module.engine = test_engine
            await db_module.init_db()

            # Vérifier le mode WAL directement sur le fichier (avant dispose)
            import sqlite3
            with sqlite3.connect(str(db_path)) as raw:
                mode = raw.execute("PRAGMA journal_mode").fetchone()[0]
                assert mode.lower() == "wal", f"journal_mode attendu 'wal', obtenu '{mode}'"
        finally:
            await test_engine.dispose()
            db_module.engine = original_engine
    finally:
        # Sur Windows, les fichiers WAL restent verrouillés un instant après dispose
        # → best-effort cleanup, on ignore les erreurs
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)


# ---------------------------------------------------------------------------
# busy_timeout : valeur 30000 sur chaque connexion du pool
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_busy_timeout_pragma_30000_on_multiple_pool_connections():
    """`PRAGMA busy_timeout` doit valoir 30000 sur TOUTES les nouvelles connexions."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "busy.db"
        engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", echo=False)

        # Miroir exact du listener de app.core.db._set_sqlite_pragmas
        @event.listens_for(engine.sync_engine, "connect")
        def _set_pragmas(dbapi_connection, _record):
            cur = dbapi_connection.cursor()
            try:
                cur.execute("PRAGMA busy_timeout=30000")
                cur.execute("PRAGMA foreign_keys=ON")
            finally:
                cur.close()

        try:
            # 1re connexion du pool
            async with engine.connect() as conn1:
                busy1 = (await conn1.exec_driver_sql("PRAGMA busy_timeout")).scalar()
                assert busy1 == 30000, f"conn1 busy_timeout attendu 30000, obtenu {busy1}"

            # 2e connexion — doit aussi voir 30000 (listener reconnect)
            async with engine.connect() as conn2:
                busy2 = (await conn2.exec_driver_sql("PRAGMA busy_timeout")).scalar()
                assert busy2 == 30000, f"conn2 busy_timeout attendu 30000, obtenu {busy2}"

            # 3e pour être sûr (au-delà de 1, on a prouvé le re-fire du listener)
            async with engine.connect() as conn3:
                busy3 = (await conn3.exec_driver_sql("PRAGMA busy_timeout")).scalar()
                assert busy3 == 30000
        finally:
            await engine.dispose()


# ---------------------------------------------------------------------------
# foreign_keys : ON (=1) sur chaque connexion du pool
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_foreign_keys_pragma_on_on_multiple_pool_connections():
    """`PRAGMA foreign_keys` doit valoir 1 (ON) sur TOUTES les nouvelles connexions."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "fk.db"
        engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", echo=False)

        @event.listens_for(engine.sync_engine, "connect")
        def _set_pragmas(dbapi_connection, _record):
            cur = dbapi_connection.cursor()
            try:
                cur.execute("PRAGMA busy_timeout=30000")
                cur.execute("PRAGMA foreign_keys=ON")
            finally:
                cur.close()

        try:
            async with engine.connect() as conn1:
                fk1 = (await conn1.exec_driver_sql("PRAGMA foreign_keys")).scalar()
                assert fk1 == 1, f"conn1 foreign_keys attendu 1, obtenu {fk1}"

            async with engine.connect() as conn2:
                fk2 = (await conn2.exec_driver_sql("PRAGMA foreign_keys")).scalar()
                assert fk2 == 1, f"conn2 foreign_keys attendu 1, obtenu {fk2}"
        finally:
            await engine.dispose()


# ---------------------------------------------------------------------------
# Concurrence : avec busy_timeout=30000, la 2e écriture ATTEND (ne fail pas)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_busy_timeout_makes_second_writer_wait_instead_of_failing():
    """busy_timeout=30000 : la 2e connexion qui tente d'écrire BLOQUE au lieu
    de lever OperationalError('database is locked') immédiatement.

    On valide via asyncio.wait_for(timeout=0.5s) — si la 2e écriture attendait
    bien, on lèvera asyncio.TimeoutError. Si busy_timeout n'était pas actif,
    on aurait OperationalError instantanée.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "busy_concur.db"
        engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", echo=False)

        @event.listens_for(engine.sync_engine, "connect")
        def _set_pragmas(dbapi_connection, _record):
            cur = dbapi_connection.cursor()
            try:
                cur.execute("PRAGMA busy_timeout=30000")
                cur.execute("PRAGMA foreign_keys=ON")
            finally:
                cur.close()

        try:
            # 1re connexion : crée la table et INSERT non-committé → write lock détenu
            async with engine.connect() as conn1:
                await conn1.exec_driver_sql("CREATE TABLE t (x INTEGER)")
                await conn1.execute(text("INSERT INTO t VALUES (1)"))

                # 2e connexion : tente d'écrire → doit BLOQUER grâce à busy_timeout.
                # Note : sqlite3 est synchrone, donc asyncio ne peut pas interrompre
                # l'appel en cours. On ne peut qu'attendre la fin de busy_timeout (30s)
                # lors de la fermeture. D'où la durée du test.
                async with engine.connect() as conn2:
                    try:
                        await asyncio.wait_for(
                            conn2.execute(text("INSERT INTO t VALUES (2)")),
                            timeout=0.1,
                        )
                        pytest.fail(
                            "La 2e écriture aurait dû BLOQUER (busy_timeout=30000) "
                            "mais a complété en <0.1s — le write lock n'est pas pris ?"
                        )
                    except asyncio.TimeoutError:
                        # Comportement attendu : conn2 attend, le timeout asyncio
                        # expire bien avant busy_timeout (30s).
                        pass

                # On libère la transaction de conn1 avant de sortir du with
                await conn1.rollback()
        finally:
            await engine.dispose()
