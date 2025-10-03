# CloudCruise Quick Start Guide

## Setup (5 minutes)

### 1. Install Dependencies
```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install project dependencies
make install
```

### 2. Configure Environment
```bash
# Copy example env file
cp .env.example .env

# Edit .env and add your OpenAI API key
# Required: OPENAI_API_KEY=sk-...
```

### 3. Start Infrastructure & Initialize Database
```bash
# One command to start everything
make dev

# This will:
# - Start PostgreSQL, MinIO, Kafka, and Redis in Docker
# - Initialize database with required extensions and tables
```

### 4. Run the Application
```bash
# Terminal 1: Start API server
make run-api

# Terminal 2: Start Kafka consumer (in another terminal)
make run-consumer
```

## Test It Out

### Upload a HAR file
```bash
curl -X POST http://localhost:8000/upload-har \
  -F "file=@examples/sample.har"

# Response:
# {
#   "job_id": "abc123...",
#   "message": "HAR file uploaded successfully and queued for processing",
#   "status": "pending"
# }
```

### Check Status
```bash
curl http://localhost:8000/status/abc123...

# Response:
# {
#   "job_id": "abc123...",
#   "filename": "sample.har",
#   "status": "completed",
#   "total_requests": 3,
#   "upload_timestamp": "2024-01-15T10:30:00"
# }
```

### Generate Curl Command (LLM-powered!)
```bash
curl -X POST http://localhost:8000/generate-curl \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": "abc123...",
    "prompt": "Get the weather forecast for San Francisco",
    "max_candidates": 10
  }'

# Response:
# {
#   "curl_command": "curl 'https://api.weather.com/v1/forecast?city=San%20Francisco&days=7' \\\n  -H 'accept: application/json' \\\n  ...",
#   "matched_request": {
#     "url": "https://api.weather.com/v1/forecast?city=San%20Francisco&days=7",
#     "method": "GET",
#     ...
#   },
#   "model_used": "o3-mini-2025-01-31"
# }
```

## Access Web Interfaces

- **API Documentation**: http://localhost:8000/docs (Swagger UI)
- **MinIO Console**: http://localhost:9001 (minioadmin/minioadmin)

## How It Works

1. **Upload**: HAR file → FastAPI → Kafka topic
2. **Process**: Kafka consumer → Parse HAR → Store in S3 → Save metadata to PostgreSQL
3. **Query**: Natural language prompt → PostgreSQL filters → LLM matches → Generate curl

## Common Commands

```bash
# Start infrastructure
make start-infra

# Stop infrastructure
make stop-infra

# Initialize database
make init-db

# Clean everything (including volumes)
make clean

# See all available commands
make help
```

## Troubleshooting

**Database connection error?**
```bash
# Make sure infrastructure is running
docker-compose ps

# Restart if needed
make stop-infra && make start-infra
```

**Kafka consumer not processing?**
```bash
# Check Kafka is running
docker-compose logs kafka

# Check consumer logs
# (Look at the terminal where you ran make run-consumer)
```

**LLM errors?**
```bash
# Make sure OPENAI_API_KEY is set in .env
grep OPENAI_API_KEY .env

# Check API key is valid
```

## Next Steps

- Upload your own HAR files (export from browser DevTools → Network tab → Save as HAR)
- Try different natural language prompts to match requests
- Explore the generated curl commands
- Check out the full [README.md](README.md) for more details

## Architecture Overview

```
┌─────────┐      ┌─────────┐      ┌───────┐
│ FastAPI │─────▶│  Kafka  │─────▶│Worker │
└─────────┘      └─────────┘      └───┬───┘
                                      │
                          ┌───────────┴────────────┐
                          ▼                        ▼
                    ┌──────────┐           ┌────────────┐
                    │   S3/    │           │ PostgreSQL │
                    │  MinIO   │           │  (Metadata)│
                    └──────────┘           └────────────┘
```

LLM Flow:
```
User Prompt → PostgreSQL Filter → o3-mini → (fallback: gpt-4o) → Curl Command
```
