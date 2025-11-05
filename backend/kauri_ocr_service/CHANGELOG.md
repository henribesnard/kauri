# Changelog

All notable changes to the KAURI OCR Service will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned
- Qwen2.5-VL GPU engine integration
- Surya handwriting OCR
- Advanced table detection with TableTransformer
- Signature detection
- Elasticsearch full-text search
- LLM-based entity extraction
- A/B testing framework
- Auto-scaling workers

## [1.0.0] - 2024-10-15

### Added
- Initial release of KAURI OCR Service
- FastAPI REST API with async support
- PaddleOCR engine for CPU-based document processing
- Multi-format support (PDF, PNG, JPG, TIFF, BMP)
- Multi-page document processing
- RabbitMQ asynchronous worker architecture
- PostgreSQL database with complete schema:
  - ocr_documents: Main document metadata and results
  - ocr_pages: Per-page details and layout
  - ocr_tables: Extracted tables with multiple formats
  - ocr_entities: Named entity extraction
- Redis caching layer for results and statistics
- MinIO/S3 storage for documents and outputs
- OHADA compliance validation:
  - Invoice validation
  - Balance sheet validation
  - Journal entry validation
  - SYSCOHADA account code validation
  - Financial amount validation
- Entity extraction with spaCy:
  - Financial entities (amounts, VAT, currency)
  - Identifiers (invoice numbers, tax IDs)
  - Dates and parties
  - Accounting codes
- Quality scoring and review system
- Markdown output generation
- Multi-tenant support with strict isolation
- Health check endpoints
- Docker and docker-compose configuration
- Comprehensive documentation
- Test suite with pytest
- Alembic database migrations
- Makefile for common tasks

### API Endpoints
- `POST /api/v1/ocr/process` - Submit document for OCR
- `GET /api/v1/ocr/document/{id}` - Get OCR results
- `GET /api/v1/ocr/document/{id}/status` - Get processing status
- `POST /api/v1/ocr/search` - Search documents
- `GET /api/v1/ocr/stats/tenant/{id}` - Get tenant statistics
- `DELETE /api/v1/ocr/document/{id}` - Delete document
- `GET /api/v1/health` - Health check
- `GET /api/v1/health/ready` - Readiness check
- `GET /api/v1/health/live` - Liveness check

### Features
- Asynchronous processing with priority queues
- Automatic retry with exponential backoff
- Quality score calculation
- Human review flagging
- OHADA compliance checking
- Structured data extraction
- Multi-language support (FR, EN)
- Rate limiting per tenant
- Audit logging
- Soft delete support

### Infrastructure
- Docker containerization
- Docker Compose for local development
- PostgreSQL 15+ database
- Redis cache
- RabbitMQ message queue
- MinIO object storage
- Prometheus metrics ready
- Health checks for Kubernetes

### Documentation
- README with installation and usage
- ARCHITECTURE.md with detailed design
- API documentation (OpenAPI/Swagger)
- Configuration examples
- Testing guide

## [0.1.0] - 2024-10-01

### Added
- Project initialization
- Basic project structure
- Requirements and dependencies
