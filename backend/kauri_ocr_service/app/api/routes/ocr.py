"""
OCR processing endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from typing import List, Optional
from uuid import UUID
import logging
from pathlib import Path

from app.core.database import get_db
from app.models.ocr_document import OCRDocument, ProcessingStatus
from app.schemas.ocr_document import (
    OCRDocumentResponse,
    OCRProcessRequest,
    OCRProcessResponse,
    OCRResultSummary,
    DocumentSearchRequest,
    DocumentSearchResponse,
)
from app.services.pdf_generator import pdf_generator_service
from app.services.queue_publisher import ocr_queue_publisher

logger = logging.getLogger(__name__)

router = APIRouter()


def _serialize_document(document: OCRDocument) -> OCRDocumentResponse:
    """Convert ORM document to API schema."""
    doc_data = {}
    mapper = OCRDocument.__mapper__
    for column in OCRDocument.__table__.columns:
        attr_key = mapper.get_property_by_column(column).key
        doc_data[column.name] = getattr(document, attr_key)
    return OCRDocumentResponse(**doc_data)


@router.post("/ocr/process", response_model=OCRProcessResponse)
async def process_document(
    request: OCRProcessRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Submit a document for OCR processing
    Creates a job and enqueues it for processing
    """
    try:
        # Create OCR document record
        ocr_doc = OCRDocument(
            tenant_id=request.tenant_id,
            user_id=request.user_id,
            source_document_id=request.source_document_id,
            filename=request.filename,
            file_path=request.file_path,
            file_size=0,  # TODO: Get actual file size
            mime_type=request.mime_type,
            status=ProcessingStatus.QUEUED,
            metadata_json=request.metadata or {}
        )

        db.add(ocr_doc)
        await db.commit()
        await db.refresh(ocr_doc)

        # Publish job to worker queue
        job_message = {
            "document_id": str(ocr_doc.id),
            "tenant_id": str(ocr_doc.tenant_id),
            "user_id": str(ocr_doc.user_id),
            "source_document_id": str(ocr_doc.source_document_id),
            "file_path": ocr_doc.file_path,
            "filename": ocr_doc.filename,
            "mime_type": ocr_doc.mime_type,
            "priority": request.priority,
            "ocr_engine": request.ocr_engine.value if request.ocr_engine else None,
            "languages": request.languages,
            "enable_table_detection": request.enable_table_detection,
            "enable_entity_extraction": request.enable_entity_extraction,
            "enable_ohada_validation": request.enable_ohada_validation,
            "country_code": request.country_code,
            "metadata": request.metadata or {},
        }

        try:
            ocr_queue_publisher.publish_job(job_message, priority=request.priority)
        except Exception as exc:
            logger.error("Failed to enqueue OCR job %s: %s", ocr_doc.id, exc)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to enqueue document for processing",
            ) from exc

        logger.info(f"Document queued for OCR processing: {ocr_doc.id}")

        return OCRProcessResponse(
            job_id=ocr_doc.id,
            document_id=ocr_doc.id,
            status=ProcessingStatus.QUEUED,
            message="Document queued for processing",
            estimated_time_seconds=30
        )

    except Exception as e:
        logger.error(f"Error queuing document for OCR: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to queue document: {str(e)}"
        )


@router.get("/ocr/document/{document_id}", response_model=OCRDocumentResponse)
async def get_document(
    document_id: UUID,
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Get OCR document by ID
    """
    query = select(OCRDocument).where(
        and_(
            OCRDocument.id == document_id,
            OCRDocument.tenant_id == tenant_id,
            OCRDocument.is_deleted == False
        )
    )
    result = await db.execute(query)
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    return _serialize_document(document)


@router.get("/ocr/document/{document_id}/status")
async def get_document_status(
    document_id: UUID,
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Get document processing status
    """
    query = select(
        OCRDocument.id,
        OCRDocument.status,
        OCRDocument.confidence_score,
        OCRDocument.quality_score,
        OCRDocument.requires_human_review,
        OCRDocument.processing_time_ms,
        OCRDocument.error_message
    ).where(
        and_(
            OCRDocument.id == document_id,
            OCRDocument.tenant_id == tenant_id,
            OCRDocument.is_deleted == False
        )
    )
    result = await db.execute(query)
    document = result.one_or_none()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    return {
        "document_id": document.id,
        "status": document.status,
        "confidence_score": document.confidence_score,
        "quality_score": document.quality_score,
        "requires_review": document.requires_human_review,
        "processing_time_ms": document.processing_time_ms,
        "error_message": document.error_message
    }


@router.post("/ocr/search", response_model=DocumentSearchResponse)
async def search_documents(
    request: DocumentSearchRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Search OCR documents
    """
    # Build query
    query = select(OCRDocument).where(
        and_(
            OCRDocument.tenant_id == request.tenant_id,
            OCRDocument.is_deleted == False
        )
    )

    # Apply filters
    if request.status:
        query = query.where(OCRDocument.status == request.status)

    if request.document_type:
        query = query.where(OCRDocument.document_type == request.document_type)

    if request.requires_review is not None:
        query = query.where(OCRDocument.requires_human_review == request.requires_review)

    if request.from_date:
        query = query.where(OCRDocument.created_at >= request.from_date)

    if request.to_date:
        query = query.where(OCRDocument.created_at <= request.to_date)

    if request.min_confidence:
        query = query.where(OCRDocument.confidence_score >= request.min_confidence)

    if request.search_text:
        query = query.where(OCRDocument.extracted_text.ilike(f"%{request.search_text}%"))

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Apply pagination
    query = query.order_by(OCRDocument.created_at.desc())
    query = query.offset(request.offset).limit(request.limit)

    # Execute query
    result = await db.execute(query)
    documents = result.scalars().all()

    # Convert to summary
    items = [
        OCRResultSummary(
            document_id=doc.id,
            status=doc.status,
            document_type=doc.document_type,
            page_count=doc.page_count,
            word_count=doc.word_count,
            confidence_score=doc.confidence_score,
            quality_score=doc.quality_score,
            processing_time_ms=doc.processing_time_ms,
            requires_review=doc.requires_human_review,
            has_tables=False,  # TODO: Check if document has tables
            has_entities=False,  # TODO: Check if document has entities
            created_at=doc.created_at,
            processed_at=doc.processed_at
        )
        for doc in documents
    ]

    return DocumentSearchResponse(
        total=total,
        items=items,
        limit=request.limit,
        offset=request.offset
    )


@router.delete("/ocr/document/{document_id}")
async def delete_document(
    document_id: UUID,
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Soft delete an OCR document
    """
    query = select(OCRDocument).where(
        and_(
            OCRDocument.id == document_id,
            OCRDocument.tenant_id == tenant_id,
            OCRDocument.is_deleted == False
        )
    )
    result = await db.execute(query)
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    # Soft delete
    document.is_deleted = True
    document.deleted_at = func.now()

    await db.commit()

    return {"message": "Document deleted successfully", "document_id": document_id}


@router.get("/ocr/stats/tenant/{tenant_id}")
async def get_tenant_stats(
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Get OCR processing statistics for a tenant
    """
    # Total documents
    total_query = select(func.count(OCRDocument.id)).where(
        and_(
            OCRDocument.tenant_id == tenant_id,
            OCRDocument.is_deleted == False
        )
    )
    total_result = await db.execute(total_query)
    total_documents = total_result.scalar()

    # By status
    status_query = select(
        OCRDocument.status,
        func.count(OCRDocument.id)
    ).where(
        and_(
            OCRDocument.tenant_id == tenant_id,
            OCRDocument.is_deleted == False
        )
    ).group_by(OCRDocument.status)
    status_result = await db.execute(status_query)
    by_status = {status: count for status, count in status_result.all()}

    # Average quality
    avg_query = select(
        func.avg(OCRDocument.confidence_score),
        func.avg(OCRDocument.quality_score)
    ).where(
        and_(
            OCRDocument.tenant_id == tenant_id,
            OCRDocument.is_deleted == False,
            OCRDocument.status == ProcessingStatus.COMPLETED
        )
    )
    avg_result = await db.execute(avg_query)
    avg_confidence, avg_quality = avg_result.one()

    # Requires review
    review_query = select(func.count(OCRDocument.id)).where(
        and_(
            OCRDocument.tenant_id == tenant_id,
            OCRDocument.requires_human_review == True,
            OCRDocument.is_deleted == False
        )
    )
    review_result = await db.execute(review_query)
    requires_review = review_result.scalar()

    return {
        "tenant_id": tenant_id,
        "total_documents": total_documents,
        "by_status": by_status,
        "avg_confidence_score": float(avg_confidence) if avg_confidence else None,
        "avg_quality_score": float(avg_quality) if avg_quality else None,
        "requires_review": requires_review
    }


@router.get("/ocr/document/{document_id}/searchable-pdf")
async def download_searchable_pdf(
    document_id: UUID,
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Download the searchable PDF for a document

    Returns the generated searchable PDF file
    """
    # Get document from database
    query = select(OCRDocument).where(
        and_(
            OCRDocument.id == document_id,
            OCRDocument.tenant_id == tenant_id,
            OCRDocument.is_deleted == False
        )
    )
    result = await db.execute(query)
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    # Check if searchable PDF exists in metadata
    if not document.metadata_json or 'searchable_pdf_path' not in document.metadata_json:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Searchable PDF not generated for this document"
        )

    pdf_path = Path(document.metadata_json['searchable_pdf_path'])

    if not pdf_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Searchable PDF file not found on disk"
        )

    # Return file
    return FileResponse(
        path=str(pdf_path),
        media_type="application/pdf",
        filename=f"{document.filename}_searchable.pdf"
    )


@router.post("/ocr/document/{document_id}/regenerate-pdf")
async def regenerate_searchable_pdf(
    document_id: UUID,
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Regenerate the searchable PDF for a document

    Useful if the original generation failed or the file was deleted
    """
    # Get document from database
    query = select(OCRDocument).where(
        and_(
            OCRDocument.id == document_id,
            OCRDocument.tenant_id == tenant_id,
            OCRDocument.is_deleted == False
        )
    )
    result = await db.execute(query)
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    # Check if original file exists
    if not Path(document.file_path).exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Original document file not found"
        )

    # Check if it's a PDF
    if not document.file_path.lower().endswith('.pdf'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF documents can be converted to searchable PDFs"
        )

    try:
        # Regenerate searchable PDF
        logger.info(f"Regenerating searchable PDF for document: {document_id}")

        pdf_result = await pdf_generator_service.generate_searchable_pdf(
            input_pdf_path=document.file_path,
            output_filename=f"{document.id}_searchable.pdf"
        )

        if not pdf_result.get('success'):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate searchable PDF: {pdf_result.get('error')}"
            )

        # Update document metadata
        if document.metadata_json is None:
            document.metadata_json = {}

        document.metadata_json['searchable_pdf_path'] = pdf_result['output_path']
        document.metadata_json['searchable_pdf_size'] = pdf_result.get('file_size')
        document.metadata_json['searchable_pdf_regenerated_at'] = func.now()

        await db.commit()

        logger.info(f"Searchable PDF regenerated successfully: {document_id}")

        return {
            "message": "Searchable PDF regenerated successfully",
            "document_id": document_id,
            "output_path": pdf_result['output_path'],
            "file_size": pdf_result.get('file_size')
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error regenerating searchable PDF: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to regenerate searchable PDF: {str(e)}"
        )
