import httpx
import os
import json
import asyncio
import re
import logging
from typing import Dict, Any, Optional
from .config import settings

# Get a logger instance
logger = logging.getLogger(__name__)


class GeminiClient:
    def __init__(self, max_retries: int = 3, retry_delay: int = 2):
        self.project_id = settings.project_id
        self.location = settings.location
        self.model = settings.model
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        # Support API key authentication via GEMINI_API_KEY env var
        self.api_key = os.environ.get("GEMINI_API_KEY", "")

        # Validate configuration
        if not all([self.project_id, self.location, self.model]):
            raise ValueError("Gemini configuration must be set in settings (project_id, location, model)")

        # Use API key endpoint if available, otherwise use gcloud auth
        if self.api_key:
            self.base_url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
            self.use_api_key = True
        else:
            self.base_url = f"https://{self.location}-aiplatform.googleapis.com/v1/projects/{self.project_id}/locations/{self.location}/publishers/google/models/{self.model}:generateContent"
            self.use_api_key = False

    async def _make_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Internal method to make a request with retry logic."""
        last_exception = None
        
        # Build headers based on authentication method
        if self.use_api_key:
            headers = {
                "Content-Type": "application/json"
            }
            # For API key auth, we don't need Authorization header
        else:
            access_token = await self._get_access_token()
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }

        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(self.base_url, headers=headers, json=payload, timeout=120.0)
                    response.raise_for_status()
                    response_data = response.json()

                    # Extract text from Gemini response
                    text_response = response_data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                    if not text_response:
                        raise ValueError("Empty response from LLM.")

                    # Parse JSON from text response and return on success
                    return self._extract_json_from_response(text_response)

            except (httpx.HTTPStatusError, httpx.TimeoutException) as e:
                logger.warning(f"HTTP error on attempt {attempt + 1}/{self.max_retries}: {e}")
                last_exception = e
                await asyncio.sleep(self.retry_delay * (attempt + 1)) # Exponential backoff
            except ValueError as e:
                logger.warning(f"Data processing error (e.g., invalid JSON) on attempt {attempt + 1}/{self.max_retries}: {e}")
                last_exception = e
                await asyncio.sleep(self.retry_delay)
            except Exception as e:
                logger.error(f"An unexpected error occurred on attempt {attempt + 1}: {e}")
                last_exception = e
                break # Do not retry on unknown errors

        # If all retries fail, raise the last captured exception
        raise last_exception or Exception("Failed to get a valid response from Gemini after all retries.")


    async def generate_architectural_design(self, prompt: str) -> Dict[str, Any]:
        """Generate architectural design using Gemini API with system prompt for JSON output."""
        system_prompt = "You are an expert BIM architect. Return ONLY valid JSON."
        full_prompt = f"{system_prompt}\n\n{prompt}"

        payload = {
            "contents": [{
                "role": "USER",
                "parts": [{"text": full_prompt}]
            }],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 8192
            }
        }
        return await self._make_request(payload)

    async def generate_with_schema(
        self,
        prompt: str,
        schema: Dict[str, Any],
        system: Optional[str] = None,
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate structured output following a JSON schema using Gemini API."""
        system_prompt = system or "You are a helpful assistant. Generate output that meets all constraints."
        schema_str = json.dumps(schema, indent=2)

        full_prompt = f"""{system_prompt}

Generate output that exactly matches this JSON schema:

{schema_str}

Input: {prompt}

Return ONLY valid JSON that matches the schema above, no other text."""

        payload = {
            "contents": [{
                "role": "USER",
                "parts": [{"text": full_prompt}]
            }],
            "generationConfig": {
                "temperature": 0.1,
                "maxOutputTokens": 8192
            }
        }
        return await self._make_request(payload)

    async def generate_content(self, prompt: str) -> str:
        """Generate simple text content."""
        payload = {
            "contents": [{
                "role": "USER",
                "parts": [{"text": prompt}]
            }]
        }
        # Note: This will also return a dict because _make_request is designed for JSON.
        # The calling function might need adjustment if it expects a raw string.
        return await self._make_request(payload)

    def _extract_json_from_response(self, text: str) -> Dict[str, Any]:
        """Extract JSON from text response, handling code blocks and other formatting."""
        original_text = text.strip()
        
        # If the text is empty, raise error
        if not original_text:
            raise ValueError("Empty response from LLM.")
        
        # Try to find JSON in markdown code blocks first
        # Look for ```json ... ``` or ``` ... ```
        import re
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', original_text)
        if json_match:
            # Use the content inside the code block
            json_str = json_match.group(1).strip()
        else:
            # No code block, try to find JSON object by balancing braces
            # Find the start of the JSON object
            json_start = original_text.find('{')
            if json_start == -1:
                raise ValueError(f"No JSON object found in LLM response. Length: {len(original_text)}. First 500 chars: {original_text[:500]}...")
            
            # Find the end of the JSON object by balancing braces
            brace_count = 0
            json_end = -1
            for i, char in enumerate(original_text[json_start:]):
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        json_end = json_start + i + 1
                        break
            
            if json_end == -1:
                raise ValueError(f"Unterminated JSON object in LLM response. Length: {len(original_text)}. First 500 chars: {original_text[:500]}...")
            
            json_str = original_text[json_start:json_end]
        
        # Attempt to parse the extracted JSON string
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            # If parsing fails, raise an informative error
            raise ValueError(f"Invalid JSON response from LLM. Length: {len(json_str)}. JSON attempted: {json_str[:500]}... Error: {str(e)}")

    async def _get_access_token(self) -> str:
        """Get access token from gcloud CLI."""
        process = await asyncio.create_subprocess_exec(
            "gcloud", "auth", "print-access-token",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        if process.returncode != 0:
            raise Exception(f"Failed to get gcloud access token: {stderr.decode().strip()}")
        return stdout.decode().strip()

