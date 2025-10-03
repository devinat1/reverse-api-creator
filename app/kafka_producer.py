import json
import logging
from typing import Any, Dict
from uuid import UUID

from aiokafka import AIOKafkaProducer

from app.config import settings

logger = logging.getLogger(__name__)


class KafkaProducerService:
    """Kafka producer for publishing HAR upload events."""

    def __init__(self):
        self.bootstrap_servers = settings.kafka_bootstrap_servers
        self.topic = settings.kafka_topic_har_uploads
        self.producer: AIOKafkaProducer | None = None

    async def start(self):
        """Start the Kafka producer."""
        self.producer = AIOKafkaProducer(
            bootstrap_servers=self.bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            max_request_size=52428800,  # 50MB (default is 1MB)
        )
        await self.producer.start()
        logger.info("Kafka producer started")

    async def stop(self):
        """Stop the Kafka producer."""
        if self.producer:
            await self.producer.stop()
            logger.info("Kafka producer stopped")

    async def publish_har_upload_event(
        self,
        job_id: UUID,
        filename: str,
        har_content: str,
        user_ip: str | None = None,
    ) -> None:
        """
        Publish HAR upload event to Kafka topic.

        Args:
            job_id: Unique job identifier
            filename: Original filename
            har_content: HAR file content as string
            user_ip: Optional user IP address
        """
        if not self.producer:
            raise RuntimeError("Kafka producer not started")

        message = {
            "job_id": str(job_id),
            "filename": filename,
            "har_content": har_content,
            "user_ip": user_ip,
            "timestamp": None,  # Will be set by Kafka
        }

        try:
            await self.producer.send_and_wait(self.topic, value=message)
            logger.info(f"Published HAR upload event for job_id: {job_id}")
        except Exception as e:
            logger.error(f"Failed to publish HAR upload event: {e}")
            raise


# Singleton instance
kafka_producer = KafkaProducerService()
