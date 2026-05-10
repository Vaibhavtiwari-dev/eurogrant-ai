from pydantic import BaseModel, EmailStr, field_validator, Field
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

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

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
    created_at: datetime

    class Config:
        from_attributes = True

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

    class Config:
        from_attributes = True

# Document Schemas
class DocumentOut(BaseModel):
    id: int
    file_name: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True
