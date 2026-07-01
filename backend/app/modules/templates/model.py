import uuid
from datetime import datetime, UTC
from sqlalchemy import String, JSON, DateTime, Uuid
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class DocumentTemplate(Base):
    __tablename__ = "document_templates"
    
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    description: Mapped[str] = mapped_column(String(255), nullable=True)
    version: Mapped[str] = mapped_column(String(20), default="1.0.0")
    required_files: Mapped[list[str]] = mapped_column(JSON, nullable=False) # JSON array of strings
    status: Mapped[str] = mapped_column(String(20), default="Active") # Active, Inactive
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )
