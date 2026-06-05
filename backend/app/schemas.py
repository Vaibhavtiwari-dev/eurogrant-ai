import re
from pydantic import BaseModel, EmailStr, field_validator, Field, ConfigDict
from typing import Optional, List
from .models import RoleEnum, ProposalStatus
from datetime import datetime

# Auth Schemas
class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None

class UserCreate(UserBase):
    password: str = Field(..., min_length=8)
    organization_name: str # First user creates the org
    invite_code: str

    @field_validator("password")
    @classmethod
    def validate_password_complexity(cls, v):
        if not re.search(r'[A-Z]', v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r'[a-z]', v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r'[0-9]', v):
            raise ValueError("Password must contain at least one digit")
        if not re.search(r'[!@#$%^&*()_+\-=\[\]{}|;:\'",./<>?]', v):
            raise ValueError("Password must contain at least one special character")
        return v

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: Optional[str] = None  # JWT delivered exclusively via httpOnly cookie
    token_type: str
    message: Optional[str] = None

class TokenData(BaseModel):
    email: Optional[str] = None

# Organization Schemas
class OrganizationBase(BaseModel):
    name: str
    subscription_tier: str
    sector: Optional[str] = None
    headcount_range: Optional[str] = None
    revenue_tier: Optional[str] = None
    legal_entity_type: Optional[str] = None
    countries_of_operation: Optional[str] = None # JSON string
    core_technologies: Optional[str] = None # JSON string

class OrganizationOut(OrganizationBase):
    id: int
    match_threshold: float
    alert_email_enabled: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class OrganizationUpdate(BaseModel):
    name: Optional[str] = None
    sector: Optional[str] = None
    headcount_range: Optional[str] = None
    revenue_tier: Optional[str] = None
    legal_entity_type: Optional[str] = None
    countries_of_operation: Optional[str] = None
    core_technologies: Optional[str] = None
    match_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)  # 0.0–1.0 probability range
    alert_email_enabled: Optional[bool] = None


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
    pipelines: List[PipelineOut]
    hot_matches: List[MatchOut]

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
    funding_range: Optional[str] = None
    eligibility_criteria: Optional[str] = None
    scoring_rubric: Optional[str] = None
    source_url: Optional[str] = None
    sector_tags: Optional[str] = None

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
    explanation: Optional[str] = None
    created_at: datetime
    grant: GrantOut

    model_config = ConfigDict(from_attributes=True)


class GrantSearchRequest(BaseModel):
    query: Optional[str] = None
    limit: Optional[int] = 10
    offset: Optional[int] = 0
    sectors: Optional[List[str]] = None


# Proposal Schemas
class ProposalCreate(BaseModel):
    grant_id: int

class ProposalOut(BaseModel):
    id: int
    organization_id: int
    grant_id: int
    status: ProposalStatus
    content: Optional[str] = None
    compatibility_score: Optional[float] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
