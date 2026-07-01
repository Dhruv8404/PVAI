import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field


# Allowed template details schema
class TemplateMinResponse(BaseModel):
    id: uuid.UUID
    name: str
    version: str

    class Config:
        from_attributes = True


class RoleMinResponse(BaseModel):
    id: uuid.UUID
    name: str

    class Config:
        from_attributes = True


class UserBase(BaseModel):
    email: EmailStr
    name: str


class UserCreate(UserBase):
    password: str = Field(..., min_length=6)
    role: str = "User" # Admin, User
    status: str = "Active" # Active, Inactive
    report_limit: int = 5
    allowed_templates: List[uuid.UUID] = []


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    name: Optional[str] = None
    role: Optional[str] = None
    status: Optional[str] = None
    report_limit: Optional[int] = None
    allowed_templates: Optional[List[uuid.UUID]] = None


class UserResponse(UserBase):
    id: uuid.UUID
    status: str
    created_at: datetime
    last_login: Optional[datetime] = None
    documents_generated: int = 0
    report_limit: int = 5
    roles: List[RoleMinResponse]
    allowed_templates: List[TemplateMinResponse] = []

    class Config:
        from_attributes = True
