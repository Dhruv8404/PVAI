import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class TemplateBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = None
    version: str = "1.0.0"
    required_files: List[str] = [] # list of expected workbook columns/labels


class TemplateCreate(TemplateBase):
    pass


class TemplateUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    version: Optional[str] = None
    required_files: Optional[List[str]] = None
    status: Optional[str] = None # Active, Inactive


class TemplateResponse(TemplateBase):
    id: uuid.UUID
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Pydantic Schemas for AI Template Wizard & ChromaDB Embeddings

class ManifestFieldCreate(BaseModel):
    field_name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=255)
    required: bool = True
    data_type: str = Field("string", description="Must be one of string, integer, float, date, boolean, enum")
    examples: List[str] = []
    aliases: List[str] = []


class TemplateManifestSubmit(BaseModel):
    required_excel_files: List[str] = Field(..., description="List of spreadsheet files, e.g. ['PSUR Current']")
    required_fields: List[ManifestFieldCreate] = Field(..., min_items=1)


class TemplateFieldResponse(BaseModel):
    id: uuid.UUID
    field_name: str
    description: Optional[str] = None
    required: bool
    data_type: str
    examples: Optional[List[str]] = None
    aliases: Optional[List[str]] = None
    chroma_document_id: Optional[str] = None
    embedding_status: str

    class Config:
        from_attributes = True


class HtmlTemplateResponse(BaseModel):
    id: uuid.UUID
    name: str
    version: str
    description: Optional[str] = None
    html_file: str
    file_url: Optional[str] = None
    preview_image: Optional[str] = None
    is_active: bool
    status: str
    required_files: Optional[List[str]] = None
    uploaded_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class HtmlTemplateDetailResponse(HtmlTemplateResponse):
    html_content: str
    fields: List[TemplateFieldResponse] = []


# Pydantic Schemas for AI Configurations

class AIConfigResponse(BaseModel):
    id: uuid.UUID
    embedding_model: str
    embedding_dimension: int
    collection_name: str
    similarity_threshold: float
    llm_threshold: float
    llm_model: str
    llm_provider: str
    fallback_enabled: bool
    cache_enabled: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AIConfigUpdate(BaseModel):
    embedding_model: Optional[str] = Field(None, min_length=1)
    embedding_dimension: Optional[int] = Field(None, gt=0)
    collection_name: Optional[str] = Field(None, min_length=1)
    similarity_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)
    llm_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)
    llm_model: Optional[str] = Field(None, min_length=1)
    llm_provider: Optional[str] = Field(None, min_length=1)
    fallback_enabled: Optional[bool] = None
    cache_enabled: Optional[bool] = None


# Phase 2 Header Mapping Schemas

class HeaderMappingItem(BaseModel):
    uploaded: str
    mapped: Optional[str] = None
    confidence: float
    source: str
    status: str  # AutoMapped, NeedsReview, Confirmed


class ExcelFileMappingResponse(BaseModel):
    file_name: str
    expected_type: str
    headers: List[HeaderMappingItem]


class AnalyzeHeadersResponse(BaseModel):
    status: str
    files: List[ExcelFileMappingResponse]


class ConfirmMappingItem(BaseModel):
    uploaded_header: str
    mapped_field: str


class ConfirmMappingRequest(BaseModel):
    customer_id: str
    mappings: List[ConfirmMappingItem]


class CustomerHeaderMappingResponse(BaseModel):
    id: uuid.UUID
    customer_id: str
    template_id: uuid.UUID
    uploaded_header: str
    mapped_field: str
    confidence: float
    mapping_source: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


# Phase 3 Data Standardization Schemas

class ValidationLogResponse(BaseModel):
    id: uuid.UUID
    dataset_id: uuid.UUID
    file_name: Optional[str] = None
    sheet_name: Optional[str] = None
    row_number: Optional[int] = None
    field_name: Optional[str] = None
    message: str
    severity: str
    created_at: datetime

    class Config:
        from_attributes = True


class StandardizedDatasetResponse(BaseModel):
    id: uuid.UUID
    template_id: uuid.UUID
    customer_id: str
    upload_session_id: Optional[uuid.UUID] = None
    dataset_version: int
    processing_status: str
    data: Dict[str, Any]
    statistics: Dict[str, Any]
    created_at: datetime

    class Config:
        from_attributes = True


class StandardizeDataAPIResponse(BaseModel):
    dataset_id: uuid.UUID
    statistics: Dict[str, Any]
    validation_summary: Dict[str, int]
    data: Dict[str, Any]


# Phase 4 Report Intelligence Schemas

class PromptTemplateResponse(BaseModel):
    id: uuid.UUID
    template_type: str
    prompt_name: str
    prompt_version: str
    system_prompt: str
    user_prompt: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class GenerateReportRequest(BaseModel):
    dataset_id: uuid.UUID
    generated_by: str


class ReportFeedbackSubmit(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    comments: Optional[str] = None
    narrative_corrections: Dict[str, str] = {}  # {section_name: corrected_text}


class ReportQualityResponse(BaseModel):
    overall_score: float
    completeness_score: float
    consistency_score: float
    formatting_score: float
    suggestions: List[str]


class ReportExplanationResponse(BaseModel):
    decisions: List[Dict[str, Any]]
    overall_explanation: str


class ReportVersionResponse(BaseModel):
    id: uuid.UUID
    template_id: uuid.UUID
    dataset_id: uuid.UUID
    customer_id: str
    version: int
    status: str
    sections_data: Dict[str, Any]
    created_at: datetime


    class Config:
        from_attributes = True


class ReportAuditResponse(BaseModel):
    id: uuid.UUID
    report_id: uuid.UUID
    section_name: str
    action: str
    performed_by: str
    old_value: Optional[str] = None
    new_value: str
    created_at: datetime

    class Config:
        from_attributes = True





