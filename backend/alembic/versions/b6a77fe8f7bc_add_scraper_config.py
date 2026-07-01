"""add_scraper_config

Revision ID: b6a77fe8f7bc
Revises: f81738121747
Create Date: 2026-07-01 09:16:45.319678

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b6a77fe8f7bc"
down_revision: Union[str, Sequence[str], None] = "f81738121747"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("school_registries", sa.Column("config", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("school_registries", "config")
