from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration settings."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Database
    database_url: str = "postgresql://postgres:postgres@localhost:5432/cloudcruise"

    # S3/MinIO
    s3_endpoint_url: str = "http://localhost:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket_name: str = "har-files"
    s3_region: str = "us-east-1"

    # Kafka
    kafka_bootstrap_servers: str = "localhost:9094"
    kafka_topic_har_uploads: str = "har-uploads"
    kafka_consumer_group: str = "har-processor"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Rate Limiting
    rate_limit_upload: str = "10/minute"
    rate_limit_curl_gen: str = "20/minute"

    # LLM
    openai_api_key: str = ""
    helicone_api_key: str = ""
    llm_primary_model: str = "o3-mini-2025-01-31"
    llm_fallback_model: str = "gpt-4o-2024-08-06"
    llm_max_candidates: int = 10
    llm_timeout: int = 10

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # Request Execution
    request_execution_timeout: int = 30
    max_response_size: int = 10485760  # 10MB
    enable_request_execution: bool = True
    blocked_domains: str = ""  # Comma-separated list of blocked domains

    # URL to HAR Conversion
    enable_url_to_har: bool = True
    url_to_har_timeout: int = 30  # Timeout for page load in seconds
    url_to_har_blocked_domains: str = (
        ""  # Comma-separated list of blocked domains for URL conversion
    )
    url_to_har_wait_until: str = "networkidle"  # load, domcontentloaded, networkidle


settings = Settings()
