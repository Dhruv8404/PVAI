import uuid
from datetime import datetime, UTC
from sqlalchemy import String, JSON, DateTime, Uuid, Boolean
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


class HtmlTemplate(Base):
    __tablename__ = "html_templates"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    version: Mapped[str] = mapped_column(String(20), default="1.0.0")
    description: Mapped[str] = mapped_column(String(255), nullable=True)
    html_file: Mapped[str] = mapped_column(String(255), nullable=False)  # file path
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    uploaded_by: Mapped[str] = mapped_column(String(100), nullable=True)  # User email
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )
