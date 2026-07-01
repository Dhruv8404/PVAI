import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class DocumentResponse(BaseModel):
    id: uuid.UUID
    name: str
    template_id: Optional[uuid.UUID] = None
    template_name: Optional[str] = None
    excel_file_name: str
    html_path: str
    pdf_path: Optional[str] = None
    status: str
    execution_time_ms: int
    created_at: datetime
    created_by_name: Optional[str] = None

    class Config:
        from_attributes = True
