"""add_creation_key_if_missing

Revision ID: 662f6fe18004
Revises: f81738121747
Create Date: 2026-07-01 12:00:00.000000

"""
import logging
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.exc import OperationalError


revision: str = '662f6fe18004'
down_revision: Union[str, Sequence[str], None] = 'f81738121747'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

logger = logging.getLogger('alembic.migration')


def upgrade() -> None:
    """Ajoute creation_key si la table existe et que la colonne manque.

    Le schéma est aussi créé par `Base.metadata.create_all()` au démarrage ;
    cette migration reste donc idempotente pour les bases fraîches.
    """
    try:
        op.add_column(
            'gap_recommendations',
            sa.Column('creation_key', sa.String(length=255), nullable=True),
        )
    except OperationalError as exc:
        if 'duplicate column name' in str(exc).lower():
            logger.warning("Column 'creation_key' already exists — skipping.")
        else:
            raise


def downgrade() -> None:
    op.drop_column('gap_recommendations', 'creation_key')
