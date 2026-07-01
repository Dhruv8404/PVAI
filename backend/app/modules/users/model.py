import uuid
from datetime import datetime, UTC
from sqlalchemy import String, Boolean, DateTime, Table, Column, ForeignKey, Uuid, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.modules.templates.model import DocumentTemplate
from app.modules.documents.model import GeneratedDocument

# Junction Table: User <-> Role
user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", Uuid, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", Uuid, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)
)

# Junction Table: Role <-> Permission
role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", Uuid, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    Column("permission_id", Uuid, ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True)
)

# Junction Table: User <-> DocumentTemplate (allocated permissions)
user_templates = Table(
    "user_templates",
    Base.metadata,
    Column("user_id", Uuid, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("template_id", Uuid, ForeignKey("document_templates.id", ondelete="CASCADE"), primary_key=True)
)


class Permission(Base):
    __tablename__ = "permissions"
    
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    description: Mapped[str] = mapped_column(String(255), nullable=True)


class Role(Base):
    __tablename__ = "roles"
    
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    description: Mapped[str] = mapped_column(String(255), nullable=True)
    
    # Relationships
    permissions: Mapped[list[Permission]] = relationship(
        secondary=role_permissions, lazy="selectin"
    )


class User(Base):
    __tablename__ = "users"
    
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="Active") # Active, Inactive
    report_limit: Mapped[int] = mapped_column(Integer, default=5)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )
    
    # Relationships
    roles: Mapped[list[Role]] = relationship(
        secondary=user_roles, lazy="selectin"
    )
    
    allowed_templates: Mapped[list["DocumentTemplate"]] = relationship(
        secondary=user_templates, lazy="selectin"
    )
    
    documents: Mapped[list["GeneratedDocument"]] = relationship(
        "GeneratedDocument", back_populates="user", lazy="selectin"
    )
