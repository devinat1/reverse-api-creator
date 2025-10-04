HAR file processing API

[Setup and Demo](https://youtu.be/qMCH0PkwJzE)

## Features

- **HAR File Upload**: Upload HAR files via REST API with rate limiting
- **URL to HAR Conversion**: Capture network traffic from live URLs using Playwright headless browser
- **Web UI**: Next.js frontend with drag-drop upload, request browsing, and curl generation
- **Event-Driven Processing**: Kafka-based async processing pipeline with 50MB message support
- **Storage**: S3/MinIO for raw HAR file storage
- **Metadata Indexing**: PostgreSQL with full-text search and GIN indexes
- **Advanced Filtering**: Intelligent pre-filtering that prioritizes API requests over static assets
- **LLM-Powered Matching**: Natural language query to find specific API requests
- **Curl Generation**: Automatic curl command generation with special character escaping
- **Request Analysis**: Automatic detection of authentication and parameters from HAR data
- **Request Execution**: Execute requests with parameter overrides and comprehensive error handling
- **Rate Limiting**: Redis-backed rate limiting per endpoint
- **Model Fallback**: Primary model (o3-mini) with gpt-4o fallback
- **Observability**: Helicone integration for LLM monitoring

## Architecture

```
Web UI (Next.js) → FastAPI → Kafka Topic → Consumer Worker
                      ↓                          ↓
                   Redis              ┌──────────┴────────┐
                (Rate Limit)          ↓                   ↓
                                  S3/MinIO           PostgreSQL
                                 (Raw HAR)           (Metadata)
```

## Quick Start

**Quick Option**: Use `make dev` to start infrastructure and initialize database, then run `make run-api` and `make run-consumer`. See `make help` for all commands. Run `yarn` followed by `yarn dev` in frontend to start the web client.

### Prerequisites

- Python 3.11+
- Docker and Docker Compose
- [uv](https://github.com/astral-sh/uv) package manager

### 1. Install Dependencies

```bash
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install project dependencies
uv sync
```

### 2. Start Infrastructure

```bash
# Start PostgreSQL, MinIO, Kafka, and Redis
docker-compose up -d

# Wait for services to be healthy
docker-compose ps
```

### 3. Configure Environment

```bash
# Copy example env file
cp .env.example .env

# Edit .env and add your OpenAI API key
# OPENAI_API_KEY=your-key-here
```

### 4. Initialize Database

```bash
# Create tables with pg_trgm extension for full-text search
make init-db
or: uv run python scripts/init_db.py
```

### 5. Setup Frontend (Optional)

```bash
cd frontend
npm install (or yarn)
npm run dev (or yarn dev)
cd ..
```

### 6. Run the Application

```bash
# Terminal 1: Start the API server
uv run python app/main.py

# Terminal 2: Start the Kafka consumer
uv run python app/consumer.py

# Terminal 3 (optional): Start the web UI
cd frontend && npm run dev (or yarn dev)
# Access UI at http://localhost:3000
```

## Rate Limits

- `/upload-har`: 10 requests/minute per IP
- `/url-to-har`: 10 requests/minute per IP
- `/generate-curl`: 20 requests/minute per IP
- `/execute-request`: 30 requests/minute per IP

## Project Structure

```
cloudcruise/
├── app/
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration settings
│   ├── database.py          # SQLAlchemy setup
│   ├── models.py            # Database models
│   ├── har_parser.py        # HAR file parsing
│   ├── url_to_har.py        # URL to HAR conversion (Playwright)
│   ├── storage.py           # S3/MinIO storage service
│   ├── kafka_producer.py    # Kafka producer
│   ├── consumer.py          # Kafka consumer worker
│   ├── request_filter.py    # PostgreSQL pre-filtering
│   ├── request_analyzer.py  # Request analysis (auth, params)
│   ├── request_executor.py  # HTTP request execution
│   ├── llm_service.py       # LLM matching with fallback
│   ├── curl_generator.py    # Curl command generation
│   └── rate_limit.py        # Rate limiting setup
├── frontend/                # Next.js web UI
│   ├── src/
│   │   ├── app/             # App router pages
│   │   └── components/      # React components
│   └── package.json         # Frontend dependencies
├── docker-compose.yml       # Local development stack
├── pyproject.toml          # Python dependencies
└── .env.example            # Environment variables template
```

## How It Works

### 1. Upload Flow
1. User uploads HAR file to `/upload-har`
2. API validates file and creates database record
3. Message published to Kafka topic `har-uploads`
4. Consumer picks up message and processes asynchronously
5. HAR file stored in S3/MinIO
6. Request metadata extracted and saved to PostgreSQL

### 2. Curl Generation Flow
1. User provides `job_id` and natural language `prompt`
2. **PostgreSQL pre-filtering**: Extract keywords, filter requests by URL/domain/method
3. Narrow down to top 10-20 candidates
4. **LLM matching**: Send minimal candidates to o3-mini
5. LLM returns best match index
6. If o3-mini fails → Fallback to gpt-4o
7. Retrieve full request details from PostgreSQL
8. Generate formatted curl command
9. Return curl command to user

### 3. Token Optimization
- **Pre-filtering** reduces 100s of requests to ~10 candidates
- **Minimal prompt** sends only method + path (not full headers/bodies)
- Typical LLM prompt: <200 tokens vs thousands
- Cost-effective and fast

## Development

### Run Tests

```bash
uv run pytest
```

### Load Testing

Load test suite with Locust covering HAR uploads, curl generation, request execution, and rate limiting.

```bash
# Start Locust web UI
locust -f tests/load/locustfile.py --host=http://localhost:8000
# Open http://localhost:8089

# Headless mode
locust -f tests/load/locustfile.py --host=http://localhost:8000 \
  --users 50 --spawn-rate 5 --run-time 60s --headless

# Test specific scenario
locust -f tests/load/locustfile.py --host=http://localhost:8000 \
  RateLimitTestUser --users 20 --spawn-rate 10 --headless
```

**Available user classes:**
- `NormalUser` - Mixed operations (uploads + status checks)
- `CurlGenerationUser` - LLM curl generation testing
- `RateLimitTestUser` - Rate limit testing (aggressive)
- `RequestExecutionUser` - Request execution testing
- `MixedWorkloadUser` - Realistic mixed workload (default)

### Management Consoles

- **API Docs**: http://localhost:8000/docs (Swagger UI)
- **MinIO**: http://localhost:9001 (minioadmin/minioadmin)
- **Kafka UI**: http://localhost:8080
- **Web UI**: http://localhost:3000
## API Endpoints

### Health Check

```bash
GET /health

curl http://localhost:8000/health

Response:
{
  "status": "healthy"
}
```

### Convert URL to HAR

```bash
POST /url-to-har
Content-Type: application/json

curl -X POST http://localhost:8000/url-to-har \
  -H "Content-Type: application/json" \
  -d '{"url": "https://api.example.com"}'

Response:
{
  "job_id": "123e4567-e89b-12d3-a456-426614174000",
  "message": "URL converted to HAR successfully and queued for processing",
  "status": "pending"
}
```

### Upload HAR File

```bash
POST /upload-har
Content-Type: multipart/form-data

curl -X POST http://localhost:8000/upload-har \
  -F "file=@example.har"

Response:
{
  "job_id": "123e4567-e89b-12d3-a456-426614174000",
  "message": "HAR file uploaded successfully and queued for processing",
  "status": "pending"
}
```

### Check Processing Status

```bash
GET /status/{job_id}

curl http://localhost:8000/status/123e4567-e89b-12d3-a456-426614174000

Response:
{
  "job_id": "123e4567-e89b-12d3-a456-426614174000",
  "filename": "example.har",
  "status": "completed",
  "total_requests": 42,
  "upload_timestamp": "2024-01-15T10:30:00"
}
```

### Get Job Requests

```bash
GET /job/{job_id}/requests

curl http://localhost:8000/job/123e4567-e89b-12d3-a456-426614174000/requests

Response:
{
  "job_id": "123e4567-e89b-12d3-a456-426614174000",
  "total_requests": 42,
  "requests": [
    {
      "request_id": 123,
      "url": "https://api.weather.com/v1/forecast?city=SF",
      "method": "GET",
      "domain": "api.weather.com",
      "status_code": 200,
      "content_type": "application/json"
    },
    ...
  ]
}
```

### Generate Curl Command

```bash
POST /generate-curl

curl -X POST http://localhost:8000/generate-curl \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": "123e4567-e89b-12d3-a456-426614174000",
    "prompt": "Return the API that fetches the weather of San Francisco",
    "max_candidates": 10
  }'

Response:
{
  "curl_command": "curl 'https://api.weather.com/v1/forecast?city=SF' \\\n  -H 'accept: application/json' \\\n  ...",
  "matched_request": {
    "url": "https://api.weather.com/v1/forecast?city=SF",
    "method": "GET",
    "domain": "api.weather.com",
    "path": "/v1/forecast",
    "status_code": 200,
    "content_type": "application/json"
  },
  "model_used": "o3-mini-2025-01-31"
}
```

### Download Curl as File

```bash
POST /generate-curl/download

curl -X POST http://localhost:8000/generate-curl/download \
  -H "Content-Type: application/json" \
  -d '{"job_id": "...", "prompt": "..."}' \
  -o curl_command.txt
```

### Get Request Details

```bash
GET /request/{request_id}/details

curl http://localhost:8000/request/123/details

Response:
{
  "request_id": 123,
  "url": "https://api.weather.com/v1/forecast?city=San+Francisco",
  "method": "GET",
  "domain": "api.weather.com",
  "path": "/v1/forecast",
  "authentication": {
    "detected": true,
    "type": "bearer",
    "header_name": "Authorization",
    "value_pattern": "Bearer ***"
  },
  "parameters": {
    "query": [
      {"name": "city", "value": "San Francisco"},
      {"name": "days", "value": "7"}
    ],
    "headers": [
      {"name": "accept", "value": "application/json", "is_auth": false},
      {"name": "authorization", "value": "***", "is_auth": true}
    ],
    "body": null,
    "body_type": null
  },
  "response_info": {
    "status_code": 200,
    "content_type": "application/json",
    "size_bytes": 1024,
    "body_preview": "{\"city\":\"San Francisco\"...}"
  },
  "timing": {
    "total_ms": 123
  }
}
```

### Execute Request

```bash
POST /execute-request

# Execute with parameter overrides
curl -X POST http://localhost:8000/execute-request \
  -H "Content-Type: application/json" \
  -d '{
    "request_id": 123,
    "overrides": {
      "query_params": {"city": "New York", "days": "5"},
      "headers": {"Authorization": "Bearer new-token"}
    },
    "follow_redirects": true,
    "timeout": 30
  }'

Success Response:
{
  "success": true,
  "request": {
    "url": "https://api.weather.com/v1/forecast?city=New+York&days=5",
    "method": "GET",
    "headers": {...}
  },
  "response": {
    "status_code": 200,
    "status_text": "OK",
    "headers": {"content-type": "application/json", ...},
    "body": "...",
    "size_bytes": 1024
  },
  "timing": {
    "execution_time_ms": 145
  }
}

Error Response (e.g., authentication failure):
{
  "success": false,
  "request": {
    "url": "https://api.weather.com/v1/forecast?city=New+York",
    "method": "GET"
  },
  "response": {
    "status_code": 401,
    "status_text": "Unauthorized",
    "headers": {...},
    "body": "Invalid API key"
  },
  "timing": {
    "execution_time_ms": 89
  },
  "error": {
    "type": "authentication_error",
    "message": "Authentication failed",
    "details": "Invalid API key",
    "suggestions": [
      "Check your Authorization header is set correctly",
      "Verify your API key or token is valid",
      "Ensure the token hasn't expired"
    ]
  }
}
```

## License

MIT
