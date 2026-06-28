"""initial_schema

Revision ID: f81738121747
Revises:
Create Date: 2026-06-28 01:56:36.831465

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f81738121747'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('gap_recommendations', sa.Column('creation_key', sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column('gap_recommendations', 'creation_key')
