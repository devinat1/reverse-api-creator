import boto3
from botocore.exceptions import ClientError
from datetime import datetime
from typing import Optional
from uuid import UUID

from app.config import settings


class StorageService:
    """Service for interacting with S3/MinIO storage."""

    def __init__(self):
        self.s3_client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            region_name=settings.s3_region,
        )
        self.bucket_name = settings.s3_bucket_name

    def ensure_bucket_exists(self) -> None:
        """Create bucket if it doesn't exist."""
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code")
            if error_code == "404":
                self.s3_client.create_bucket(Bucket=self.bucket_name)
            else:
                raise

    def upload_har_file(self, job_id: UUID, filename: str, content: bytes) -> str:
        """
        Upload HAR file to S3/MinIO.

        Args:
            job_id: Unique job identifier
            filename: Original filename
            content: HAR file content as bytes

        Returns:
            S3 key of uploaded file
        """
        # Generate S3 key with organized structure: hars/{date}/{job_id}.har
        date_str = datetime.utcnow().strftime("%Y-%m-%d")
        s3_key = f"hars/{date_str}/{job_id}.har"

        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=content,
                ContentType="application/json",
                Metadata={
                    "original_filename": filename,
                    "job_id": str(job_id),
                },
            )
            return s3_key
        except ClientError as e:
            raise Exception(f"Failed to upload HAR file to S3: {e}")

    def download_har_file(self, s3_key: str) -> Optional[str]:
        """
        Download HAR file from S3/MinIO.

        Args:
            s3_key: S3 key of the file

        Returns:
            HAR file content as string, or None if not found
        """
        try:
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=s3_key)
            return response["Body"].read().decode("utf-8")
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code")
            if error_code == "NoSuchKey":
                return None
            raise Exception(f"Failed to download HAR file from S3: {e}")

    def delete_har_file(self, s3_key: str) -> bool:
        """
        Delete HAR file from S3/MinIO.

        Args:
            s3_key: S3 key of the file

        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=s3_key)
            return True
        except ClientError as e:
            raise Exception(f"Failed to delete HAR file from S3: {e}")


# Singleton instance
storage_service = StorageService()
