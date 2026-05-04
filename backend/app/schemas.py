from pydantic import BaseModel, EmailStr
from typing import Optional, List
from .models import RoleEnum, ProposalStatus
from datetime import datetime

# Auth Schemas
class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None

class UserCreate(UserBase):
    password: str
    organization_name: str # First user creates the org

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
