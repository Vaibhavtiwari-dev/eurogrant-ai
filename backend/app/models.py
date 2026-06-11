from datetime import datetime
from enum import StrEnum
from typing import Optional

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from .database import Base


class RoleEnum(StrEnum):
    ADMIN = "admin"
    WRITER = "writer"
    VIEWER = "viewer"


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    subscription_tier: Mapped[str] = mapped_column(String(50), default="growth")
    email_domain: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sector: Mapped[str | None] = mapped_column(String(255), nullable=True)
    headcount_range: Mapped[str | None] = mapped_column(String(50), nullable=True)
    revenue_tier: Mapped[str | None] = mapped_column(String(50), nullable=True)
    legal_entity_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    countries_of_operation: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    core_technologies: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=True
    )

    match_threshold: Mapped[float] = mapped_column(Float, default=0.7)
    alert_email_enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    users: Mapped[list["User"]] = relationship(back_populates="organization")
    proposals: Mapped[list["Proposal"]] = relationship(back_populates="organization")
    documents: Mapped[list["CompanyDocument"]] = relationship(back_populates="organization")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    role: Mapped[RoleEnum] = mapped_column(Enum(RoleEnum), default=RoleEnum.VIEWER)
    organization_id: Mapped[int | None] = mapped_column(
        ForeignKey("organizations.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    organization: Mapped[Optional["Organization"]] = relationship(back_populates="users")


class Grant(Base):
    __tablename__ = "grants"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    external_id: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255), index=True)
    description: Mapped[str] = mapped_column(Text)
    deadline: Mapped[datetime] = mapped_column(DateTime)
    funding_range: Mapped[str | None] = mapped_column(String(100), nullable=True)
    eligibility_criteria: Mapped[str | None] = mapped_column(Text, nullable=True)
    scoring_rubric: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    sector_tags: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ProposalStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    COMPLETED_WITH_ERRORS = "completed_with_errors"
    FAILED = "failed"


class SectionStatus(StrEnum):
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


class DocumentStatus(StrEnum):
    PENDING = "pending"
    PROCESSED = "processed"
    FAILED = "failed"


class CompanyDocument(Base):
    __tablename__ = "company_documents"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"))
    file_name: Mapped[str] = mapped_column(String(255))
    s3_key: Mapped[str] = mapped_column(String(500))
    content_type: Mapped[str] = mapped_column(String(100))
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus), default=DocumentStatus.PENDING
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    organization: Mapped["Organization"] = relationship(back_populates="documents")


class Proposal(Base):
    __tablename__ = "proposals"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"))
    grant_id: Mapped[int] = mapped_column(ForeignKey("grants.id"))
    status: Mapped[ProposalStatus] = mapped_column(
        Enum(ProposalStatus), default=ProposalStatus.PENDING
    )
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    compatibility_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    generation_job_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=True
    )

    organization: Mapped["Organization"] = relationship(back_populates="proposals")
    grant: Mapped["Grant"] = relationship()
    sections: Mapped[list["ProposalSection"]] = relationship(
        back_populates="proposal",
        order_by="ProposalSection.order",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class ProposalSection(Base):
    __tablename__ = "proposal_sections"
    __table_args__ = (
        UniqueConstraint("proposal_id", "section_key", name="uq_proposal_sections_key"),
        UniqueConstraint("proposal_id", "order", name="uq_proposal_sections_order"),
        CheckConstraint('"order" >= 0', name="ck_proposal_sections_order_nonnegative"),
        CheckConstraint("version > 0", name="ck_proposal_sections_version_positive"),
        CheckConstraint(
            "weight IS NULL OR (weight >= 0 AND weight <= 1)",
            name="ck_proposal_sections_weight_range",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    proposal_id: Mapped[int] = mapped_column(
        ForeignKey("proposals.id", ondelete="CASCADE"), nullable=False, index=True
    )
    section_key: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    weight: Mapped[float | None] = mapped_column(Float, nullable=True)
    content_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[SectionStatus] = mapped_column(
        Enum(SectionStatus), nullable=False, default=SectionStatus.PENDING
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    generation_job_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    generation_base_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    edited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    edited_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    last_error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=True
    )

    proposal: Mapped["Proposal"] = relationship(back_populates="sections")


class GrantMatch(Base):
    __tablename__ = "grant_matches"
    __table_args__ = (
        UniqueConstraint("organization_id", "grant_id", name="uq_grant_matches_org_grant"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"))
    grant_id: Mapped[int] = mapped_column(ForeignKey("grants.id"))
    score: Mapped[float] = mapped_column(Float)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    organization: Mapped["Organization"] = relationship()
    grant: Mapped["Grant"] = relationship()
