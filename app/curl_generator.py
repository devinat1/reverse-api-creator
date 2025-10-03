import json
from typing import Dict, Any

from app.models import Request


class CurlGenerator:
    """Service for generating curl commands from HAR request data."""

    @staticmethod
    def generate_curl_command(request: Request) -> str:
        """
        Generate a curl command from a Request object.

        Args:
            request: Request object from database

        Returns:
            Formatted curl command as string
        """
        lines = [f"curl '{request.url}' \\"]

        # Add method if not GET
        if request.method and request.method.upper() != "GET":
            lines.append(f"  -X {request.method} \\")

        # Add headers (filter out HTTP/2 pseudo-headers, accept-encoding, and sort alphabetically)
        if request.request_headers:
            # Filter and sort headers
            headers_to_add = []
            for name, value in request.request_headers.items():
                # Skip HTTP/2 pseudo-headers (start with ':')
                if name.startswith(':'):
                    continue
                # Skip accept-encoding (causes compressed/binary responses in curl)
                if name.lower() == 'accept-encoding':
                    continue
                headers_to_add.append((name, value))

            # Sort headers alphabetically by name (case-insensitive)
            headers_to_add.sort(key=lambda x: x[0].lower())

            # Add sorted headers
            for name, value in headers_to_add:
                # Escape single quotes in header values
                escaped_value = value.replace("'", "'\\''")
                lines.append(f"  -H '{name}: {escaped_value}' \\")

        # Add request body if present
        if request.request_body:
            # Escape single quotes in body
            escaped_body = request.request_body.replace("'", "'\\''")
            lines.append(f"  --data-raw '{escaped_body}' \\")

        # Remove trailing backslash from last line
        if lines[-1].endswith(" \\"):
            lines[-1] = lines[-1][:-2]

        return "\n".join(lines)

    @staticmethod
    def generate_curl_with_metadata(request: Request) -> Dict[str, Any]:
        """
        Generate curl command with additional metadata.

        Args:
            request: Request object from database

        Returns:
            Dictionary with curl command and metadata
        """
        curl_command = CurlGenerator.generate_curl_command(request)

        return {
            "curl_command": curl_command,
            "metadata": {
                "url": request.url,
                "method": request.method,
                "domain": request.domain,
                "path": request.path,
                "status_code": request.status_code,
                "content_type": request.content_type,
            },
        }
