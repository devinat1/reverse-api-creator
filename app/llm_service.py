import json
import logging
from typing import Dict, Any, List, Optional

import litellm

from app.config import settings

logger = logging.getLogger(__name__)

# Configure LiteLLM
litellm.set_verbose = False


class LLMService:
    """Service for LLM-powered request matching with fallback."""

    def __init__(self):
        self.primary_model = settings.llm_primary_model
        self.fallback_model = settings.llm_fallback_model
        self.timeout = settings.llm_timeout

    def _create_prompt(self, user_prompt: str, candidates: List[Dict[str, Any]]) -> str:
        """
        Create minimal prompt for LLM.

        Args:
            user_prompt: User's natural language request
            candidates: List of minimal candidate dictionaries

        Returns:
            Formatted prompt string
        """
        # Format candidates with domain, method, path, and content-type
        candidate_lines = []
        for c in candidates:
            # Build candidate description
            parts = [f"{c['index']}: {c['domain']} - {c['method']} {c['path']}"]

            # Add content type if available and relevant
            if c.get('content_type'):
                content_type = c['content_type'].split(';')[0].strip()  # Remove charset etc.
                if content_type:
                    parts.append(f"[{content_type}]")

            candidate_lines.append(" ".join(parts))

        candidates_text = "\n".join(candidate_lines)

        prompt = f"""Match this request: "{user_prompt}"

Candidates (format: index: domain - METHOD path [content-type]):
{candidates_text}

Return JSON with the index of the best match:
{{"index": <number>, "reasoning": "<brief explanation>"}}"""

        return prompt

    def _parse_response(self, response_text: str, num_candidates: int) -> Optional[int]:
        """
        Parse LLM response to extract index.

        Args:
            response_text: Raw LLM response
            num_candidates: Total number of candidates

        Returns:
            Index of matched request, or None if parsing fails
        """
        try:
            # Try to parse as JSON
            data = json.loads(response_text)
            index = data.get("index")

            if index is not None and isinstance(index, int) and 0 <= index < num_candidates:
                return index

        except json.JSONDecodeError:
            # Try to extract number from text
            import re
            match = re.search(r'"?index"?\s*:\s*(\d+)', response_text)
            if match:
                index = int(match.group(1))
                if 0 <= index < num_candidates:
                    return index

        return None

    async def match_request(
        self,
        user_prompt: str,
        candidates: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Use LLM to match user prompt to best candidate request.

        Args:
            user_prompt: Natural language description
            candidates: List of minimal candidate dictionaries

        Returns:
            Dictionary with matched index and metadata
        """
        if not candidates:
            raise ValueError("No candidates provided")

        prompt = self._create_prompt(user_prompt, candidates)
        num_candidates = len(candidates)

        # Try primary model (o3-mini)
        try:
            logger.info(f"Trying primary model: {self.primary_model}")
            response = await litellm.acompletion(
                model=self.primary_model,
                messages=[{"role": "user", "content": prompt}],
                timeout=self.timeout,
                response_format={"type": "json_object"},
            )

            response_text = response.choices[0].message.content
            matched_index = self._parse_response(response_text, num_candidates)

            if matched_index is not None:
                logger.info(f"Primary model matched index: {matched_index}")
                return {
                    "index": matched_index,
                    "request_id": candidates[matched_index]["request_id"],
                    "model_used": self.primary_model,
                    "response": response_text,
                }

            logger.warning("Primary model returned invalid index, trying fallback")

        except Exception as e:
            logger.error(f"Primary model failed: {e}, trying fallback")

        # Fallback to gpt-4o
        try:
            logger.info(f"Trying fallback model: {self.fallback_model}")
            response = await litellm.acompletion(
                model=self.fallback_model,
                messages=[{"role": "user", "content": prompt}],
                timeout=self.timeout,
                response_format={"type": "json_object"},
            )

            response_text = response.choices[0].message.content
            matched_index = self._parse_response(response_text, num_candidates)

            if matched_index is not None:
                logger.info(f"Fallback model matched index: {matched_index}")
                return {
                    "index": matched_index,
                    "request_id": candidates[matched_index]["request_id"],
                    "model_used": self.fallback_model,
                    "response": response_text,
                }

            raise ValueError("Fallback model also returned invalid index")

        except Exception as e:
            logger.error(f"Fallback model failed: {e}")
            raise Exception("Both primary and fallback models failed to match request")


# Singleton instance
llm_service = LLMService()
