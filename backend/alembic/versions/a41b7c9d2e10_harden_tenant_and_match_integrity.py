"""harden tenant and match integrity

Revision ID: a41b7c9d2e10
Revises: 23d3fff296a2
Create Date: 2026-06-11
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a41b7c9d2e10"
down_revision: Union[str, Sequence[str], None] = "23d3fff296a2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("organizations", sa.Column("email_domain", sa.String(length=255), nullable=True))
    op.execute(
        sa.text(
            """
            DELETE FROM grant_matches
            WHERE id IN (
                SELECT id FROM (
                    SELECT id,
                           ROW_NUMBER() OVER (
                               PARTITION BY organization_id, grant_id
                               ORDER BY created_at DESC, id DESC
                           ) AS duplicate_rank
                    FROM grant_matches
                ) ranked
                WHERE duplicate_rank > 1
            )
            """
        )
    )
    with op.batch_alter_table("grant_matches") as batch_op:
        batch_op.create_unique_constraint(
            "uq_grant_matches_org_grant",
            ["organization_id", "grant_id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("grant_matches") as batch_op:
        batch_op.drop_constraint("uq_grant_matches_org_grant", type_="unique")
    op.drop_column("organizations", "email_domain")
