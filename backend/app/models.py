"""Pydantic models for API request/response validation."""

from typing import Optional, List, Dict, Any, Union, Literal
from pydantic import BaseModel, Field
from datetime import datetime, timezone
from enum import Enum

# Existing models for test data generation can be imported here

class SubscriptionTier(str, Enum):
    """User subscription tier enum."""
    FREE = "free"
    PAID = "paid"
    ENTERPRISE = "enterprise"

class ProjectStatus(str, Enum):
    """Project status enum."""
    CREATED = "created"
    DOCUMENTS_UPLOADED = "documents_uploaded"
    PROCESSING = "processing"
    GENERATING = "generating"
    SCHEMA_GENERATED = "schema_generated"
    COMPLETED = "completed"
    FAILED = "failed"

class DocumentStatus(str, Enum):
    """Document processing status enum."""
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class JobStatus(str, Enum):
    """Background job status enum."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

# Request Models
class ProjectCreateRequest(BaseModel):
    """Request model for creating a new project."""
    name: str = Field(..., min_length=1, max_length=255, description="Project name")
    description: Optional[str] = Field(None, max_length=1000, description="Project description")
    instruction: Optional[str] = Field(None, description="Instruction for dataset generation")

class ProjectUpdateRequest(BaseModel):
    """Request model for updating a project."""
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Project name")
    description: Optional[str] = Field(None, max_length=1000, description="Project description")
    instruction: Optional[str] = Field(None, min_length=10, description="Instruction for dataset generation")

class SchemaGenerateRequest(BaseModel):
    """Request model for generating schema."""
    mode: Literal["qa", "business"] = Field("qa", description="Schema generation mode: 'qa' for Q&A training or 'business' for business datasets")
    instruction: str = Field(..., min_length=10, description="Instruction for schema generation")
    feedback: Optional[str] = Field(None, description="User feedback for schema refinement")
    selected_document_ids: Optional[List[str]] = Field(None, description="List of document IDs to use for schema generation. If None, all documents are used.")

class SchemaUpdateRequest(BaseModel):
    """Request model for updating project schema."""
    schema_config: List[Dict[str, Any]] = Field(..., description="Updated schema configuration")

class DatasetGenerateRequest(BaseModel):
    """Request model for starting dataset generation."""
    num_records: int = Field(10, ge=1, le=5000, description="Number of records to generate")
    rows_per_context: int = Field(5, ge=1, le=20, description="Number of rows to generate per context")
    evolution_depth: int = Field(1, ge=1, le=3, description="Depth of dataset evolution/transformation")

class DatasetRecordUpdate(BaseModel):
    """Model for updating individual dataset records."""
    record_id: str = Field(..., description="Record ID to update")
    approved: bool = Field(..., description="Whether the record is approved")
    data: Optional[Dict[str, Any]] = Field(None, description="Updated record data")

class DatasetRecordsUpdateRequest(BaseModel):
    """Request model for batch updating dataset records."""
    updates: List[DatasetRecordUpdate] = Field(..., description="List of record updates")

class ExportRequest(BaseModel):
    """Request model for exporting dataset."""
    format: str = Field(..., pattern="^(json|csv)$", description="Export format: json or csv")
    approved_only: bool = Field(True, description="Export only approved records")
    filename: Optional[str] = Field(None, max_length=255, description="Custom filename (without extension)")

# Response Models
class UserProfileResponse(BaseModel):
    """Response model for user profile."""
    id: str
    subscription_tier: SubscriptionTier
    monthly_usage_pages: int
    monthly_usage_mb: float
    last_reset_date: datetime
    created_at: datetime
    updated_at: datetime

class ProjectSummary(BaseModel):
    """Summary model for project listing."""
    id: str
    name: str
    description: Optional[str]
    status: ProjectStatus
    documents_count: int
    datasets_count: int
    total_pages_processed: int
    processing_time_seconds: int
    created_at: datetime
    updated_at: datetime

class ProjectListResponse(BaseModel):
    """Response model for project listing."""
    projects: List[ProjectSummary]
    pagination: Dict[str, Any]

class DocumentSummary(BaseModel):
    """Summary model for document listing."""
    id: str
    filename: str
    file_size: int
    file_type: str
    status: DocumentStatus
    pages_extracted: Optional[int]
    pages_processed: int
    error_message: Optional[str]
    created_at: datetime
    updated_at: datetime

class DatasetSummary(BaseModel):
    """Summary model for dataset listing."""
    id: str
    total_records: int
    approved_records: int
    generation_config: Dict[str, Any]
    created_at: datetime

class ProjectDetailResponse(BaseModel):
    """Detailed response model for project."""
    id: str
    name: str
    description: Optional[str]
    instruction: Optional[str]
    status: ProjectStatus
    schema_config: Optional[Dict[str, Any]]
    total_pages_processed: int
    processing_time_seconds: int
    documents: List[DocumentSummary]
    datasets: List[DatasetSummary]
    created_at: datetime
    updated_at: datetime

class SchemaField(BaseModel):
    """Model for schema field."""
    key: str = Field(..., description="Field name/key")
    type: str = Field(..., description="Field data type")
    description: str = Field(..., description="Field description")

class SchemaResponse(BaseModel):
    """Response model for schema generation."""
    generated_schema: List[SchemaField]

# New models for PUT /documents/projects/{id}/schema and templates
class SchemaPutField(BaseModel):
    key: str
    type: str
    required: Optional[bool] = False
    description: Optional[str] = None

class SchemaPutSchema(BaseModel):
    name: Optional[str] = None
    fields: List[SchemaPutField]

class SchemaPutRequest(BaseModel):
    schema: SchemaPutSchema
    instruction: Optional[str] = None

class SchemaTemplateCreateRequest(BaseModel):
    name: str
    category: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    schema_json: Dict[str, Any]

class DocumentUploadResponse(BaseModel):
    """Response model for document upload."""
    uploaded_files: List[DocumentSummary]
    task_id: Optional[str] = Field(None, description="Background task ID for processing")

class ProcessingProgress(BaseModel):
    """Model for processing progress information."""
    current_step: str
    steps_completed: int
    total_steps: int
    percentage: float
    estimated_remaining: Optional[str] = Field(None, description="Estimated time remaining")

class DocumentStatusResponse(BaseModel):
    """Response model for document processing status."""
    id: str
    filename: str
    status: DocumentStatus
    progress: Optional[ProcessingProgress]
    pages_extracted: Optional[int]
    error_message: Optional[str]

class GenerationProgress(BaseModel):
    """Model for dataset generation progress."""
    chunks_processed: int
    total_chunks: int
    percentage: float
    records_generated: int
    estimated_remaining: Optional[str]

class GenerationStatusResponse(BaseModel):
    """Response model for dataset generation status."""
    status: JobStatus
    progress: Optional[GenerationProgress]
    current_step: str

class DatasetRecord(BaseModel):
    """Model for individual dataset record."""
    id: str
    data: Dict[str, Any]  # The actual Q&A or structured data
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="Confidence score")
    source_info: Optional[Dict[str, Any]] = Field(None, description="Source document information")
    approved: bool = Field(False, description="Whether the record is approved")
    edited: bool = Field(False, description="Whether the record has been edited")

class DatasetDetailResponse(BaseModel):
    """Detailed response model for dataset."""
    id: str
    total_records: int
    approved_records: int
    schema_used: Dict[str, Any]
    generation_config: Dict[str, Any]
    records: List[DatasetRecord]
    pagination: Dict[str, Any]
    created_at: datetime

class ExportResponse(BaseModel):
    """Response model for dataset export."""
    export_id: str
    download_url: str
    format: str
    record_count: int
    file_size: int
    approved_only: bool

class LimitCheckResponse(BaseModel):
    """Response model for user limit checking."""
    allowed: bool
    reason: Optional[str] = None
    limits: Optional[Dict[str, Any]] = None
    current_usage: Optional[Dict[str, Any]] = None

class APIResponse(BaseModel):
    """Generic API response wrapper."""
    success: bool
    data: Optional[Any] = None
    message: Optional[str] = None
    error: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ErrorResponse(BaseModel):
    """Error response model."""
    success: bool = Field(False)
    error: Dict[str, Any]
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))