"""
SQLAlchemy models and enums for OCR documents.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import (
    Column,
    String,
    Enum as SqlEnum,
    Integer,
    Float,
    Boolean,
    DateTime,
    Text,
    JSON,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.sql import func

from app.core.database import Base


class DocumentType(str, Enum):
    """Supported document categories."""

    INVOICE = "invoice"
    RECEIPT = "receipt"
    BANK_STATEMENT = "bank_statement"
    FINANCIAL_STATEMENT = "financial_statement"
    CONTRACT = "contract"
    OTHER = "other"


class ProcessingStatus(str, Enum):
    """Workflow status for OCR processing."""

    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REQUIRES_REVIEW = "requires_review"
    CANCELLED = "cancelled"


class OCREngine(str, Enum):
    """Enumeration of supported OCR engines."""

    PADDLE = "paddleocr"
    QWEN = "qwen25vl"
    SURYA = "surya"
    TESSERACT = "tesseract"


class OCRDocument(Base):
    """Persistent representation of an OCR processing job."""

    __tablename__ = "ocr_documents"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(PGUUID(as_uuid=True), nullable=False, index=True)
    user_id = Column(PGUUID(as_uuid=True), nullable=False)
    source_document_id = Column(PGUUID(as_uuid=True), nullable=False)

    filename = Column(String(255), nullable=False)
    file_path = Column(String(1024), nullable=False)
    file_size = Column(Integer, nullable=False, default=0)
    page_count = Column(Integer, nullable=False, default=1)
    mime_type = Column(String(100), nullable=False)

    status = Column(
        SqlEnum(ProcessingStatus, name="processing_status"),
        nullable=False,
        default=ProcessingStatus.QUEUED,
    )
    ocr_engine = Column(SqlEnum(OCREngine, name="ocr_engine"), nullable=True)
    document_type = Column(SqlEnum(DocumentType, name="document_type"), nullable=True)
    document_subtype = Column(String(100), nullable=True)
    classification_confidence = Column(Float, nullable=True)

    extracted_text = Column(Text, nullable=True)
    markdown_output = Column(Text, nullable=True)
    structured_data = Column(MutableDict.as_mutable(JSON), nullable=True)

    confidence_score = Column(Float, nullable=True)
    quality_score = Column(Float, nullable=True)
    word_count = Column(Integer, nullable=False, default=0)
    character_count = Column(Integer, nullable=False, default=0)

    total_amount = Column(Float, nullable=True)
    currency = Column(String(8), nullable=True)
    vat_amount = Column(Float, nullable=True)
    vat_rate = Column(Float, nullable=True)
    amount_ht = Column(Float, nullable=True)

    ohada_compliant = Column(Boolean, default=False)
    ohada_validation_errors = Column(MutableDict.as_mutable(JSON), nullable=True)
    country_code = Column(String(4), nullable=True)

    requires_human_review = Column(Boolean, default=False)
    reviewed_by = Column(PGUUID(as_uuid=True), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)

    processing_time_ms = Column(Integer, nullable=True)
    retry_count = Column(Integer, nullable=False, default=0)
    error_message = Column(Text, nullable=True)

    storage_path = Column(String(1024), nullable=True)
    markdown_path = Column(String(1024), nullable=True)
    json_path = Column(String(1024), nullable=True)

    metadata_json = Column(
        "metadata",
        MutableDict.as_mutable(JSON),
        nullable=True,
    )

    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    processed_at = Column(DateTime(timezone=True), nullable=True)

    is_deleted = Column(Boolean, nullable=False, default=False)

    def mark_processed(self, quality_ms: int | None = None) -> None:
        """Helper to set completion metadata."""
        self.status = ProcessingStatus.COMPLETED
        self.processed_at = datetime.utcnow()
        self.processing_time_ms = quality_ms or self.processing_time_ms

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return (
            f"<OCRDocument id={self.id} tenant={self.tenant_id} "
            f"status={self.status} file={self.filename}>"
        )
