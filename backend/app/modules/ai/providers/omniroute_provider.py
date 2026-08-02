import os
import json
import httpx
import logging
from typing import Dict, Any, List, Optional, AsyncIterator
from app.core.config import settings

logger = logging.getLogger(__name__)


class OmniRouteProvider:
    def __init__(self):
        self.api_key = settings.OMNIROUTE_API_KEY
        self.base_url = settings.OMNIROUTE_BASE_URL
        
    def is_configured(self) -> bool:
        return bool(self.api_key and self.base_url)

    async def validate_connection(self) -> bool:
        """Validates connection to OmniRoute gateway by checking if configured and pinging the base URL."""
        if not self.is_configured():
            logger.warning("OmniRoute is not configured (missing api_key or base_url).")
            return False
        
        try:
            url = f"{self.base_url.rstrip('/')}/models"
            headers = {"Authorization": f"Bearer {self.api_key}"}
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(url, headers=headers)
                if response.status_code == 200:
                    logger.info("OmniRoute gateway connection validated successfully.")
                    return True
                else:
                    comp_url = f"{self.base_url.rstrip('/')}/chat/completions"
                    payload = {
                        "model": "gpt-4o",
                        "messages": [{"role": "user", "content": "ping"}],
                        "max_tokens": 1
                    }
                    response = await client.post(comp_url, headers=headers, json=payload)
                    if response.status_code in (200, 400, 404):
                        logger.info(f"OmniRoute gateway validated via completions check (Status: {response.status_code}).")
                        return True
                    logger.warning(f"OmniRoute validation returned status {response.status_code}: {response.text}")
                    return False
        except Exception as e:
            logger.warning(f"Failed to connect to OmniRoute gateway: {e}")
            return False

    async def generate(self, prompt: str, model: str, temperature: float = 0.7) -> str:
        """Generates a text completion response for the given prompt."""
        if not self.is_configured():
            logger.warning("OmniRoute not configured. Returning local simulated response.")
            return self._simulate_narrative(prompt)
            
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        url = f"{self.base_url.rstrip('/')}/chat/completions"
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature
        }
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(url, headers=headers, json=payload)
                if response.status_code == 200:
                    data = response.json()
                    return data["choices"][0]["message"]["content"] or ""
                else:
                    logger.error(f"OmniRoute HTTP error {response.status_code}: {response.text}")
                    raise Exception(f"OmniRoute HTTP error {response.status_code}")
        except Exception as e:
            logger.error(f"OmniRoute generate exception: {e}")
            raise

    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.7,
        response_format: Optional[Dict[str, Any]] = None
    ) -> str:
        """Sends a chat completions request with multi-turn messages and optional JSON formatting."""
        if not self.is_configured():
            logger.warning("OmniRoute not configured. Returning local simulated chat response.")
            if response_format and response_format.get("type") == "json_object":
                return '{"Patient Name": "Subject", "Age": "Years"}'
            return "Simulated chat response."

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        url = f"{self.base_url.rstrip('/')}/chat/completions"
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature
        }
        if response_format:
            payload["response_format"] = response_format

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(url, headers=headers, json=payload)
                if response.status_code == 200:
                    data = response.json()
                    return data["choices"][0]["message"]["content"] or ""
                else:
                    logger.error(f"OmniRoute HTTP error {response.status_code}: {response.text}")
                    raise Exception(f"OmniRoute HTTP error {response.status_code}")
        except Exception as e:
            logger.error(f"OmniRoute chat exception: {e}")
            raise

    async def stream(self, prompt: str, model: str, temperature: float = 0.7) -> AsyncIterator[str]:
        """Streams completion tokens back to the caller."""
        if not self.is_configured():
            logger.warning("OmniRoute not configured. Streaming simulated response.")
            simulated = self._simulate_narrative(prompt)
            for word in simulated.split(" "):
                yield word + " "
            return

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        url = f"{self.base_url.rstrip('/')}/chat/completions"
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "stream": True
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                async with client.stream("POST", url, headers=headers, json=payload) as response:
                    if response.status_code != 200:
                        logger.error(f"OmniRoute streaming failed with status {response.status_code}")
                        raise Exception(f"OmniRoute stream status {response.status_code}")
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            content = line[6:].strip()
                            if content == "[DONE]":
                                break
                            try:
                                chunk = json.loads(content)
                                delta = chunk["choices"][0]["delta"]
                                if "content" in delta:
                                    yield delta["content"]
                            except Exception:
                                pass
        except Exception as e:
            logger.error(f"OmniRoute stream exception: {e}")
            raise

    def _simulate_narrative(self, prompt: str) -> str:
        prompt_lower = prompt.lower()
        if "executive" in prompt_lower:
            return "Clinical Safety Report Executive Summary.\nA total of N/A cases were reviewed under this assessment period. The clinical safety profile evaluated demonstrates overall stability."
        if "signal" in prompt_lower:
            return "Signal Detection Narrative Summary.\nAnalysis evaluated total records. No mathematical anomalies or validation alert flags were observed."
        if "benefit-risk" in prompt_lower:
            return "Benefit-Risk Assessment Summary.\nThe benefit-risk ratio for the evaluated safety cohort remains positive."
        return "Vigilance Clinical Recommendations Summary.\nBased on the analysis of safety case records, it is recommended to maintain routine signal monitoring."


omniroute_provider = OmniRouteProvider()
