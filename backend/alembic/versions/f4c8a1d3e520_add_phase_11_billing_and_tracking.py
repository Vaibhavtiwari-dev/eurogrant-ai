"""add phase 11 billing and tracking

Revision ID: f4c8a1d3e520
Revises: e2f4a6b8c910
Create Date: 2026-06-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f4c8a1d3e520"
down_revision: str | Sequence[str] | None = "e2f4a6b8c910"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    subscription_status = sa.Enum(
        "INACTIVE",
        "TRIALING",
        "ACTIVE",
        "PAST_DUE",
        "CANCELED",
        "UNPAID",
        name="subscriptionstatus",
    )
    application_status = sa.Enum(
        "DRAFT",
        "SUBMITTED",
        "WON",
        "LOST",
        "WITHDRAWN",
        name="applicationstatus",
    )

    op.add_column(
        "organizations",
        sa.Column(
            "subscription_status",
            subscription_status,
            nullable=False,
            server_default="INACTIVE",
        ),
    )
    op.add_column("organizations", sa.Column("stripe_customer_id", sa.String(255)))
    op.add_column("organizations", sa.Column("stripe_subscription_id", sa.String(255)))
    op.add_column(
        "organizations",
        sa.Column("subscription_current_period_end", sa.DateTime(timezone=True)),
    )
    op.create_index(
        op.f("ix_organizations_stripe_customer_id"),
        "organizations",
        ["stripe_customer_id"],
        unique=True,
    )
    op.create_index(
        op.f("ix_organizations_stripe_subscription_id"),
        "organizations",
        ["stripe_subscription_id"],
        unique=True,
    )

    op.add_column(
        "proposals",
        sa.Column(
            "application_status",
            application_status,
            nullable=False,
            server_default="DRAFT",
        ),
    )
    op.add_column("proposals", sa.Column("submitted_at", sa.DateTime(timezone=True)))

    op.create_table(
        "proposal_feedback",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "proposal_id",
            sa.Integer(),
            sa.ForeignKey("proposals.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("week_start", sa.Date(), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("comments", sa.Text()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "rating >= 1 AND rating <= 5",
            name="ck_proposal_feedback_rating",
        ),
        sa.UniqueConstraint(
            "proposal_id",
            "user_id",
            "week_start",
            name="uq_proposal_feedback_user_week",
        ),
    )
    op.create_index(
        op.f("ix_proposal_feedback_id"), "proposal_feedback", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_proposal_feedback_proposal_id"),
        "proposal_feedback",
        ["proposal_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_proposal_feedback_user_id"),
        "proposal_feedback",
        ["user_id"],
        unique=False,
    )

    op.create_table(
        "billing_webhook_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("stripe_event_id", sa.String(255), nullable=False),
        sa.Column("event_type", sa.String(255), nullable=False),
        sa.Column(
            "processed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(
        op.f("ix_billing_webhook_events_id"),
        "billing_webhook_events",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_billing_webhook_events_stripe_event_id"),
        "billing_webhook_events",
        ["stripe_event_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_billing_webhook_events_stripe_event_id"),
        table_name="billing_webhook_events",
    )
    op.drop_index(op.f("ix_billing_webhook_events_id"), table_name="billing_webhook_events")
    op.drop_table("billing_webhook_events")

    op.drop_index(op.f("ix_proposal_feedback_user_id"), table_name="proposal_feedback")
    op.drop_index(op.f("ix_proposal_feedback_proposal_id"), table_name="proposal_feedback")
    op.drop_index(op.f("ix_proposal_feedback_id"), table_name="proposal_feedback")
    op.drop_table("proposal_feedback")

    op.drop_column("proposals", "submitted_at")
    op.drop_column("proposals", "application_status")
    op.drop_index(
        op.f("ix_organizations_stripe_subscription_id"),
        table_name="organizations",
    )
    op.drop_index(op.f("ix_organizations_stripe_customer_id"), table_name="organizations")
    op.drop_column("organizations", "subscription_current_period_end")
    op.drop_column("organizations", "stripe_subscription_id")
    op.drop_column("organizations", "stripe_customer_id")
    op.drop_column("organizations", "subscription_status")

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        sa.Enum(name="applicationstatus").drop(bind, checkfirst=True)
        sa.Enum(name="subscriptionstatus").drop(bind, checkfirst=True)
