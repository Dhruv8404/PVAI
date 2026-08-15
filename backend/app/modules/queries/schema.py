import uuid
from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, EmailStr, Field


class QueryCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    phone: str = Field(..., min_length=5, max_length=50)
    message: str = Field(..., min_length=5, max_length=5000)


class QueryStatusUpdate(BaseModel):
    status: Literal["Recent", "Viewed"]


class QueryOut(BaseModel):
    id: uuid.UUID
    name: str
    email: str
    phone: str
    message: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True
