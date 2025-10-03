"""URL to HAR conversion service using Playwright."""

import asyncio
import json
import logging
import os
import tempfile
from typing import Optional
from urllib.parse import urlparse

from playwright.async_api import (
    async_playwright,
    TimeoutError as PlaywrightTimeoutError,
)

from app.config import settings

logger = logging.getLogger(__name__)


class URLToHARConverter:
    """Converts a URL to HAR format by loading it in a browser and capturing network traffic."""

    @staticmethod
    def validate_url(url: str) -> tuple[bool, Optional[str]]:
        """
        Validate URL format and check against blocked domains.

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check if URL has valid format
        try:
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                return (
                    False,
                    "Invalid URL format. Must include protocol (http/https) and domain.",
                )

            # Only allow http and https
            if parsed.scheme not in ["http", "https"]:
                return False, "Only HTTP and HTTPS protocols are allowed."

            # Check against blocked domains
            blocked_domains = []
            if settings.url_to_har_blocked_domains:
                blocked_domains = [
                    d.strip().lower()
                    for d in settings.url_to_har_blocked_domains.split(",")
                    if d.strip()
                ]

            domain = parsed.netloc.lower()
            for blocked in blocked_domains:
                if blocked in domain:
                    return False, f"Domain '{domain}' is blocked for URL conversion."

            return True, None

        except Exception as e:
            return False, f"Invalid URL: {str(e)}"

    @staticmethod
    async def convert_url_to_har(url: str) -> dict:
        """
        Load a URL in a headless browser and capture network traffic as HAR.

        Args:
            url: The URL to load

        Returns:
            Dictionary containing:
                - success: bool
                - har_content: str (JSON string of HAR data) if successful
                - error: str if failed

        Raises:
            Exception: If Playwright fails to start or crashes
        """
        # Validate URL first
        is_valid, error_msg = URLToHARConverter.validate_url(url)
        if not is_valid:
            return {"success": False, "error": error_msg}

        logger.info(f"Starting URL to HAR conversion for: {url}")

        # Create a temporary file for the HAR output
        har_file_path = None
        try:
            # Create temporary file
            har_fd, har_file_path = tempfile.mkstemp(suffix=".har")
            os.close(
                har_fd
            )  # Close the file descriptor, Playwright will write to the path

            async with async_playwright() as p:
                # Launch browser in headless mode
                browser = await p.chromium.launch(headless=True)

                # Create a new browser context with HAR recording enabled
                context = await browser.new_context(
                    record_har_path=har_file_path,
                    record_har_content="omit",  # Don't include response bodies to reduce size
                )

                # Create a new page
                page = await context.new_page()

                try:
                    # Navigate to the URL with timeout
                    wait_until = settings.url_to_har_wait_until
                    if wait_until not in ["load", "domcontentloaded", "networkidle"]:
                        wait_until = "networkidle"

                    await page.goto(
                        url,
                        wait_until=wait_until,
                        timeout=settings.url_to_har_timeout
                        * 1000,  # Convert to milliseconds
                    )

                    # Give a small additional delay to ensure all requests are captured
                    await asyncio.sleep(1)

                    logger.info(f"Successfully loaded URL: {url}")

                except PlaywrightTimeoutError:
                    logger.warning(f"Timeout loading URL: {url}")
                    await context.close()
                    await browser.close()
                    return {
                        "success": False,
                        "error": f"Timeout loading URL after {settings.url_to_har_timeout} seconds",
                    }

                except Exception as e:
                    logger.error(f"Error loading URL {url}: {e}")
                    await context.close()
                    await browser.close()
                    return {"success": False, "error": f"Failed to load URL: {str(e)}"}

                # Close context and browser - this triggers HAR file write
                await context.close()
                await browser.close()

            # Read the HAR file
            try:
                with open(har_file_path, "r", encoding="utf-8") as f:
                    har_content = f.read()

                logger.info(f"Successfully converted URL to HAR: {url}")

                return {
                    "success": True,
                    "har_content": har_content,
                }

            except Exception as e:
                logger.error(f"Error reading HAR file for {url}: {e}")
                return {"success": False, "error": f"Failed to read HAR file: {str(e)}"}

        except Exception as e:
            logger.error(f"Playwright error for URL {url}: {e}")
            return {"success": False, "error": f"Browser automation failed: {str(e)}"}

        finally:
            # Clean up temporary file
            if har_file_path and os.path.exists(har_file_path):
                try:
                    os.unlink(har_file_path)
                except Exception as e:
                    logger.warning(f"Failed to delete temporary HAR file: {e}")
