import re
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import or_, func

from app.models import Request


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
        }

        # Extract words (alphanumeric sequences)
        words = re.findall(r'\b\w+\b', prompt.lower())

        # Filter out common words and short words
        keywords = [w for w in words if w not in common_words and len(w) > 2]

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
    def filter_requests(
        db: Session,
        har_file_id: int,
        prompt: str,
        max_results: int = 10,
    ) -> List[Request]:
        """
        Filter requests from database using keyword matching.

        Args:
            db: Database session
            har_file_id: HAR file ID to filter requests from
            prompt: Natural language prompt
            max_results: Maximum number of results to return

        Returns:
            List of filtered Request objects
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

        # Order by relevance (prioritize shorter URLs, successful status codes)
        query = query.order_by(
            Request.status_code.desc().nullslast(),
            func.length(Request.url).asc(),
        )

        # Limit results
        results = query.limit(max_results).all()

        return results

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
                "path": path_with_params,
                "request_id": req.id,  # Store for later retrieval
            })

        return candidates
