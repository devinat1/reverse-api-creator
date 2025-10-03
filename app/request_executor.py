import httpx
import logging
import time
from typing import Dict, Any, Optional, List
from urllib.parse import urlencode, urlparse

from app.models import Request

logger = logging.getLogger(__name__)


class RequestExecutionError(Exception):
    """Custom exception for request execution errors."""
    pass


class RequestExecutor:
    """Executes HTTP requests with comprehensive error handling."""

    def __init__(
        self,
        timeout: int = 30,
        max_response_size: int = 10 * 1024 * 1024,  # 10MB
        blocked_domains: Optional[List[str]] = None,
    ):
        self.timeout = timeout
        self.max_response_size = max_response_size
        self.blocked_domains = blocked_domains or []

    def _is_domain_blocked(self, url: str) -> bool:
        """Check if domain is in blocklist."""
        if not self.blocked_domains:
            return False

        parsed = urlparse(url)
        domain = parsed.netloc.lower()

        for blocked in self.blocked_domains:
            if blocked.lower() in domain:
                return True

        return False

    def _classify_error(
        self,
        error: Exception,
        status_code: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Classify error and provide helpful suggestions.

        Args:
            error: The exception that occurred
            status_code: HTTP status code if available

        Returns:
            Structured error information
        """
        error_info = {
            "type": "unknown_error",
            "message": str(error),
            "details": None,
            "suggestions": [],
        }

        # HTTP Status Code Errors
        if status_code:
            if status_code == 400:
                error_info.update({
                    "type": "bad_request",
                    "message": "Bad request - invalid parameters",
                    "suggestions": [
                        "Check that all required parameters are provided",
                        "Verify parameter values are in the correct format",
                        "Review the API documentation for parameter requirements",
                    ],
                })
            elif status_code == 401:
                error_info.update({
                    "type": "authentication_error",
                    "message": "Authentication failed",
                    "suggestions": [
                        "Check your Authorization header is set correctly",
                        "Verify your API key or token is valid",
                        "Ensure the token hasn't expired",
                    ],
                })
            elif status_code == 403:
                error_info.update({
                    "type": "authorization_error",
                    "message": "Access forbidden - insufficient permissions",
                    "suggestions": [
                        "Verify you have permission to access this resource",
                        "Check if your API key has the required scopes",
                        "Ensure your account has the necessary privileges",
                    ],
                })
            elif status_code == 404:
                error_info.update({
                    "type": "not_found",
                    "message": "Resource not found",
                    "suggestions": [
                        "Check that the URL is correct",
                        "Verify the resource ID exists",
                        "Ensure the endpoint path is valid",
                    ],
                })
            elif status_code == 429:
                error_info.update({
                    "type": "rate_limit_error",
                    "message": "Rate limit exceeded",
                    "suggestions": [
                        "Wait before making another request",
                        "Check the Retry-After header for wait time",
                        "Consider implementing exponential backoff",
                    ],
                })
            elif 400 <= status_code < 500:
                error_info.update({
                    "type": "client_error",
                    "message": f"Client error: {status_code}",
                    "suggestions": [
                        "Review the request parameters and headers",
                        "Check the API documentation",
                    ],
                })
            elif 500 <= status_code < 600:
                error_info.update({
                    "type": "server_error",
                    "message": f"Server error: {status_code}",
                    "suggestions": [
                        "The server is experiencing issues",
                        "Try again later",
                        "Contact the API provider if the issue persists",
                    ],
                })

        # Network Errors
        elif isinstance(error, httpx.TimeoutException):
            error_info.update({
                "type": "timeout_error",
                "message": "Request timeout",
                "details": str(error),
                "suggestions": [
                    "The server took too long to respond",
                    "Try increasing the timeout value",
                    "Check if the server is online and responsive",
                ],
            })
        elif isinstance(error, httpx.ConnectError):
            error_info.update({
                "type": "connection_error",
                "message": "Connection failed",
                "details": str(error),
                "suggestions": [
                    "Check your internet connection",
                    "Verify the server URL is correct",
                    "Ensure the server is online",
                ],
            })
        elif isinstance(error, httpx.ConnectTimeout):
            error_info.update({
                "type": "connection_timeout",
                "message": "Connection timeout",
                "details": str(error),
                "suggestions": [
                    "The server took too long to establish a connection",
                    "Check if the server is reachable",
                    "Verify there are no firewall issues",
                ],
            })
        elif isinstance(error, httpx.RemoteProtocolError):
            error_info.update({
                "type": "protocol_error",
                "message": "Protocol error",
                "details": str(error),
                "suggestions": [
                    "The server sent an invalid response",
                    "This may be a server-side issue",
                    "Contact the API provider",
                ],
            })
        elif isinstance(error, httpx.TooManyRedirects):
            error_info.update({
                "type": "redirect_error",
                "message": "Too many redirects",
                "details": str(error),
                "suggestions": [
                    "The server is redirecting too many times",
                    "Check the URL for redirect loops",
                ],
            })
        elif isinstance(error, (httpx.InvalidURL, httpx.UnsupportedProtocol)):
            error_info.update({
                "type": "invalid_url",
                "message": "Invalid URL",
                "details": str(error),
                "suggestions": [
                    "Check the URL format",
                    "Ensure the protocol (http/https) is correct",
                ],
            })

        return error_info

    async def execute_request(
        self,
        request: Request,
        overrides: Optional[Dict[str, Any]] = None,
        follow_redirects: bool = True,
    ) -> Dict[str, Any]:
        """
        Execute an HTTP request with error handling.

        Args:
            request: Request object from database
            overrides: Optional parameter overrides
            follow_redirects: Whether to follow HTTP redirects

        Returns:
            Dictionary with execution results
        """
        overrides = overrides or {}

        # Build URL with query parameters
        url = request.url
        if overrides.get("query_params"):
            parsed = urlparse(request.url)
            # Use override query params
            query_string = urlencode(overrides["query_params"])
            url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            if query_string:
                url = f"{url}?{query_string}"

        # Check if domain is blocked
        if self._is_domain_blocked(url):
            return {
                "success": False,
                "error": {
                    "type": "blocked_domain",
                    "message": "Domain is blocked",
                    "details": "This domain is in the blocklist and cannot be accessed",
                    "suggestions": ["Contact administrator to unblock this domain"],
                },
            }

        # Build headers (exclude HTTP/2 pseudo-headers)
        headers = {
            k: v for k, v in (request.request_headers or {}).items()
            if not k.startswith(':')
        }
        if overrides.get("headers"):
            # Also filter overrides
            filtered_overrides = {
                k: v for k, v in overrides["headers"].items()
                if not k.startswith(':')
            }
            headers.update(filtered_overrides)

        # Build body
        body = None
        if request.method.upper() in ["POST", "PUT", "PATCH"]:
            if overrides.get("body") is not None:
                body = overrides["body"]
            else:
                body = request.request_body

        # Record start time
        start_time = time.time()

        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                follow_redirects=follow_redirects,
            ) as client:
                # Execute request
                response = await client.request(
                    method=request.method,
                    url=url,
                    headers=headers,
                    content=body,
                )

                # Calculate execution time
                execution_time_ms = int((time.time() - start_time) * 1000)

                # Check response size
                response_size = len(response.content)
                if response_size > self.max_response_size:
                    logger.warning(f"Response size {response_size} exceeds max {self.max_response_size}")

                # Get response body as text (handle encoding errors)
                try:
                    response_body = response.text
                except:
                    response_body = "<binary data>"

                # Success response
                return {
                    "success": True,
                    "request": {
                        "url": url,
                        "method": request.method,
                        "headers": {k: v for k, v in headers.items()},
                    },
                    "response": {
                        "status_code": response.status_code,
                        "status_text": response.reason_phrase,
                        "headers": dict(response.headers),
                        "body": response_body,
                        "size_bytes": response_size,
                    },
                    "timing": {
                        "execution_time_ms": execution_time_ms,
                    },
                }

        except httpx.HTTPStatusError as e:
            # HTTP error response (4xx, 5xx)
            execution_time_ms = int((time.time() - start_time) * 1000)

            try:
                error_body = e.response.text
            except:
                error_body = "<binary data>"

            error_info = self._classify_error(e, status_code=e.response.status_code)
            error_info["details"] = error_body

            return {
                "success": False,
                "request": {
                    "url": url,
                    "method": request.method,
                },
                "response": {
                    "status_code": e.response.status_code,
                    "status_text": e.response.reason_phrase,
                    "headers": dict(e.response.headers),
                    "body": error_body,
                },
                "timing": {
                    "execution_time_ms": execution_time_ms,
                },
                "error": error_info,
            }

        except Exception as e:
            # Other errors (network, timeout, etc.)
            execution_time_ms = int((time.time() - start_time) * 1000)

            error_info = self._classify_error(e)

            return {
                "success": False,
                "request": {
                    "url": url,
                    "method": request.method,
                },
                "timing": {
                    "execution_time_ms": execution_time_ms,
                },
                "error": error_info,
            }
