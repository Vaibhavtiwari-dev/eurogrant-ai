"""add_created_by_to_proposals

Revision ID: 7b3c9d1e2f4a
Revises: 665cd05ee540
Create Date: 2026-06-19 19:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7b3c9d1e2f4a'
down_revision: Union[str, Sequence[str], None] = '665cd05ee540'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add created_by column to proposals for audit trail."""
    op.add_column('proposals', sa.Column('created_by', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_proposals_created_by', 'proposals', 'users', ['created_by'], ['id'], ondelete='SET NULL')


def downgrade() -> None:
    """Remove created_by column from proposals."""
    op.drop_constraint('fk_proposals_created_by', 'proposals', type_='foreignkey')
    op.drop_column('proposals', 'created_by')
