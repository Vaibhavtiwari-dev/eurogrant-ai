"""add proposal sections

Revision ID: e2f4a6b8c910
Revises: a41b7c9d2e10
Create Date: 2026-06-11
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e2f4a6b8c910"
down_revision: Union[str, Sequence[str], None] = "a41b7c9d2e10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TYPE proposalstatus ADD VALUE IF NOT EXISTS 'COMPLETED_WITH_ERRORS'")

    op.add_column(
        "proposals", sa.Column("generation_job_id", sa.String(length=36), nullable=True)
    )
    op.create_index(
        op.f("ix_proposals_generation_job_id"),
        "proposals",
        ["generation_job_id"],
        unique=False,
    )

    section_status = sa.Enum(
        "PENDING",
        "GENERATING",
        "COMPLETED",
        "FAILED",
        name="sectionstatus",
    )
    op.create_table(
        "proposal_sections",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("proposal_id", sa.Integer(), nullable=False),
        sa.Column("section_key", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("weight", sa.Float(), nullable=True),
        sa.Column("content_json", sa.JSON(), nullable=False),
        sa.Column("order", sa.Integer(), nullable=False),
        sa.Column("status", section_status, nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("generation_job_id", sa.String(length=36), nullable=True),
        sa.Column("generation_base_version", sa.Integer(), nullable=True),
        sa.Column("edited_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("edited_by", sa.Integer(), nullable=True),
        sa.Column("last_error_code", sa.String(length=100), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint('"order" >= 0', name="ck_proposal_sections_order_nonnegative"),
        sa.CheckConstraint("version > 0", name="ck_proposal_sections_version_positive"),
        sa.CheckConstraint(
            "weight IS NULL OR (weight >= 0 AND weight <= 1)",
            name="ck_proposal_sections_weight_range",
        ),
        sa.ForeignKeyConstraint(["edited_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["proposal_id"], ["proposals.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("proposal_id", "order", name="uq_proposal_sections_order"),
        sa.UniqueConstraint("proposal_id", "section_key", name="uq_proposal_sections_key"),
    )
    op.create_index(
        op.f("ix_proposal_sections_generation_job_id"),
        "proposal_sections",
        ["generation_job_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_proposal_sections_id"), "proposal_sections", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_proposal_sections_proposal_id"),
        "proposal_sections",
        ["proposal_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_proposal_sections_proposal_id"), table_name="proposal_sections")
    op.drop_index(op.f("ix_proposal_sections_id"), table_name="proposal_sections")
    op.drop_index(
        op.f("ix_proposal_sections_generation_job_id"), table_name="proposal_sections"
    )
    op.drop_table("proposal_sections")
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        sa.Enum(name="sectionstatus").drop(bind, checkfirst=True)
    op.drop_index(op.f("ix_proposals_generation_job_id"), table_name="proposals")
    op.drop_column("proposals", "generation_job_id")
    # PostgreSQL enum values are intentionally retained. Removing one requires
    # rebuilding the enum and risks locking or rewriting the proposals table.
