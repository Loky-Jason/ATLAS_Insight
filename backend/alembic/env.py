"""Alembic env — sync SQLite for ATLAS Insight (schema-only migrations)."""
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

import app.models  # noqa: F401 — registers models on Base.metadata
from alembic import context
from app.core.config import settings
from app.core.db import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url() -> str:
    """URL sync dérivée de la config applicative (source de vérité unique).

    L'app tourne sur le driver async `aiosqlite`, Alembic en sync : on retire
    juste le suffixe de driver. Évite le drift avec la valeur figée d'alembic.ini.
    """
    return settings.database_url.replace("sqlite+aiosqlite://", "sqlite://")


config.set_main_option("sqlalchemy.url", get_url())


def run_migrations_offline() -> None:
    context.configure(
        url=get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        # render_as_batch : SQLite ne sait pas ALTER/DROP COLUMN nativement,
        # Alembic recrée la table dans un batch.
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
