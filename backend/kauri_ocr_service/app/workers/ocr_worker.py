"""
OCR Worker - Processes documents from RabbitMQ queue
"""
import asyncio
import json
import logging
import sys
from typing import Dict, Any
import threading
import pika
from sqlalchemy import select

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.ocr_document import OCRDocument, ProcessingStatus
from app.services.ocr_engine import ocr_service
from app.services.pdf_generator import pdf_generator_service
from app.utils.ohada_validator import ohada_validator

logging.basicConfig(
    level=settings.LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class OCRWorker:
    """OCR Worker for processing documents"""

    def __init__(self):
        self.connection = None
        self.channel = None
        self.running = False
        self.loop = asyncio.new_event_loop()
        self.loop_thread = threading.Thread(
            target=self._run_loop, name="ocr-worker-loop", daemon=True
        )

    def _run_loop(self):
        """Background event loop that processes async tasks."""
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def connect(self):
        """Connect to RabbitMQ"""
        try:
            logger.info(f"Connecting to RabbitMQ at {settings.RABBITMQ_HOST}:{settings.RABBITMQ_PORT}")

            credentials = pika.PlainCredentials(
                settings.RABBITMQ_USER,
                settings.RABBITMQ_PASSWORD
            )

            parameters = pika.ConnectionParameters(
                host=settings.RABBITMQ_HOST,
                port=settings.RABBITMQ_PORT,
                virtual_host=settings.RABBITMQ_VHOST,
                credentials=credentials,
                heartbeat=600,
                blocked_connection_timeout=300
            )

            self.connection = pika.BlockingConnection(parameters)
            self.channel = self.connection.channel()

            # Declare queues
            self.channel.queue_declare(
                queue=settings.OCR_QUEUE_NAME,
                durable=True,
                arguments={'x-max-priority': 10}
            )

            self.channel.queue_declare(
                queue=settings.OCR_PRIORITY_QUEUE,
                durable=True,
                arguments={'x-max-priority': 10}
            )

            # Set QoS
            self.channel.basic_qos(prefetch_count=settings.WORKER_PREFETCH_COUNT)

            logger.info("Connected to RabbitMQ successfully")

        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            raise

    def start(self):
        """Start consuming messages"""
        try:
            logger.info("Starting OCR worker...")
            self.running = True
            if not self.loop_thread.is_alive():
                self.loop_thread.start()

            # Consume from both queues (priority queue first)
            self.channel.basic_consume(
                queue=settings.OCR_PRIORITY_QUEUE,
                on_message_callback=self.on_message,
                auto_ack=False
            )

            self.channel.basic_consume(
                queue=settings.OCR_QUEUE_NAME,
                on_message_callback=self.on_message,
                auto_ack=False
            )

            logger.info(f"Worker started. Waiting for messages...")
            self.channel.start_consuming()

        except KeyboardInterrupt:
            logger.info("Worker stopped by user")
            self.stop()
        except Exception as e:
            logger.error(f"Worker error: {e}")
            self.stop()
            raise

    def stop(self):
        """Stop the worker"""
        logger.info("Stopping OCR worker...")
        self.running = False

        if self.channel:
            self.channel.stop_consuming()

        if self.connection:
            self.connection.close()

        if self.loop.is_running():
            self.loop.call_soon_threadsafe(self.loop.stop)
        if self.loop_thread.is_alive():
            self.loop_thread.join(timeout=2)

        logger.info("Worker stopped")

    def on_message(self, channel, method, properties, body):
        """
        Callback when message is received from queue
        """
        try:
            # Parse message
            message = json.loads(body)
            document_id = message.get('document_id')

            logger.info(f"Received OCR job for document: {document_id}")

            # Process document
            future = asyncio.run_coroutine_threadsafe(
                self.process_document(message), self.loop
            )
            future.result()

            # Acknowledge message
            channel.basic_ack(delivery_tag=method.delivery_tag)
            logger.info(f"Document processed successfully: {document_id}")

        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)

            # Reject and requeue if retries available
            retry_count = message.get('retry_count', 0)
            if retry_count < settings.WORKER_MAX_RETRIES:
                logger.info(f"Requeuing message (retry {retry_count + 1}/{settings.WORKER_MAX_RETRIES})")
                message['retry_count'] = retry_count + 1

                # Requeue with delay
                channel.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
            else:
                logger.error(f"Max retries reached. Moving to dead letter queue")
                channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

                # Update document status to failed
                future = asyncio.run_coroutine_threadsafe(
                    self.mark_failed(message.get('document_id'), str(e)),
                    self.loop
                )
                future.result()

    async def process_document(self, message: Dict[str, Any]):
        """
        Process a document with OCR

        Args:
            message: Job message containing document details
        """
        document_id = message.get('document_id')
        file_path = message.get('file_path')
        tenant_id = message.get('tenant_id')

        async with AsyncSessionLocal() as db:
            try:
                # Get document from database
                query = select(OCRDocument).where(OCRDocument.id == document_id)
                result = await db.execute(query)
                document = result.scalar_one_or_none()

                if not document:
                    logger.error(f"Document not found: {document_id}")
                    return

                # Update status to processing
                document.status = ProcessingStatus.PROCESSING
                await db.commit()

                # Run OCR
                logger.info(f"Running OCR on: {file_path}")
                ocr_result = await ocr_service.process_document(
                    file_path=file_path,
                    engine=message.get('ocr_engine')
                )

                if not ocr_result.get('success'):
                    raise Exception(f"OCR failed: {ocr_result.get('error')}")

                # Update document with OCR results
                document.extracted_text = ocr_result.get('text', '')
                document.word_count = ocr_result.get('word_count', 0)
                document.character_count = len(document.extracted_text)
                document.confidence_score = ocr_result.get('confidence_score')
                document.processing_time_ms = ocr_result.get('processing_time_ms')
                document.page_count = ocr_result.get('page_count', 1)

                # Generate markdown output
                markdown_output = self._generate_markdown(ocr_result)
                document.markdown_output = markdown_output

                # Extract structured data
                structured_data = self._extract_structured_data(ocr_result, message)
                document.structured_data = structured_data

                # Generate searchable PDF (if input is PDF)
                searchable_pdf_path = None
                if file_path.lower().endswith('.pdf'):
                    logger.info(f"Generating searchable PDF for: {file_path}")
                    pdf_result = await pdf_generator_service.generate_searchable_pdf(
                        input_pdf_path=file_path,
                        output_filename=f"{document.id}_searchable.pdf",
                        ocr_data=ocr_result
                    )

                    if pdf_result.get('success'):
                        searchable_pdf_path = pdf_result['output_path']
                        logger.info(f"Searchable PDF generated: {searchable_pdf_path}")

                        # Store path in document metadata
                        if document.metadata_json is None:
                            document.metadata_json = {}
                        document.metadata_json['searchable_pdf_path'] = searchable_pdf_path
                        document.metadata_json['searchable_pdf_size'] = pdf_result.get('file_size')
                    else:
                        logger.warning(f"Failed to generate searchable PDF: {pdf_result.get('error')}")

                # OHADA Validation if enabled
                if settings.ENABLE_OHADA_VALIDATION and message.get('enable_ohada_validation', True):
                    logger.info("Running OHADA validation")
                    validation_result = ohada_validator.validate_document(
                        structured_data,
                        country_code=message.get('country_code')
                    )

                    document.ohada_compliant = validation_result['is_compliant']
                    document.ohada_validation_errors = {
                        'errors': validation_result['errors'],
                        'warnings': validation_result['warnings']
                    }

                # Calculate quality score
                quality_score = self._calculate_quality_score(
                    ocr_result,
                    document.confidence_score
                )
                document.quality_score = quality_score

                # Determine if requires review
                requires_review = (
                    quality_score < settings.OCR_REQUIRES_REVIEW_THRESHOLD or
                    document.confidence_score < settings.OCR_MIN_CONFIDENCE or
                    not document.ohada_compliant
                )
                document.requires_human_review = requires_review

                # Update status
                if requires_review:
                    document.status = ProcessingStatus.REQUIRES_REVIEW
                else:
                    document.status = ProcessingStatus.COMPLETED

                await db.commit()

                logger.info(f"Document processed: {document_id} (quality: {quality_score:.2f}, review: {requires_review})")

                # TODO: Send notification to callback URL or webhook
                # TODO: Store files in MinIO (markdown, JSON)
                # TODO: Index for search (Elasticsearch)

            except Exception as e:
                logger.error(f"Error processing document {document_id}: {e}", exc_info=True)
                document.status = ProcessingStatus.FAILED
                document.error_message = str(e)
                document.retry_count += 1
                await db.commit()
                raise

    async def mark_failed(self, document_id: str, error_message: str):
        """Mark document as failed"""
        async with AsyncSessionLocal() as db:
            try:
                query = select(OCRDocument).where(OCRDocument.id == document_id)
                result = await db.execute(query)
                document = result.scalar_one_or_none()

                if document:
                    document.status = ProcessingStatus.FAILED
                    document.error_message = error_message
                    await db.commit()
                    logger.info(f"Document marked as failed: {document_id}")

            except Exception as e:
                logger.error(f"Error marking document as failed: {e}")

    def _generate_markdown(self, ocr_result: Dict[str, Any]) -> str:
        """Generate markdown output from OCR results"""
        text = ocr_result.get('text', '')

        # TODO: Enhance markdown generation
        # - Detect and format headers
        # - Preserve structure and tables
        # - Add metadata

        markdown = f"# OCR Document\n\n{text}"
        return markdown

    def _extract_structured_data(
        self,
        ocr_result: Dict[str, Any],
        message: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extract structured data from OCR results"""
        structured = {
            'text': ocr_result.get('text', ''),
            'word_count': ocr_result.get('word_count', 0),
            'confidence_score': ocr_result.get('confidence_score'),
            'pages': ocr_result.get('pages', [])
        }

        # TODO: Add entity extraction with spaCy
        # TODO: Add table detection and extraction
        # TODO: Add signature detection
        # TODO: Add financial data extraction

        return structured

    def _calculate_quality_score(
        self,
        ocr_result: Dict[str, Any],
        confidence_score: float
    ) -> float:
        """
        Calculate overall quality score for OCR results

        Factors:
        - Confidence score (40%)
        - Text length and readability (30%)
        - Structure detection (20%)
        - Error indicators (10%)
        """
        if confidence_score is None:
            return 0.0

        # Confidence component (40%)
        confidence_component = confidence_score * 0.4

        # Text length component (30%)
        word_count = ocr_result.get('word_count', 0)
        text_component = min(word_count / 100, 1.0) * 0.3

        # Structure component (20%)
        # TODO: Enhance with actual structure detection
        structure_component = 0.2

        # Error component (10%)
        # TODO: Detect common OCR errors
        error_component = 0.1

        quality_score = confidence_component + text_component + structure_component + error_component

        return min(max(quality_score, 0.0), 1.0)


def main():
    """Main entry point for worker"""
    logger.info(f"Starting {settings.APP_NAME} Worker")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Concurrency: {settings.WORKER_CONCURRENCY}")

    worker = OCRWorker()

    try:
        worker.connect()
        worker.start()
    except KeyboardInterrupt:
        logger.info("Worker stopped by user")
        worker.stop()
    except Exception as e:
        logger.error(f"Worker failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
