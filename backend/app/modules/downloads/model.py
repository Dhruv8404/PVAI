import uuid
from datetime import datetime, UTC
from sqlalchemy import String, DateTime, ForeignKey, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class DownloadLog(Base):
    __tablename__ = "download_logs"
    
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    generated_document_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("generated_documents.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    format: Mapped[str] = mapped_column(String(10), nullable=False) # HTML, PDF
    ip_address: Mapped[str] = mapped_column(String(50), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))

    # Relationships
    document: Mapped["GeneratedDocument"] = relationship(lazy="selectin")
    user: Mapped["User"] = relationship(lazy="selectin")
