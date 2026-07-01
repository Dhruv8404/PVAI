import uuid
from datetime import datetime, UTC
from sqlalchemy import String, Integer, DateTime, ForeignKey, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class GeneratedDocument(Base):
    __tablename__ = "generated_documents"
    
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    template_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("document_templates.id", ondelete="SET NULL"), nullable=True, index=True)
    
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    excel_file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    html_path: Mapped[str] = mapped_column(String(255), nullable=False)
    pdf_path: Mapped[str] = mapped_column(String(255), nullable=True)
    
    status: Mapped[str] = mapped_column(String(20), default="Success") # Success, Failed
    execution_time_ms: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), index=True)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="documents", lazy="selectin")
    template: Mapped["DocumentTemplate"] = relationship(lazy="selectin")
