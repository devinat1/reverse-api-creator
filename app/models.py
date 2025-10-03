from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    BigInteger,
    Index,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.database import Base


class HARFile(Base):
    """Represents an uploaded HAR file."""

    __tablename__ = "har_files"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(
        UUID(as_uuid=True), unique=True, default=uuid4, nullable=False, index=True
    )
    filename = Column(String, nullable=False)
    s3_key = Column(String, nullable=False)
    s3_bucket = Column(String, nullable=False)
    status = Column(
        String, default="pending", nullable=False, index=True
    )  # pending, processing, completed, failed
    upload_timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    total_requests = Column(Integer, default=0)
    user_ip = Column(String, nullable=True)

    # Relationship
    requests = relationship(
        "Request", back_populates="har_file", cascade="all, delete-orphan"
    )


class Request(Base):
    """Represents an individual HTTP request from a HAR file."""

    __tablename__ = "requests"

    id = Column(Integer, primary_key=True, index=True)
    har_file_id = Column(
        Integer,
        ForeignKey("har_files.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Searchable fields
    url = Column(Text, nullable=False)
    domain = Column(String, nullable=False, index=True)
    path = Column(Text, nullable=False)
    method = Column(String, nullable=False, index=True)
    status_code = Column(Integer, nullable=True, index=True)
    timestamp = Column(DateTime, nullable=True, index=True)
    duration_ms = Column(Integer, nullable=True)
    content_type = Column(String, nullable=True, index=True)

    # Sizes
    request_size = Column(BigInteger, nullable=True)
    response_size = Column(BigInteger, nullable=True)

    # Searchable JSONB fields
    query_params = Column(JSONB, nullable=True)

    # Full request/response details
    request_headers = Column(JSONB, nullable=True)
    request_body = Column(Text, nullable=True)
    response_headers = Column(JSONB, nullable=True)
    response_body = Column(Text, nullable=True)

    # Relationship
    har_file = relationship("HARFile", back_populates="requests")

    # Indexes for full-text search
    __table_args__ = (
        Index(
            "idx_request_url_gin",
            url,
            postgresql_using="gin",
            postgresql_ops={"url": "gin_trgm_ops"},
        ),
        Index(
            "idx_request_domain_gin",
            domain,
            postgresql_using="gin",
            postgresql_ops={"domain": "gin_trgm_ops"},
        ),
        Index(
            "idx_request_path_gin",
            path,
            postgresql_using="gin",
            postgresql_ops={"path": "gin_trgm_ops"},
        ),
        Index("idx_request_query_params_gin", query_params, postgresql_using="gin"),
    )
