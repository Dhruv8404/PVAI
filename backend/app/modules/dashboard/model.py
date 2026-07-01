import uuid
from datetime import datetime, UTC
from sqlalchemy import String, DateTime, ForeignKey, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class ActivityLog(Base):
    __tablename__ = "activity_logs"
    
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    action: Mapped[str] = mapped_column(String(50), nullable=False) # e.g. USER_LOGIN, DOC_GENERATE
    details: Mapped[str] = mapped_column(String(255), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    # Relationships
    user: Mapped["User"] = relationship(lazy="selectin")
