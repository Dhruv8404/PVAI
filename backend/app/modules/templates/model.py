import uuid
from datetime import datetime, UTC
from sqlalchemy import String, JSON, DateTime, Uuid, Boolean, ForeignKey, Float, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
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
    preview_image: Mapped[str] = mapped_column(String(255), nullable=True)
    
    # New Phase 1 Columns
    status: Mapped[str] = mapped_column(String(20), default="Draft")  # Draft, Processing, Ready, Failed, Active, Inactive
    required_files: Mapped[list[str]] = mapped_column(JSON, nullable=True)  # List of required spreadsheet names
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )

    # Relationships
    fields: Mapped[list["TemplateField"]] = relationship(
        "TemplateField", back_populates="template", cascade="all, delete-orphan"
    )

    @property
    def file_url(self) -> str:
        return self.html_file


class TemplateField(Base):
    __tablename__ = "template_fields"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    template_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("html_templates.id", ondelete="CASCADE"), nullable=False)
    field_name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=True)
    required: Mapped[bool] = mapped_column(Boolean, default=True)
    data_type: Mapped[str] = mapped_column(String(20), default="string")  # string, integer, float, date, boolean, enum
    examples: Mapped[list[str]] = mapped_column(JSON, nullable=True)  # JSON list of examples
    aliases: Mapped[list[str]] = mapped_column(JSON, nullable=True)  # JSON list of aliases
    chroma_document_id: Mapped[str] = mapped_column(String(255), nullable=True)
    embedding_status: Mapped[str] = mapped_column(String(20), default="Pending")  # Pending, Completed, Failed
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    # Relationships
    template: Mapped["HtmlTemplate"] = relationship("HtmlTemplate", back_populates="fields")


class AIConfiguration(Base):
    __tablename__ = "ai_configurations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    embedding_model: Mapped[str] = mapped_column(String(100), default="BAAI/bge-small-en-v1.5")
    embedding_dimension: Mapped[int] = mapped_column(Integer, default=384)
    collection_name: Mapped[str] = mapped_column(String(100), default="template_fields")
    similarity_threshold: Mapped[float] = mapped_column(Float, default=0.90)
    llm_threshold: Mapped[float] = mapped_column(Float, default=0.70)
    llm_model: Mapped[str] = mapped_column(String(50), default="gpt-4o")
    llm_provider: Mapped[str] = mapped_column(String(50), default="openai")  # openai, gemini, ollama
    fallback_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    cache_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )


class ExcelUploadSession(Base):
    __tablename__ = "excel_upload_sessions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    template_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("html_templates.id", ondelete="CASCADE"), nullable=False)
    customer_id: Mapped[str] = mapped_column(String(100), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    expected_file_type: Mapped[str] = mapped_column(String(100), nullable=False)
    detected_sheet_names: Mapped[list[str]] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="Uploaded")  # Uploaded, Analyzed, Failed
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class CustomerHeaderMapping(Base):
    __tablename__ = "customer_header_mappings"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[str] = mapped_column(String(100), nullable=False)
    template_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("html_templates.id", ondelete="CASCADE"), nullable=False)
    uploaded_header: Mapped[str] = mapped_column(String(100), nullable=False)
    mapped_field: Mapped[str] = mapped_column(String(100), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    mapping_source: Mapped[str] = mapped_column(String(20), default="Embedding")  # Embedding, LLM, Manual
    status: Mapped[str] = mapped_column(String(20), default="AutoMapped")  # AutoMapped, NeedsReview, Confirmed
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )


class StandardizedDataset(Base):
    __tablename__ = "standardized_datasets"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    template_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("html_templates.id", ondelete="CASCADE"), nullable=False)
    customer_id: Mapped[str] = mapped_column(String(100), nullable=False)
    upload_session_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("excel_upload_sessions.id", ondelete="SET NULL"), nullable=True)
    dataset_version: Mapped[int] = mapped_column(Integer, default=1)
    processing_status: Mapped[str] = mapped_column(String(20), default="Reading")  # Reading, Standardizing, Validating, Merging, Building, Completed, Failed
    data: Mapped[dict] = mapped_column(JSON, nullable=False)
    statistics: Mapped[dict] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class ValidationLog(Base):
    __tablename__ = "validation_logs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    dataset_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("standardized_datasets.id", ondelete="CASCADE"), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=True)
    sheet_name: Mapped[str] = mapped_column(String(100), nullable=True)
    row_number: Mapped[int] = mapped_column(Integer, nullable=True)
    field_name: Mapped[str] = mapped_column(String(100), nullable=True)
    message: Mapped[str] = mapped_column(String(500), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), default="Error")  # Error, Warning
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class PromptTemplate(Base):
    __tablename__ = "prompt_templates"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    template_type: Mapped[str] = mapped_column(String(50), nullable=False)  # Narrative Generation, Clinical Summary, etc.
    prompt_name: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(10), default="1.0")
    system_prompt: Mapped[str] = mapped_column(String(2000), nullable=False)
    user_prompt: Mapped[str] = mapped_column(String(2000), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class ReportVersion(Base):
    __tablename__ = "report_versions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    template_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("html_templates.id", ondelete="CASCADE"), nullable=False)
    dataset_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("standardized_datasets.id", ondelete="CASCADE"), nullable=False)
    customer_id: Mapped[str] = mapped_column(String(100), nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(30), default="AI Generated")  # Draft, AI Generated, Under Review, Approved, Rejected, Archived
    generated_by: Mapped[str] = mapped_column(String(100), nullable=False)
    sections_data: Mapped[dict] = mapped_column(JSON, nullable=False)  # Dict containing each section's data and version metadata
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))



class ReportAudit(Base):
    __tablename__ = "report_audits"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    report_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("report_versions.id", ondelete="CASCADE"), nullable=False)
    section_name: Mapped[str] = mapped_column(String(50), nullable=False)
    action: Mapped[str] = mapped_column(String(50), nullable=False)  # Edited, Status Change, Approved
    performed_by: Mapped[str] = mapped_column(String(100), nullable=False)
    old_value: Mapped[str] = mapped_column(String(5000), nullable=True)
    new_value: Mapped[str] = mapped_column(String(5000), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class ReportGeneration(Base):
    __tablename__ = "report_generations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    report_version_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("report_versions.id", ondelete="CASCADE"), nullable=False)
    quality_score: Mapped[float] = mapped_column(Float, default=0.0)
    quality_suggestions: Mapped[dict] = mapped_column(JSON, nullable=True)
    explanations: Mapped[dict] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class AIProcessingLog(Base):
    __tablename__ = "ai_processing_logs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    processing_step: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g., Executive Summary Agent
    provider: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g., openai
    model: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g., gpt-4o
    tokens_used: Mapped[int] = mapped_column(Integer, default=0)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="Success")  # Success, Failed
    prompt_version: Mapped[str] = mapped_column(String(20), nullable=True)
    dataset_version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class LearningHistory(Base):
    __tablename__ = "learning_histories"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    source_action: Mapped[str] = mapped_column(String(100), nullable=False)  # Reviewer Narrative Edit
    customer_id: Mapped[str] = mapped_column(String(100), nullable=False)
    template_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("html_templates.id", ondelete="CASCADE"), nullable=False)
    key_field: Mapped[str] = mapped_column(String(100), nullable=False)  # Section Name e.g. Executive Summary
    original_value: Mapped[str] = mapped_column(String(5000), nullable=False)
    corrected_value: Mapped[str] = mapped_column(String(5000), nullable=False)
    confidence_gain: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))




