import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class TemplateBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = None
    version: str = "1.0.0"
    required_files: List[str] = [] # list of expected workbook columns/labels


class TemplateCreate(TemplateBase):
    pass


class TemplateUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    version: Optional[str] = None
    required_files: Optional[List[str]] = None
    status: Optional[str] = None # Active, Inactive


class TemplateResponse(TemplateBase):
    id: uuid.UUID
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class HtmlTemplateResponse(BaseModel):
    id: uuid.UUID
    name: str
    version: str
    description: Optional[str] = None
    html_file: str
    is_active: bool
    uploaded_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class HtmlTemplateDetailResponse(HtmlTemplateResponse):
    html_content: str

