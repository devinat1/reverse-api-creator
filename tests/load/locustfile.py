"""
Load testing suite for CloudCruise HAR API.

This file contains different load test scenarios for testing:
- HAR file uploads and Kafka throughput
- Curl generation with LLM integration
- Request execution
- Rate limiting behavior

Usage:
    # Run with web UI (navigate to http://localhost:8089)
    locust -f tests/load/locustfile.py --host=http://localhost:8000

    # Headless mode with specific users and duration
    locust -f tests/load/locustfile.py --host=http://localhost:8000 \
           --users 50 --spawn-rate 5 --run-time 60s --headless

    # Test specific user class
    locust -f tests/load/locustfile.py --host=http://localhost:8000 \
           RateLimitTestUser --users 20 --spawn-rate 10 --headless
"""

import json
import os
import random
import time
from pathlib import Path

from locust import HttpUser, TaskSet, task, between, events


# Get the path to test data
TEST_DATA_DIR = Path(__file__).parent / "test_data"
SMALL_HAR_PATH = TEST_DATA_DIR / "small_test.har"
LARGE_HAR_PATH = TEST_DATA_DIR / "large_test.har"


class HARUploadTasks(TaskSet):
    """Task set for testing HAR file uploads."""

    def on_start(self):
        """Initialize test data."""
        # Load HAR files into memory
        with open(SMALL_HAR_PATH, "r") as f:
            self.small_har_content = f.read()
        with open(LARGE_HAR_PATH, "r") as f:
            self.large_har_content = f.read()

        # Track job IDs for status checking
        self.job_ids = []

    @task(3)
    def upload_small_har(self):
        """Upload a small HAR file (most common scenario)."""
        files = {
            "file": ("small_test.har", self.small_har_content, "application/json")
        }

        with self.client.post(
            "/upload-har",
            files=files,
            catch_response=True,
            name="/upload-har (small)"
        ) as response:
            if response.status_code == 200:
                data = response.json()
                self.job_ids.append(data["job_id"])
                response.success()
            elif response.status_code == 429:
                # Rate limit hit - this is expected behavior
                response.success()
            else:
                response.failure(f"Unexpected status code: {response.status_code}")

    @task(1)
    def upload_large_har(self):
        """Upload a larger HAR file (stress test)."""
        files = {
            "file": ("large_test.har", self.large_har_content, "application/json")
        }

        with self.client.post(
            "/upload-har",
            files=files,
            catch_response=True,
            name="/upload-har (large)"
        ) as response:
            if response.status_code == 200:
                data = response.json()
                self.job_ids.append(data["job_id"])
                response.success()
            elif response.status_code == 429:
                response.success()
            else:
                response.failure(f"Unexpected status code: {response.status_code}")

    @task(2)
    def check_status(self):
        """Check the status of uploaded HAR files."""
        if not self.job_ids:
            return

        job_id = random.choice(self.job_ids)
        with self.client.get(
            f"/status/{job_id}",
            catch_response=True,
            name="/status/{job_id}"
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 404:
                # Job might not be created yet
                response.success()
            else:
                response.failure(f"Unexpected status code: {response.status_code}")


class CurlGenerationTasks(TaskSet):
    """Task set for testing curl generation with LLM."""

    def on_start(self):
        """Set up test by uploading a HAR file first."""
        with open(SMALL_HAR_PATH, "r") as f:
            har_content = f.read()

        # Upload HAR file and wait for processing
        files = {"file": ("test.har", har_content, "application/json")}
        response = self.client.post("/upload-har", files=files)

        if response.status_code == 200:
            self.job_id = response.json()["job_id"]
            # Wait for processing to complete
            time.sleep(2)
        else:
            self.job_id = None

    @task
    def generate_curl_command(self):
        """Generate curl command from natural language prompt."""
        if not self.job_id:
            return

        prompts = [
            "get all users",
            "create a new user",
            "search for products",
            "create an order",
            "get user profile"
        ]

        payload = {
            "job_id": self.job_id,
            "prompt": random.choice(prompts),
            "max_candidates": 10
        }

        with self.client.post(
            "/generate-curl",
            json=payload,
            catch_response=True,
            name="/generate-curl"
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 429:
                # Rate limit hit
                response.success()
            elif response.status_code == 400:
                # Job might still be processing
                response.success()
            elif response.status_code == 404:
                # No matching requests
                response.success()
            else:
                response.failure(f"Unexpected status code: {response.status_code}")


class RateLimitTestTasks(TaskSet):
    """Task set specifically for testing rate limits."""

    def on_start(self):
        """Initialize test data."""
        with open(SMALL_HAR_PATH, "r") as f:
            self.har_content = f.read()
        self.rate_limit_hits = 0
        self.successful_requests = 0

    @task
    def rapid_fire_uploads(self):
        """Send rapid requests to test rate limiting."""
        files = {"file": ("test.har", self.har_content, "application/json")}

        with self.client.post(
            "/upload-har",
            files=files,
            catch_response=True,
            name="/upload-har (rate limit test)"
        ) as response:
            if response.status_code == 200:
                self.successful_requests += 1
                response.success()
            elif response.status_code == 429:
                self.rate_limit_hits += 1
                # Mark as success since hitting rate limit is expected behavior
                response.success()
            else:
                response.failure(f"Unexpected status code: {response.status_code}")


class RequestExecutionTasks(TaskSet):
    """Task set for testing request execution."""

    def on_start(self):
        """Set up test by uploading a HAR file and getting a request ID."""
        with open(SMALL_HAR_PATH, "r") as f:
            har_content = f.read()

        # Upload HAR file
        files = {"file": ("test.har", har_content, "application/json")}
        response = self.client.post("/upload-har", files=files)

        if response.status_code == 200:
            self.job_id = response.json()["job_id"]
            # Wait for processing
            time.sleep(2)

            # Get requests for this job
            requests_response = self.client.get(f"/job/{self.job_id}/requests")
            if requests_response.status_code == 200:
                requests_data = requests_response.json()
                if requests_data["requests"]:
                    self.request_id = requests_data["requests"][0]["id"]
                else:
                    self.request_id = None
            else:
                self.request_id = None
        else:
            self.job_id = None
            self.request_id = None

    @task(2)
    def get_request_details(self):
        """Get detailed information about a request."""
        if not self.request_id:
            return

        with self.client.get(
            f"/request/{self.request_id}/details",
            catch_response=True,
            name="/request/{id}/details"
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 404:
                response.success()
            else:
                response.failure(f"Unexpected status code: {response.status_code}")

    @task(1)
    def execute_request(self):
        """Execute a request from the HAR file."""
        if not self.request_id:
            return

        payload = {
            "request_id": self.request_id,
            "follow_redirects": True,
            "timeout": 10
        }

        with self.client.post(
            "/execute-request",
            json=payload,
            catch_response=True,
            name="/execute-request"
        ) as response:
            if response.status_code in [200, 403]:
                # 403 if execution is disabled
                response.success()
            elif response.status_code == 429:
                response.success()
            else:
                response.failure(f"Unexpected status code: {response.status_code}")


# User classes representing different load test scenarios
class NormalUser(HttpUser):
    """
    Simulates normal application usage with a mix of operations.

    This user uploads HAR files, checks status, and occasionally generates curl commands.
    Wait time between tasks: 1-5 seconds (normal user behavior).
    """
    tasks = [HARUploadTasks]
    wait_time = between(1, 5)


class CurlGenerationUser(HttpUser):
    """
    Focuses on curl generation and LLM integration testing.

    This user primarily tests the /generate-curl endpoint.
    Wait time: 2-4 seconds.
    """
    tasks = [CurlGenerationTasks]
    wait_time = between(2, 4)


class RateLimitTestUser(HttpUser):
    """
    Aggressively tests rate limiting by sending rapid requests.

    This user has minimal wait time to trigger rate limits.
    Wait time: 0.1-0.5 seconds (very aggressive).
    """
    tasks = [RateLimitTestTasks]
    wait_time = between(0.1, 0.5)


class RequestExecutionUser(HttpUser):
    """
    Tests request execution functionality.

    This user focuses on executing requests and getting request details.
    Wait time: 1-3 seconds.
    """
    tasks = [RequestExecutionTasks]
    wait_time = between(1, 3)


class MixedWorkloadUser(HttpUser):
    """
    Simulates realistic mixed workload with all operations.

    This user performs a variety of tasks to simulate real-world usage.
    Wait time: 1-3 seconds.
    """
    tasks = {
        HARUploadTasks: 4,
        CurlGenerationTasks: 2,
        RequestExecutionTasks: 1,
    }
    wait_time = between(1, 3)


# Event hooks for custom reporting
@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when the test starts."""
    print("\n" + "="*80)
    print("CloudCruise Load Test Starting")
    print("="*80)
    print(f"Host: {environment.host}")
    print(f"Users: {environment.runner.target_user_count if hasattr(environment.runner, 'target_user_count') else 'N/A'}")
    print("="*80 + "\n")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when the test stops."""
    print("\n" + "="*80)
    print("CloudCruise Load Test Complete")
    print("="*80)

    # Get stats
    stats = environment.stats

    print("\nSummary:")
    print(f"  Total requests: {stats.total.num_requests}")
    print(f"  Total failures: {stats.total.num_failures}")
    print(f"  Average response time: {stats.total.avg_response_time:.2f}ms")
    print(f"  Requests/s: {stats.total.total_rps:.2f}")

    # Check for rate limit responses (429)
    rate_limit_count = sum(
        1 for name, stat in stats.entries.items()
        if stat.num_failures > 0
    )

    print(f"\nRate Limiting:")
    print(f"  Endpoints with failures: {rate_limit_count}")

    print("="*80 + "\n")
