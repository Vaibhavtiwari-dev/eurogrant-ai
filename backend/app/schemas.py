import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from .models import ProposalStatus, RoleEnum


# Auth Schemas
class UserBase(BaseModel):
    email: EmailStr
    full_name: str | None = None


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)
    organization_name: str  # First user creates the org
    invite_code: str

    @field_validator("password")
    @classmethod
    def validate_password_complexity(cls, v):
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"[0-9]", v):
            raise ValueError("Password must contain at least one digit")
        if not re.search(r'[!@#$%^&*()_+\-=\[\]{}|;:\'",./<>?]', v):
            raise ValueError("Password must contain at least one special character")
        return v


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str | None = None  # JWT delivered exclusively via httpOnly cookie
    token_type: str
    message: str | None = None


class TokenData(BaseModel):
    email: str | None = None


# Organization Schemas
class OrganizationBase(BaseModel):
    name: str
    subscription_tier: str
    sector: str | None = None
    headcount_range: str | None = None
    revenue_tier: str | None = None
    legal_entity_type: str | None = None
    countries_of_operation: str | None = None  # JSON string
    core_technologies: str | None = None  # JSON string


class OrganizationOut(OrganizationBase):
    id: int
    match_threshold: float
    alert_email_enabled: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OrganizationUpdate(BaseModel):
    name: str | None = None
    sector: str | None = None
    headcount_range: str | None = None
    revenue_tier: str | None = None
    legal_entity_type: str | None = None
    countries_of_operation: str | None = None
    core_technologies: str | None = None
    match_threshold: float | None = Field(None, ge=0.0, le=1.0)  # 0.0–1.0 probability range
    alert_email_enabled: bool | None = None


# Dashboard Schemas
class PipelineOut(BaseModel):
    id: str
    title: str
    status: str
    progress: int
    subtext: str


class MatchOut(BaseModel):
    title: str
    desc: str
    score: int
    time: str


class DashboardStatsOut(BaseModel):
    active_high_matches: int
    ai_generation_quality: int
    total_pipeline_value: float


class DashboardOverviewOut(BaseModel):
    stats: DashboardStatsOut
    pipelines: list[PipelineOut]
    hot_matches: list[MatchOut]


# User Output
class UserOut(UserBase):
    id: int
    role: RoleEnum
    organization_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Document Schemas
class DocumentOut(BaseModel):
    id: int
    file_name: str
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Grant Schemas
class GrantBase(BaseModel):
    external_id: str
    title: str
    description: str
    deadline: datetime
    funding_range: str | None = None
    eligibility_criteria: str | None = None
    scoring_rubric: str | None = None
    source_url: str | None = None
    sector_tags: str | None = None


class GrantCreate(GrantBase):
    pass


class GrantOut(GrantBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class GrantMatchOut(BaseModel):
    id: int
    organization_id: int
    grant_id: int
    score: float
    explanation: str | None = None
    created_at: datetime
    grant: GrantOut

    model_config = ConfigDict(from_attributes=True)


class GrantSearchRequest(BaseModel):
    query: str | None = None
    limit: int | None = 10
    offset: int | None = 0
    sectors: list[str] | None = None


# Proposal Schemas
class ProposalCreate(BaseModel):
    grant_id: int


class ProposalOut(BaseModel):
    id: int
    organization_id: int
    grant_id: int
    status: ProposalStatus
    content: str | None = None
    compatibility_score: float | None = None
    created_at: datetime
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
