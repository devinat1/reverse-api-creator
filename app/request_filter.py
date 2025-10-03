import re
import logging
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import or_, func

from app.models import Request

logger = logging.getLogger(__name__)


class RequestFilter:
    """Service for pre-filtering requests using PostgreSQL before LLM processing."""

    @staticmethod
    def extract_keywords(prompt: str) -> List[str]:
        """
        Extract keywords from user prompt for filtering.

        Args:
            prompt: Natural language prompt from user

        Returns:
            List of keywords
        """
        # Remove common words and extract meaningful keywords
        common_words = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
            "of", "with", "from", "by", "about", "as", "into", "like", "through",
            "after", "over", "between", "out", "against", "during", "without",
            "before", "under", "around", "among", "api", "endpoint", "request",
            "return", "get", "fetch", "that", "which", "what", "is", "are", "was",
            # Additional technical/file-related terms to exclude
            "har", "file", "files", "com", "org", "net", "io", "dev", "app",
            "www", "http", "https", "url", "domain", "path", "json", "xml",
        }

        # Extract words (alphanumeric sequences)
        words = re.findall(r'\b\w+\b', prompt.lower())

        # Filter out common words, short words, and domain extensions
        keywords = []
        for w in words:
            # Skip if in common words or too short
            if w in common_words or len(w) <= 2:
                continue
            # Skip if looks like a domain extension (3-4 letter extensions after a dot reference)
            if len(w) <= 4 and w in ["com", "org", "net", "edu", "gov", "io", "co", "uk", "de"]:
                continue
            keywords.append(w)

        return keywords

    @staticmethod
    def detect_http_method(prompt: str) -> str | None:
        """
        Detect HTTP method from prompt.

        Args:
            prompt: Natural language prompt

        Returns:
            HTTP method (GET, POST, etc.) or None
        """
        prompt_lower = prompt.lower()
        methods = ["get", "post", "put", "delete", "patch", "head", "options"]

        for method in methods:
            if re.search(r'\b' + method + r'\b', prompt_lower):
                return method.upper()

        return None

    @staticmethod
    def _calculate_relevance_score(req: Request, keywords: List[str]) -> float:
        """
        Calculate relevance score for a request based on API-like characteristics.

        Args:
            req: Request object
            keywords: List of keywords from user prompt

        Returns:
            Relevance score (higher is better)
        """
        score = 0.0

        # Strong boost for API subdomains (e.g., api.example.com, api-v2.example.com)
        if req.domain:
            domain_lower = req.domain.lower()
            # Check if domain starts with "api." or contains "api-"
            if domain_lower.startswith("api.") or ".api." in domain_lower or domain_lower.startswith("api-"):
                score += 15.0
            # Boost for other API-like domain keywords
            elif any(keyword in domain_lower for keyword in ["gateway", "service", "rest", "graphql"]):
                score += 10.0

        # Boost for JSON content type (typical for APIs)
        if req.content_type and "json" in req.content_type.lower():
            score += 10.0

        # Boost for successful status codes
        if req.status_code and 200 <= req.status_code < 300:
            score += 5.0

        # Boost for requests with query parameters (APIs often use them)
        if req.query_params:
            score += 3.0
            # Extra boost if query params contain API-like keywords
            query_str = str(req.query_params).lower()
            if any(api_term in query_str for api_term in ["id", "format", "api", "key", "token", "timestamp", "limit", "offset"]):
                score += 5.0

        # Strong penalty for static assets
        if req.path:
            static_extensions = [".jpg", ".jpeg", ".png", ".gif", ".css", ".js", ".ico", ".svg", ".woff", ".ttf", ".woff2", ".eot"]
            if any(req.path.lower().endswith(ext) for ext in static_extensions):
                score -= 30.0

        # Strong penalty for static resource paths
        if req.path:
            static_paths = ["/static/", "/bundle/", "/assets/", "/dist/", "/public/", "/_next/", "/webpack/"]
            if any(static_path in req.path.lower() for static_path in static_paths):
                score -= 30.0

        # Boost for keyword matches in URL (prioritize exact matches)
        if keywords:
            url_lower = req.url.lower() if req.url else ""
            path_lower = req.path.lower() if req.path else ""

            for keyword in keywords:
                if keyword in path_lower:
                    score += 5.0  # Path matches are most relevant
                elif keyword in url_lower:
                    score += 2.0  # URL matches are somewhat relevant

        # Boost for GET requests (most common for data retrieval APIs)
        if req.method and req.method.upper() == "GET":
            score += 1.0

        # Penalty for very long URLs (often tracking/analytics)
        if req.url and len(req.url) > 200:
            score -= 2.0

        # Boost for paths that look like API endpoints (contain numbers, IDs, specific patterns)
        if req.path:
            # Check for API-like path patterns
            if re.search(r'/v\d+/', req.path):  # versioned API (e.g., /v1/, /v2/)
                score += 3.0
            if re.search(r'/api/', req.path, re.IGNORECASE):  # explicit /api/ in path
                score += 3.0

        return score

    @staticmethod
    def filter_requests(
        db: Session,
        har_file_id: int,
        prompt: str,
        max_results: int = 10,
    ) -> List[Request]:
        """
        Filter requests from database using keyword matching and relevance scoring.

        Args:
            db: Database session
            har_file_id: HAR file ID to filter requests from
            prompt: Natural language prompt
            max_results: Maximum number of results to return

        Returns:
            List of filtered Request objects, ordered by relevance
        """
        keywords = RequestFilter.extract_keywords(prompt)
        http_method = RequestFilter.detect_http_method(prompt)

        # Build query
        query = db.query(Request).filter(Request.har_file_id == har_file_id)

        # Filter by HTTP method if detected
        if http_method:
            query = query.filter(Request.method == http_method)

        # If we have keywords, filter by them
        if keywords:
            # Build OR conditions for keyword matching across URL, domain, path
            conditions = []
            for keyword in keywords:
                keyword_pattern = f"%{keyword}%"
                conditions.append(Request.url.ilike(keyword_pattern))
                conditions.append(Request.domain.ilike(keyword_pattern))
                conditions.append(Request.path.ilike(keyword_pattern))

            query = query.filter(or_(*conditions))

        # Get all matching results
        results = query.all()

        # If no keyword matches, fall back to all requests (let scoring sort them)
        if not results and not keywords:
            results = query.all()

        # Calculate relevance scores and sort
        scored_results = [
            (req, RequestFilter._calculate_relevance_score(req, keywords))
            for req in results
        ]
        scored_results.sort(key=lambda x: x[1], reverse=True)

        # Log top results for debugging
        logger.info(f"Filtering with keywords: {keywords}")
        logger.info(f"Top {min(5, len(scored_results))} scored results:")
        for req, score in scored_results[:5]:
            logger.info(f"  Score: {score:6.1f} | {req.method:6s} | {req.domain:30s} | {req.path[:60]}")

        # Return top results
        return [req for req, score in scored_results[:max_results]]

    @staticmethod
    def create_minimal_candidates(requests: List[Request]) -> List[Dict[str, Any]]:
        """
        Create minimal candidate list for LLM (reduces token usage).

        Args:
            requests: List of Request objects

        Returns:
            List of minimal candidate dictionaries
        """
        candidates = []
        for idx, req in enumerate(requests):
            # Create minimal representation
            path_with_params = req.path
            if req.query_params:
                # Show first 2 query params
                params = list(req.query_params.items())[:2]
                params_str = "&".join([f"{k}={v}" for k, v in params])
                if len(req.query_params) > 2:
                    params_str += "..."
                path_with_params = f"{req.path}?{params_str}"

            candidates.append({
                "index": idx,
                "method": req.method,
                "domain": req.domain,  # Include domain for better LLM matching
                "path": path_with_params,
                "content_type": req.content_type,  # Include content type
                "request_id": req.id,  # Store for later retrieval
            })

        return candidates
