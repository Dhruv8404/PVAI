import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class DocumentResponse(BaseModel):
    id: uuid.UUID
    user_id: Optional[uuid.UUID] = None
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
    
    # New fields for ReportHistory spec
    template_version: Optional[str] = "1.0.0"
    report_type: Optional[str] = "PSUR"
    generated_file_size: Optional[int] = 0
    download_count: Optional[int] = 0
    last_downloaded_at: Optional[datetime] = None
    browser: Optional[str] = None
    ip_address: Optional[str] = None
    failed_reason: Optional[str] = None

    class Config:
        from_attributes = True
