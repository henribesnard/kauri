"""
Utility to publish OCR jobs to RabbitMQ.
"""
import json
import logging
from typing import Any, Dict

import pika

from app.core.config import settings

logger = logging.getLogger(__name__)


class OCRQueuePublisher:
    """Simple RabbitMQ publisher for OCR jobs."""

    def __init__(self):
        credentials = pika.PlainCredentials(
            settings.RABBITMQ_USER,
            settings.RABBITMQ_PASSWORD,
        )
        self._parameters = pika.ConnectionParameters(
            host=settings.RABBITMQ_HOST,
            port=settings.RABBITMQ_PORT,
            virtual_host=settings.RABBITMQ_VHOST,
            credentials=credentials,
            heartbeat=600,
            blocked_connection_timeout=300,
        )

    def publish_job(self, payload: Dict[str, Any], priority: int = 5) -> None:
        """
        Publish a job to the appropriate OCR queue.

        Args:
            payload: Message body (must be JSON serializable)
            priority: 1 (highest) .. 10 (lowest)
        """
        queue_name = (
            settings.OCR_PRIORITY_QUEUE
            if priority <= 3
            else settings.OCR_QUEUE_NAME
        )

        connection = None
        channel = None

        try:
            connection = pika.BlockingConnection(self._parameters)
            channel = connection.channel()

            channel.queue_declare(
                queue=queue_name,
                durable=True,
                arguments={"x-max-priority": 10},
            )

            channel.basic_publish(
                exchange="",
                routing_key=queue_name,
                body=json.dumps(payload),
                properties=pika.BasicProperties(
                    delivery_mode=2,  # Persist message
                    priority=max(0, min(priority, 10)),
                ),
            )

            logger.info(
                "Published OCR job %s to %s",
                payload.get("document_id"),
                queue_name,
            )

        except Exception:
            logger.error(
                "Failed to publish OCR job %s", payload.get("document_id"),
                exc_info=True,
            )
            raise
        finally:
            if channel and channel.is_open:
                channel.close()
            if connection and connection.is_open:
                connection.close()


ocr_queue_publisher = OCRQueuePublisher()
