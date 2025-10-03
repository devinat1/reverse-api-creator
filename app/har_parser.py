import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse, parse_qs


class HARParser:
    """Parser for HAR (HTTP Archive) files."""

    @staticmethod
    def parse_har_file(har_content: str) -> Dict[str, Any]:
        """Parse HAR file content and extract metadata."""
        try:
            har_data = json.loads(har_content)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid HAR file: {e}")

        if "log" not in har_data:
            raise ValueError("Invalid HAR format: missing 'log' key")

        entries = har_data.get("log", {}).get("entries", [])

        return {
            "total_requests": len(entries),
            "entries": entries,
        }

    @staticmethod
    def extract_request_metadata(entry: Dict[str, Any]) -> Dict[str, Any]:
        """Extract searchable metadata from a HAR entry."""
        request = entry.get("request", {})
        response = entry.get("response", {})

        # Parse URL
        url = request.get("url", "")
        parsed_url = urlparse(url)
        domain = parsed_url.netloc
        path = parsed_url.path or "/"

        # Parse query parameters
        query_params = {}
        if parsed_url.query:
            query_params = {
                k: v[0] if len(v) == 1 else v
                for k, v in parse_qs(parsed_url.query).items()
            }

        # Extract timestamp
        started_datetime = entry.get("startedDateTime")
        timestamp = None
        if started_datetime:
            try:
                timestamp = datetime.fromisoformat(
                    started_datetime.replace("Z", "+00:00")
                )
            except (ValueError, AttributeError):
                pass

        # Extract method and status
        method = request.get("method", "GET").upper()
        status_code = response.get("status")

        # Extract duration
        time_ms = entry.get("time")
        duration_ms = int(time_ms) if time_ms is not None else None

        # Extract content type
        content_type = None
        response_headers = response.get("headers", [])
        for header in response_headers:
            if header.get("name", "").lower() == "content-type":
                content_type = header.get("value", "").split(";")[0].strip()
                break

        # Extract request/response sizes
        request_size = request.get("bodySize", 0)
        response_size = response.get("bodySize", 0)

        # Extract headers (exclude HTTP/2 pseudo-headers that start with ':')
        request_headers = {
            h.get("name"): h.get("value")
            for h in request.get("headers", [])
            if not h.get("name", "").startswith(":")
        }
        response_headers_dict = {
            h.get("name"): h.get("value")
            for h in response_headers
            if not h.get("name", "").startswith(":")
        }

        # Extract bodies
        request_body = HARParser._extract_body(request)
        response_body = HARParser._extract_body(response)

        return {
            "url": url,
            "domain": domain,
            "path": path,
            "method": method,
            "status_code": status_code,
            "timestamp": timestamp,
            "duration_ms": duration_ms,
            "content_type": content_type,
            "request_size": request_size if request_size >= 0 else None,
            "response_size": response_size if response_size >= 0 else None,
            "query_params": query_params if query_params else None,
            "request_headers": request_headers,
            "request_body": request_body,
            "response_headers": response_headers_dict,
            "response_body": response_body,
        }

    @staticmethod
    def _extract_body(request_or_response: Dict[str, Any]) -> Optional[str]:
        """Extract body content from request or response."""
        post_data = request_or_response.get("postData")
        if post_data:
            text = post_data.get("text")
            if text:
                return text

        content = request_or_response.get("content")
        if content:
            text = content.get("text")
            if text:
                return text

        return None

    @staticmethod
    def get_minimal_request_summary(metadata: Dict[str, Any]) -> str:
        """Generate minimal summary for LLM prompt (reduces tokens)."""
        method = metadata.get("method", "GET")
        path = metadata.get("path", "/")
        query_params = metadata.get("query_params", {})

        # Include query params if they exist
        if query_params:
            # Show first few query params
            params_str = "&".join(
                [f"{k}={v}" for k, v in list(query_params.items())[:2]]
            )
            if len(query_params) > 2:
                params_str += "..."
            return f"{method} {path}?{params_str}"

        return f"{method} {path}"
