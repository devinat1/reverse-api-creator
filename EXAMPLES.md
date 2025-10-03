# CloudCruise API Examples

## Complete Workflow Example

### 1. Upload HAR File

```bash
curl -X POST http://localhost:8000/upload-har \
  -F "file=@examples/sample.har"
```

Response:
```json
{
  "job_id": "abc123-def456-789",
  "message": "HAR file uploaded successfully and queued for processing",
  "status": "pending"
}
```

### 2. Check Processing Status

```bash
curl http://localhost:8000/status/abc123-def456-789
```

Response:
```json
{
  "job_id": "abc123-def456-789",
  "filename": "sample.har",
  "status": "completed",
  "total_requests": 3,
  "upload_timestamp": "2024-01-15T10:30:00"
}
```

### 3. Generate Curl Command (LLM-powered)

```bash
curl -X POST http://localhost:8000/generate-curl \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": "abc123-def456-789",
    "prompt": "Get the weather forecast for San Francisco",
    "max_candidates": 10
  }'
```

Response:
```json
{
  "curl_command": "curl 'https://api.weather.com/v1/forecast?city=San%20Francisco&days=7' \\\n  -H 'accept: application/json' \\\n  -H 'user-agent: Mozilla/5.0' \\\n  -H 'authorization: Bearer token123'",
  "matched_request": {
    "url": "https://api.weather.com/v1/forecast?city=San%20Francisco&days=7",
    "method": "GET",
    "domain": "api.weather.com",
    "path": "/v1/forecast",
    "status_code": 200,
    "content_type": "application/json"
  },
  "model_used": "o3-mini-2025-01-31"
}
```

### 4. Get Detailed Request Information

First, you need the request ID. You can get this from the matched_request or by querying the database directly.

```bash
curl http://localhost:8000/request/1/details
```

Response:
```json
{
  "request_id": 1,
  "url": "https://api.weather.com/v1/forecast?city=San%20Francisco&days=7",
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
      {
        "name": "city",
        "value": "San Francisco"
      },
      {
        "name": "days",
        "value": "7"
      }
    ],
    "headers": [
      {
        "name": "accept",
        "value": "application/json",
        "is_auth": false
      },
      {
        "name": "user-agent",
        "value": "Mozilla/5.0",
        "is_auth": false
      },
      {
        "name": "authorization",
        "value": "***",
        "is_auth": true
      }
    ],
    "body": null,
    "body_type": null
  },
  "response_info": {
    "status_code": 200,
    "content_type": "application/json",
    "size_bytes": 1024,
    "body_preview": "{\"city\":\"San Francisco\",\"forecast\":[...]}",
    "headers": {
      "content-type": "application/json",
      "cache-control": "max-age=3600"
    }
  },
  "timing": {
    "total_ms": 123,
    "dns_ms": null,
    "connect_ms": null,
    "send_ms": null,
    "wait_ms": null,
    "receive_ms": null
  }
}
```

### 5. Execute Request (with Parameter Overrides)

```bash
curl -X POST http://localhost:8000/execute-request \
  -H "Content-Type: application/json" \
  -d '{
    "request_id": 1,
    "overrides": {
      "query_params": {
        "city": "New York",
        "days": "5"
      },
      "headers": {
        "Authorization": "Bearer your-new-token-here"
      }
    },
    "follow_redirects": true,
    "timeout": 30
  }'
```

Success Response:
```json
{
  "success": true,
  "request": {
    "url": "https://api.weather.com/v1/forecast?city=New+York&days=5",
    "method": "GET",
    "headers": {
      "accept": "application/json",
      "user-agent": "Mozilla/5.0",
      "Authorization": "Bearer your-new-token-here"
    }
  },
  "response": {
    "status_code": 200,
    "status_text": "OK",
    "headers": {
      "content-type": "application/json",
      "cache-control": "max-age=3600",
      "content-length": "856"
    },
    "body": "{\"city\":\"New York\",\"forecast\":[{\"date\":\"2024-01-15\",\"temp\":45,\"conditions\":\"Partly Cloudy\"},...]}",
    "size_bytes": 856
  },
  "timing": {
    "execution_time_ms": 234
  }
}
```

## Error Handling Examples

### Authentication Error (401)

```bash
curl -X POST http://localhost:8000/execute-request \
  -H "Content-Type: application/json" \
  -d '{
    "request_id": 1,
    "overrides": {
      "headers": {
        "Authorization": "Bearer invalid-token"
      }
    }
  }'
```

Response:
```json
{
  "success": false,
  "request": {
    "url": "https://api.weather.com/v1/forecast?city=San+Francisco&days=7",
    "method": "GET"
  },
  "response": {
    "status_code": 401,
    "status_text": "Unauthorized",
    "headers": {
      "content-type": "application/json"
    },
    "body": "{\"error\":\"Invalid authentication token\"}"
  },
  "timing": {
    "execution_time_ms": 89
  },
  "error": {
    "type": "authentication_error",
    "message": "Authentication failed",
    "details": "{\"error\":\"Invalid authentication token\"}",
    "suggestions": [
      "Check your Authorization header is set correctly",
      "Verify your API key or token is valid",
      "Ensure the token hasn't expired"
    ]
  }
}
```

### Rate Limit Error (429)

Response:
```json
{
  "success": false,
  "request": {
    "url": "https://api.weather.com/v1/forecast",
    "method": "GET"
  },
  "response": {
    "status_code": 429,
    "status_text": "Too Many Requests",
    "headers": {
      "retry-after": "60"
    },
    "body": "Rate limit exceeded"
  },
  "timing": {
    "execution_time_ms": 45
  },
  "error": {
    "type": "rate_limit_error",
    "message": "Rate limit exceeded",
    "details": "Rate limit exceeded",
    "suggestions": [
      "Wait before making another request",
      "Check the Retry-After header for wait time",
      "Consider implementing exponential backoff"
    ]
  }
}
```

### Timeout Error

Response:
```json
{
  "success": false,
  "request": {
    "url": "https://slow-api.example.com/endpoint",
    "method": "GET"
  },
  "timing": {
    "execution_time_ms": 30000
  },
  "error": {
    "type": "timeout_error",
    "message": "Request timeout",
    "details": "Request took longer than 30 seconds",
    "suggestions": [
      "The server took too long to respond",
      "Try increasing the timeout value",
      "Check if the server is online and responsive"
    ]
  }
}
```

### Connection Error

Response:
```json
{
  "success": false,
  "request": {
    "url": "https://unreachable-server.example.com/api",
    "method": "GET"
  },
  "timing": {
    "execution_time_ms": 5234
  },
  "error": {
    "type": "connection_error",
    "message": "Connection failed",
    "details": "Failed to connect to host",
    "suggestions": [
      "Check your internet connection",
      "Verify the server URL is correct",
      "Ensure the server is online"
    ]
  }
}
```

## Advanced Use Cases

### POST Request with Body Override

```bash
curl -X POST http://localhost:8000/execute-request \
  -H "Content-Type: application/json" \
  -d '{
    "request_id": 2,
    "overrides": {
      "body": "{\"name\":\"Jane Smith\",\"email\":\"jane@example.com\",\"role\":\"admin\"}"
    }
  }'
```

### Execute Without Overrides (Original Request)

```bash
curl -X POST http://localhost:8000/execute-request \
  -H "Content-Type: application/json" \
  -d '{
    "request_id": 1
  }'
```

This executes the request exactly as it was captured in the HAR file.

### Custom Timeout

```bash
curl -X POST http://localhost:8000/execute-request \
  -H "Content-Type: application/json" \
  -d '{
    "request_id": 1,
    "timeout": 60
  }'
```

### Don't Follow Redirects

```bash
curl -X POST http://localhost:8000/execute-request \
  -H "Content-Type: application/json" \
  -d '{
    "request_id": 3,
    "follow_redirects": false
  }'
```

## Understanding Authentication Detection

The request analyzer automatically detects various authentication schemes:

### Bearer Token
```json
{
  "authentication": {
    "detected": true,
    "type": "bearer",
    "header_name": "Authorization",
    "value_pattern": "Bearer ***"
  }
}
```

### API Key
```json
{
  "authentication": {
    "detected": true,
    "type": "api_key",
    "header_name": "X-API-Key",
    "value_pattern": "***"
  }
}
```

### Basic Auth
```json
{
  "authentication": {
    "detected": true,
    "type": "basic",
    "header_name": "Authorization",
    "value_pattern": "Basic ***"
  }
}
```

### Cookie Auth
```json
{
  "authentication": {
    "detected": true,
    "type": "cookie",
    "header_name": "Cookie",
    "value_pattern": "***"
  }
}
```

### No Authentication
```json
{
  "authentication": {
    "detected": false,
    "type": null,
    "header_name": null,
    "value_pattern": null
  }
}
```

## Working with Different Body Types

### JSON Body
```json
{
  "parameters": {
    "body": {
      "name": "John Doe",
      "email": "john@example.com"
    },
    "body_type": "json"
  }
}
```

### Form Data
```json
{
  "parameters": {
    "body": {
      "username": "johndoe",
      "password": "***"
    },
    "body_type": "form"
  }
}
```

### Text Body
```json
{
  "parameters": {
    "body": "Plain text content",
    "body_type": "text"
  }
}
```

### Binary/Multipart
```json
{
  "parameters": {
    "body": "<multipart data>",
    "body_type": "multipart"
  }
}
```
