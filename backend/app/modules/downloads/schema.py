import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class DownloadLogResponse(BaseModel):
    id: uuid.UUID
    generated_document_id: uuid.UUID
    document_name: Optional[str] = None
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    format: str
    ip_address: Optional[str] = None
    timestamp: datetime

    class Config:
        from_attributes = True
