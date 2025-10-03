import json
import re
from typing import Dict, Any, List, Optional
from urllib.parse import parse_qs, urlparse

from app.models import Request


class RequestAnalyzer:
    """Analyzes HAR request data to extract authentication, parameters, and metadata."""

    @staticmethod
    def detect_authentication(headers: Dict[str, str]) -> Dict[str, Any]:
        """
        Detect authentication type from request headers.

        Args:
            headers: Request headers dictionary

        Returns:
            Dictionary with authentication details
        """
        if not headers:
            return {
                "detected": False,
                "type": None,
                "header_name": None,
                "value_pattern": None,
            }

        # Normalize header names (case-insensitive)
        normalized_headers = {k.lower(): (k, v) for k, v in headers.items()}

        # Check for Authorization header
        if "authorization" in normalized_headers:
            original_name, value = normalized_headers["authorization"]
            value_lower = value.lower()

            if value_lower.startswith("bearer "):
                return {
                    "detected": True,
                    "type": "bearer",
                    "header_name": original_name,
                    "value_pattern": "Bearer ***",
                }
            elif value_lower.startswith("basic "):
                return {
                    "detected": True,
                    "type": "basic",
                    "header_name": original_name,
                    "value_pattern": "Basic ***",
                }
            else:
                return {
                    "detected": True,
                    "type": "custom",
                    "header_name": original_name,
                    "value_pattern": "***",
                }

        # Check for common API key headers
        api_key_headers = ["x-api-key", "api-key", "apikey", "x-apikey"]
        for header in api_key_headers:
            if header in normalized_headers:
                original_name, value = normalized_headers[header]
                return {
                    "detected": True,
                    "type": "api_key",
                    "header_name": original_name,
                    "value_pattern": "***",
                }

        # Check for Cookie header
        if "cookie" in normalized_headers:
            original_name, value = normalized_headers["cookie"]
            return {
                "detected": True,
                "type": "cookie",
                "header_name": original_name,
                "value_pattern": "***",
            }

        # Check for any header containing auth/token/key in name
        for header_lower, (original_name, value) in normalized_headers.items():
            if any(keyword in header_lower for keyword in ["auth", "token", "key"]):
                return {
                    "detected": True,
                    "type": "custom",
                    "header_name": original_name,
                    "value_pattern": "***",
                }

        return {
            "detected": False,
            "type": None,
            "header_name": None,
            "value_pattern": None,
        }

    @staticmethod
    def extract_parameters(request: Request) -> Dict[str, Any]:
        """
        Extract all parameters from request (query, headers, body).

        Args:
            request: Request object from database

        Returns:
            Dictionary with categorized parameters
        """
        parameters = {
            "query": [],
            "headers": [],
            "body": None,
            "body_type": None,
        }

        # Extract query parameters
        if request.query_params:
            for name, value in request.query_params.items():
                parameters["query"].append({
                    "name": name,
                    "value": value,
                })

        # Extract headers (mask sensitive ones)
        if request.request_headers:
            sensitive_headers = [
                "authorization", "cookie", "x-api-key", "api-key",
                "apikey", "x-apikey", "token", "x-auth-token"
            ]

            for name, value in request.request_headers.items():
                is_auth = name.lower() in sensitive_headers or \
                         any(keyword in name.lower() for keyword in ["auth", "token", "key"])

                parameters["headers"].append({
                    "name": name,
                    "value": "***" if is_auth else value,
                    "is_auth": is_auth,
                })

        # Extract body parameters
        if request.request_body:
            # Determine body type from content-type header
            content_type = None
            if request.request_headers:
                content_type = request.request_headers.get("content-type") or \
                              request.request_headers.get("Content-Type")

            if content_type:
                content_type_lower = content_type.lower()

                if "application/json" in content_type_lower:
                    parameters["body_type"] = "json"
                    try:
                        parameters["body"] = json.loads(request.request_body)
                    except json.JSONDecodeError:
                        parameters["body"] = request.request_body

                elif "application/x-www-form-urlencoded" in content_type_lower:
                    parameters["body_type"] = "form"
                    try:
                        parsed = parse_qs(request.request_body)
                        parameters["body"] = {k: v[0] if len(v) == 1 else v for k, v in parsed.items()}
                    except:
                        parameters["body"] = request.request_body

                elif "multipart/form-data" in content_type_lower:
                    parameters["body_type"] = "multipart"
                    parameters["body"] = "<multipart data>"

                elif "text/" in content_type_lower:
                    parameters["body_type"] = "text"
                    parameters["body"] = request.request_body

                else:
                    parameters["body_type"] = "binary"
                    parameters["body"] = "<binary data>"
            else:
                # Try to parse as JSON if no content-type
                try:
                    parameters["body"] = json.loads(request.request_body)
                    parameters["body_type"] = "json"
                except:
                    parameters["body"] = request.request_body
                    parameters["body_type"] = "text"

        return parameters

    @staticmethod
    def get_response_info(request: Request) -> Dict[str, Any]:
        """
        Extract response information from request.

        Args:
            request: Request object from database

        Returns:
            Dictionary with response details
        """
        body_preview = None
        if request.response_body:
            # Limit preview to first 500 characters
            body_preview = request.response_body[:500]
            if len(request.response_body) > 500:
                body_preview += "..."

        return {
            "status_code": request.status_code,
            "content_type": request.content_type,
            "size_bytes": request.response_size,
            "body_preview": body_preview,
            "headers": request.response_headers if request.response_headers else {},
        }

    @staticmethod
    def analyze_request(request: Request) -> Dict[str, Any]:
        """
        Perform full analysis of a request.

        Args:
            request: Request object from database

        Returns:
            Complete analysis dictionary
        """
        auth_info = RequestAnalyzer.detect_authentication(request.request_headers or {})
        parameters = RequestAnalyzer.extract_parameters(request)
        response_info = RequestAnalyzer.get_response_info(request)

        # Extract timing data if available (this would come from HAR entry)
        timing = {
            "total_ms": request.duration_ms,
            "dns_ms": None,
            "connect_ms": None,
            "send_ms": None,
            "wait_ms": None,
            "receive_ms": None,
        }

        return {
            "request_id": request.id,
            "url": request.url,
            "method": request.method,
            "domain": request.domain,
            "path": request.path,
            "authentication": auth_info,
            "parameters": parameters,
            "response_info": response_info,
            "timing": timing,
        }
