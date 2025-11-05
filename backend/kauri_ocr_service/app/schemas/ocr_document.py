"""
OCR Document Schemas
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID
from pydantic import BaseModel, Field, field_validator

from app.models.ocr_document import DocumentType, ProcessingStatus, OCREngine


class OCRDocumentBase(BaseModel):
    """Base schema for OCR document"""
    filename: str
    file_path: str
    file_size: int
    mime_type: str
    page_count: int = 1


class OCRDocumentCreate(OCRDocumentBase):
    """Schema for creating OCR document"""
    tenant_id: UUID
    user_id: UUID
    source_document_id: UUID
    metadata: Optional[Dict[str, Any]] = None


class OCRDocumentUpdate(BaseModel):
    """Schema for updating OCR document"""
    status: Optional[ProcessingStatus] = None
    document_type: Optional[DocumentType] = None
    extracted_text: Optional[str] = None
    markdown_output: Optional[str] = None
    structured_data: Optional[Dict[str, Any]] = None
    confidence_score: Optional[float] = None
    quality_score: Optional[float] = None
    requires_human_review: Optional[bool] = None
    ohada_compliant: Optional[bool] = None
    metadata: Optional[Dict[str, Any]] = None


class FinancialData(BaseModel):
    """Financial data extracted from document"""
    total_amount: Optional[float] = None
    currency: Optional[str] = None
    vat_amount: Optional[float] = None
    vat_rate: Optional[float] = None
    amount_ht: Optional[float] = None


class OCRDocumentResponse(OCRDocumentBase):
    """Schema for OCR document response"""
    id: UUID
    tenant_id: UUID
    user_id: UUID
    source_document_id: UUID

    # Classification
    document_type: Optional[DocumentType] = None
    document_subtype: Optional[str] = None
    classification_confidence: Optional[float] = None

    # Status
    status: ProcessingStatus
    ocr_engine: Optional[OCREngine] = None

    # Results
    extracted_text: Optional[str] = None
    markdown_output: Optional[str] = None
    structured_data: Optional[Dict[str, Any]] = None

    # Quality
    confidence_score: Optional[float] = None
    quality_score: Optional[float] = None
    word_count: int = 0
    character_count: int = 0

    # Financial
    total_amount: Optional[float] = None
    currency: Optional[str] = None
    vat_amount: Optional[float] = None
    vat_rate: Optional[float] = None
    amount_ht: Optional[float] = None

    # OHADA
    ohada_compliant: Optional[bool] = None
    ohada_validation_errors: Optional[Dict[str, Any]] = None
    country_code: Optional[str] = None

    # Review
    requires_human_review: bool = False
    reviewed_by: Optional[UUID] = None
    reviewed_at: Optional[datetime] = None

    # Processing
    processing_time_ms: Optional[int] = None
    retry_count: int = 0
    error_message: Optional[str] = None

    # Storage
    storage_path: Optional[str] = None
    markdown_path: Optional[str] = None
    json_path: Optional[str] = None

    # Metadata
    metadata: Optional[Dict[str, Any]] = None

    # Timestamps
    created_at: datetime
    updated_at: datetime
    processed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class OCRProcessRequest(BaseModel):
    """Schema for OCR processing request"""
    document_id: UUID
    tenant_id: UUID
    user_id: UUID
    source_document_id: UUID
    file_path: str
    filename: str
    mime_type: str

    # Options
    priority: int = Field(default=5, ge=1, le=10)
    ocr_engine: Optional[OCREngine] = None
    languages: Optional[List[str]] = None
    enable_table_detection: bool = True
    enable_entity_extraction: bool = True
    enable_ohada_validation: bool = True

    # Context
    document_type_hint: Optional[DocumentType] = None
    country_code: Optional[str] = None

    metadata: Optional[Dict[str, Any]] = None


class OCRProcessResponse(BaseModel):
    """Schema for OCR processing response"""
    job_id: UUID
    document_id: UUID
    status: ProcessingStatus
    message: str
    estimated_time_seconds: Optional[int] = None


class OCRResultSummary(BaseModel):
    """Summary of OCR results"""
    document_id: UUID
    status: ProcessingStatus
    document_type: Optional[DocumentType] = None
    page_count: int
    word_count: int
    confidence_score: Optional[float] = None
    quality_score: Optional[float] = None
    processing_time_ms: Optional[int] = None
    requires_review: bool = False
    has_tables: bool = False
    has_entities: bool = False
    created_at: datetime
    processed_at: Optional[datetime] = None


class DocumentSearchRequest(BaseModel):
    """Schema for document search"""
    tenant_id: UUID
    status: Optional[ProcessingStatus] = None
    document_type: Optional[DocumentType] = None
    requires_review: Optional[bool] = None
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None
    search_text: Optional[str] = None
    min_confidence: Optional[float] = None
    limit: int = Field(default=50, le=100)
    offset: int = Field(default=0, ge=0)


class DocumentSearchResponse(BaseModel):
    """Schema for document search response"""
    total: int
    items: List[OCRResultSummary]
    limit: int
    offset: int
