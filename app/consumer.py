import asyncio
import json
import logging
from uuid import UUID

from aiokafka import AIOKafkaConsumer
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.har_parser import HARParser
from app.models import HARFile, Request
from app.storage import storage_service

logger = logging.getLogger(__name__)


class KafkaConsumerService:
    """Kafka consumer for processing HAR upload events."""

    def __init__(self):
        self.bootstrap_servers = settings.kafka_bootstrap_servers
        self.topic = settings.kafka_topic_har_uploads
        self.group_id = settings.kafka_consumer_group
        self.consumer: AIOKafkaConsumer | None = None
        self.running = False

    async def start(self):
        """Start the Kafka consumer."""
        self.consumer = AIOKafkaConsumer(
            self.topic,
            bootstrap_servers=self.bootstrap_servers,
            group_id=self.group_id,
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            auto_offset_reset="earliest",
        )
        await self.consumer.start()
        self.running = True
        logger.info("Kafka consumer started")

    async def stop(self):
        """Stop the Kafka consumer."""
        self.running = False
        if self.consumer:
            await self.consumer.stop()
            logger.info("Kafka consumer stopped")

    async def consume(self):
        """Consume and process messages from Kafka topic."""
        if not self.consumer:
            raise RuntimeError("Kafka consumer not started")

        try:
            async for message in self.consumer:
                if not self.running:
                    break

                try:
                    await self._process_message(message.value)
                except Exception as e:
                    logger.error(f"Error processing message: {e}", exc_info=True)

        except Exception as e:
            logger.error(f"Error in consume loop: {e}", exc_info=True)

    async def _process_message(self, message: dict):
        """Process a single HAR upload message."""
        job_id_str = message.get("job_id")
        filename = message.get("filename")
        har_content = message.get("har_content")
        user_ip = message.get("user_ip")

        if not all([job_id_str, filename, har_content]):
            logger.error("Invalid message: missing required fields")
            return

        job_id = UUID(job_id_str)
        logger.info(f"Processing HAR upload for job_id: {job_id}")

        db = SessionLocal()
        try:
            # Update status to processing
            har_file = db.query(HARFile).filter(HARFile.job_id == job_id).first()
            if har_file:
                har_file.status = "processing"
                db.commit()

            # Parse HAR file
            parser = HARParser()
            parsed_data = parser.parse_har_file(har_content)

            # Upload to S3/MinIO
            s3_key = storage_service.upload_har_file(
                job_id=job_id,
                filename=filename,
                content=har_content.encode("utf-8"),
            )

            # Update HAR file record
            if not har_file:
                har_file = HARFile(
                    job_id=job_id,
                    filename=filename,
                    s3_key=s3_key,
                    s3_bucket=settings.s3_bucket_name,
                    user_ip=user_ip,
                    total_requests=parsed_data["total_requests"],
                    status="processing",
                )
                db.add(har_file)
                db.commit()
                db.refresh(har_file)
            else:
                har_file.s3_key = s3_key
                har_file.s3_bucket = settings.s3_bucket_name
                har_file.total_requests = parsed_data["total_requests"]
                db.commit()

            # Extract and save request metadata
            for entry in parsed_data["entries"]:
                try:
                    metadata = parser.extract_request_metadata(entry)
                    request = Request(
                        har_file_id=har_file.id,
                        **metadata,
                    )
                    db.add(request)
                except Exception as e:
                    logger.error(f"Error extracting request metadata: {e}")
                    continue

            db.commit()

            # Update status to completed
            har_file.status = "completed"
            db.commit()

            logger.info(f"Successfully processed HAR upload for job_id: {job_id}")

        except Exception as e:
            logger.error(f"Error processing HAR file: {e}", exc_info=True)
            if har_file:
                har_file.status = "failed"
                db.commit()
        finally:
            db.close()


async def run_consumer():
    """Run the Kafka consumer."""
    # Ensure S3 bucket exists
    storage_service.ensure_bucket_exists()

    consumer_service = KafkaConsumerService()
    await consumer_service.start()

    try:
        await consumer_service.consume()
    finally:
        await consumer_service.stop()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    asyncio.run(run_consumer())
