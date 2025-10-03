import logging
from contextlib import asynccontextmanager
from uuid import UUID, uuid4

from typing import Optional
from fastapi import (
    FastAPI,
    File,
    UploadFile,
    Depends,
    HTTPException,
    Request as FastAPIRequest,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from slowapi.errors import RateLimitExceeded
from sqlalchemy.orm import Session

from app.config import settings
from app.curl_generator import CurlGenerator
from app.database import get_db
from app.kafka_producer import kafka_producer
from app.llm_service import llm_service
from app.models import HARFile, Request
from app.rate_limit import limiter, rate_limit_exceeded_handler
from app.request_analyzer import RequestAnalyzer
from app.request_executor import RequestExecutor
from app.request_filter import RequestFilter
from app.storage import storage_service
from app.url_to_har import URLToHARConverter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    # Startup
    logger.info("Starting CloudCruise API...")
    storage_service.ensure_bucket_exists()
    await kafka_producer.start()
    logger.info("CloudCruise API started successfully")

    yield

    # Shutdown
    logger.info("Shutting down CloudCruise API...")
    await kafka_producer.stop()
    logger.info("CloudCruise API shut down successfully")


# Create FastAPI app
app = FastAPI(
    title="CloudCruise HAR API",
    description="HAR file processing API with LLM-powered curl generation",
    version="0.1.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],  # Frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)


# Request/Response models
class UploadResponse(BaseModel):
    job_id: str
    message: str
    status: str


class StatusResponse(BaseModel):
    job_id: str
    filename: str
    status: str
    total_requests: int
    upload_timestamp: str


class GenerateCurlRequest(BaseModel):
    job_id: str
    prompt: str
    max_candidates: int = 10


class GenerateCurlResponse(BaseModel):
    curl_command: str
    matched_request: dict
    request_id: int
    model_used: str


class RequestDetailsResponse(BaseModel):
    request_id: int
    url: str
    method: str
    domain: str
    path: str
    authentication: dict
    parameters: dict
    response_info: dict
    timing: dict


class ExecuteRequestRequest(BaseModel):
    request_id: int
    overrides: Optional[dict] = None
    follow_redirects: bool = True
    timeout: Optional[int] = None


class ExecuteRequestResponse(BaseModel):
    success: bool
    request: dict
    response: Optional[dict] = None
    timing: dict
    error: Optional[dict] = None


class URLToHARRequest(BaseModel):
    url: str


class URLToHARResponse(BaseModel):
    job_id: str
    message: str
    status: str


# Endpoints
@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "CloudCruise HAR API", "version": "0.1.0"}


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.post("/upload-har", response_model=UploadResponse)
@limiter.limit(settings.rate_limit_upload)
async def upload_har(
    request: FastAPIRequest,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Upload a HAR file for processing.

    The file will be published to Kafka for async processing.
    """
    # Validate file type
    if not file.filename.endswith(".har"):
        raise HTTPException(status_code=400, detail="File must be a .har file")

    # Read file content
    try:
        content = await file.read()
        har_content = content.decode("utf-8")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read file: {e}")

    # Generate job ID
    job_id = uuid4()

    # Get user IP
    user_ip = request.client.host if request.client else None

    # Create database record
    har_file = HARFile(
        job_id=job_id,
        filename=file.filename,
        s3_key="",  # Will be set by consumer
        s3_bucket=settings.s3_bucket_name,
        status="pending",
        user_ip=user_ip,
    )
    db.add(har_file)
    db.commit()

    # Publish to Kafka
    try:
        await kafka_producer.publish_har_upload_event(
            job_id=job_id,
            filename=file.filename,
            har_content=har_content,
            user_ip=user_ip,
        )
    except Exception as e:
        har_file.status = "failed"
        db.commit()
        raise HTTPException(status_code=500, detail=f"Failed to publish event: {e}")

    return UploadResponse(
        job_id=str(job_id),
        message="HAR file uploaded successfully and queued for processing",
        status="pending",
    )


@app.post("/url-to-har", response_model=URLToHARResponse)
@limiter.limit(settings.rate_limit_upload)
async def url_to_har(
    request: FastAPIRequest,
    body: URLToHARRequest,
    db: Session = Depends(get_db),
):
    """
    Convert a URL to HAR format by loading it in a browser.

    The URL will be loaded in a headless browser, network traffic will be captured,
    and the result will be processed just like an uploaded HAR file.
    """
    # Check if URL-to-HAR conversion is enabled
    if not settings.enable_url_to_har:
        raise HTTPException(
            status_code=403,
            detail="URL to HAR conversion is disabled",
        )

    # Convert URL to HAR
    try:
        result = await URLToHARConverter.convert_url_to_har(body.url)

        if not result["success"]:
            raise HTTPException(
                status_code=400,
                detail=result.get("error", "Failed to convert URL to HAR"),
            )

        har_content = result["har_content"]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error converting URL to HAR: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to convert URL to HAR: {str(e)}",
        )

    # Generate job ID
    job_id = uuid4()

    # Get user IP
    user_ip = request.client.host if request.client else None

    # Extract filename from URL (use domain name)
    from urllib.parse import urlparse

    parsed_url = urlparse(body.url)
    filename = f"{parsed_url.netloc.replace(':', '_')}.har"

    # Create database record
    har_file = HARFile(
        job_id=job_id,
        filename=filename,
        s3_key="",  # Will be set by consumer
        s3_bucket=settings.s3_bucket_name,
        status="pending",
        user_ip=user_ip,
    )
    db.add(har_file)
    db.commit()

    # Publish to Kafka
    try:
        await kafka_producer.publish_har_upload_event(
            job_id=job_id,
            filename=filename,
            har_content=har_content,
            user_ip=user_ip,
        )
    except Exception as e:
        har_file.status = "failed"
        db.commit()
        raise HTTPException(status_code=500, detail=f"Failed to publish event: {e}")

    return URLToHARResponse(
        job_id=str(job_id),
        message=f"URL converted to HAR successfully and queued for processing",
        status="pending",
    )


@app.get("/status/{job_id}", response_model=StatusResponse)
async def get_status(job_id: str, db: Session = Depends(get_db)):
    """Get processing status of a HAR file upload."""
    try:
        job_uuid = UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job_id format")

    har_file = db.query(HARFile).filter(HARFile.job_id == job_uuid).first()

    if not har_file:
        raise HTTPException(status_code=404, detail="Job not found")

    return StatusResponse(
        job_id=str(har_file.job_id),
        filename=har_file.filename,
        status=har_file.status,
        total_requests=har_file.total_requests,
        upload_timestamp=har_file.upload_timestamp.isoformat(),
    )


class RequestListItem(BaseModel):
    id: int
    method: str
    url: str
    domain: str
    path: str
    status_code: Optional[int]
    content_type: Optional[str]
    timestamp: Optional[str]
    duration_ms: Optional[int]


class RequestListResponse(BaseModel):
    requests: list[RequestListItem]
    total: int


@app.get("/job/{job_id}/requests", response_model=RequestListResponse)
async def get_job_requests(job_id: str, db: Session = Depends(get_db)):
    """Get all requests for a specific job."""
    try:
        job_uuid = UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job_id format")

    har_file = db.query(HARFile).filter(HARFile.job_id == job_uuid).first()

    if not har_file:
        raise HTTPException(status_code=404, detail="Job not found")

    # Get all requests for this HAR file, ordered by timestamp
    requests = (
        db.query(Request)
        .filter(Request.har_file_id == har_file.id)
        .order_by(Request.timestamp.desc())
        .all()
    )

    # Convert to response format
    request_items = [
        RequestListItem(
            id=req.id,
            method=req.method,
            url=req.url,
            domain=req.domain,
            path=req.path,
            status_code=req.status_code,
            content_type=req.content_type,
            timestamp=req.timestamp.isoformat() if req.timestamp else None,
            duration_ms=req.duration_ms,
        )
        for req in requests
    ]

    return RequestListResponse(
        requests=request_items,
        total=len(request_items),
    )


@app.post("/generate-curl", response_model=GenerateCurlResponse)
@limiter.limit(settings.rate_limit_curl_gen)
async def generate_curl(
    request: FastAPIRequest,
    body: GenerateCurlRequest,
    db: Session = Depends(get_db),
):
    """
    Generate a curl command based on natural language prompt.

    Uses LLM to match the prompt to a request from the HAR file.
    """
    try:
        job_uuid = UUID(body.job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job_id format")

    # Get HAR file
    har_file = db.query(HARFile).filter(HARFile.job_id == job_uuid).first()

    if not har_file:
        raise HTTPException(status_code=404, detail="Job not found")

    if har_file.status != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"HAR file processing not completed. Current status: {har_file.status}",
        )

    # Pre-filter requests using PostgreSQL
    filtered_requests = RequestFilter.filter_requests(
        db=db,
        har_file_id=har_file.id,
        prompt=body.prompt,
        max_results=body.max_candidates,
    )

    if not filtered_requests:
        raise HTTPException(
            status_code=404,
            detail="No matching requests found for the given prompt",
        )

    # Create minimal candidates for LLM
    candidates = RequestFilter.create_minimal_candidates(filtered_requests)

    # Use LLM to match the best request
    try:
        match_result = await llm_service.match_request(
            user_prompt=body.prompt,
            candidates=candidates,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM matching failed: {e}")

    # Retrieve full request details
    request_id = match_result["request_id"]
    matched_request = db.query(Request).filter(Request.id == request_id).first()

    if not matched_request:
        raise HTTPException(
            status_code=500, detail="Matched request not found in database"
        )

    # Generate curl command
    curl_data = CurlGenerator.generate_curl_with_metadata(matched_request)

    return GenerateCurlResponse(
        curl_command=curl_data["curl_command"],
        matched_request=curl_data["metadata"],
        request_id=request_id,
        model_used=match_result["model_used"],
    )


@app.post("/generate-curl/download")
@limiter.limit(settings.rate_limit_curl_gen)
async def generate_curl_download(
    request: FastAPIRequest,
    body: GenerateCurlRequest,
    db: Session = Depends(get_db),
):
    """
    Generate and download curl command as a text file.
    """
    # Reuse the generate_curl logic
    result = await generate_curl(request, body, db)

    return PlainTextResponse(
        content=result.curl_command,
        headers={
            "Content-Disposition": f"attachment; filename=curl_command.txt",
        },
    )


@app.get("/request/{request_id}/details", response_model=RequestDetailsResponse)
async def get_request_details(
    request_id: int,
    db: Session = Depends(get_db),
):
    """
    Get detailed information about a specific request.

    Analyzes the request to extract:
    - Authentication requirements (detected from headers)
    - Available parameters (query, headers, body)
    - Response information
    - Timing metrics
    """
    # Get request from database
    request = db.query(Request).filter(Request.id == request_id).first()

    if not request:
        raise HTTPException(status_code=404, detail="Request not found")

    # Analyze request
    analysis = RequestAnalyzer.analyze_request(request)

    return RequestDetailsResponse(**analysis)


@app.post("/execute-request", response_model=ExecuteRequestResponse)
@limiter.limit("30/minute")
async def execute_request(
    request: FastAPIRequest,
    body: ExecuteRequestRequest,
    db: Session = Depends(get_db),
):
    """
    Execute an HTTP request with optional parameter overrides.

    Features:
    - Parameter substitution (query params, headers, body)
    - Comprehensive error handling
    - Detailed error classification with suggestions
    - Safety checks (blocked domains)

    The request will be executed as-is from the HAR file, with any
    overrides applied.
    """
    # Check if request execution is enabled
    if not settings.enable_request_execution:
        raise HTTPException(
            status_code=403,
            detail="Request execution is disabled",
        )

    # Get request from database
    db_request = db.query(Request).filter(Request.id == body.request_id).first()

    if not db_request:
        raise HTTPException(status_code=404, detail="Request not found")

    # Parse blocked domains
    blocked_domains = []
    if settings.blocked_domains:
        blocked_domains = [
            d.strip() for d in settings.blocked_domains.split(",") if d.strip()
        ]

    # Create executor
    timeout = body.timeout or settings.request_execution_timeout
    executor = RequestExecutor(
        timeout=timeout,
        max_response_size=settings.max_response_size,
        blocked_domains=blocked_domains,
    )

    # Execute request
    result = await executor.execute_request(
        request=db_request,
        overrides=body.overrides,
        follow_redirects=body.follow_redirects,
    )

    return ExecuteRequestResponse(**result)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
    )
