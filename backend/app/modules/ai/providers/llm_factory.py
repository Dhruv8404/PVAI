import os
import json
import httpx
import logging
from typing import Dict, Any, List, Optional, AsyncIterator
from app.core.config import settings
from app.modules.ai.providers.omniroute_provider import omniroute_provider

logger = logging.getLogger(__name__)


class BaseLLMProvider:
    async def generate(self, prompt: str, model: str, temperature: float = 0.7) -> str:
        raise NotImplementedError()
        
    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.7,
        response_format: Optional[Dict[str, Any]] = None
    ) -> str:
        raise NotImplementedError()

    async def stream(self, prompt: str, model: str, temperature: float = 0.7) -> AsyncIterator[str]:
        raise NotImplementedError()

    async def validate(self) -> bool:
        raise NotImplementedError()


class OmniRouteProviderWrapper(BaseLLMProvider):
    async def validate(self) -> bool:
        return await omniroute_provider.validate_connection()

    async def generate(self, prompt: str, model: str, temperature: float = 0.7) -> str:
        return await omniroute_provider.generate(prompt, model, temperature)

    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.7,
        response_format: Optional[Dict[str, Any]] = None
    ) -> str:
        return await omniroute_provider.chat(messages, model, temperature, response_format)

    async def stream(self, prompt: str, model: str, temperature: float = 0.7) -> AsyncIterator[str]:
        async for chunk in omniroute_provider.stream(prompt, model, temperature):
            yield chunk


class OpenAIProviderWrapper(BaseLLMProvider):
    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY or os.getenv("OPENAI_API_KEY", "")

    async def validate(self) -> bool:
        if not self.api_key:
            return False
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                r = await client.get(
                    "https://api.openai.com/v1/models",
                    headers={"Authorization": f"Bearer {self.api_key}"}
                )
                return r.status_code == 200
        except Exception:
            return False

    async def generate(self, prompt: str, model: str, temperature: float = 0.7) -> str:
        messages = [{"role": "user", "content": prompt}]
        return await self.chat(messages, model, temperature)

    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.7,
        response_format: Optional[Dict[str, Any]] = None
    ) -> str:
        try:
            import openai
            client = openai.AsyncOpenAI(api_key=self.api_key)
            extra_args = {}
            if response_format:
                extra_args["response_format"] = response_format
            response = await client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                **extra_args
            )
            return response.choices[0].message.content or ""
        except (ImportError, Exception) as e:
            logger.warning(f"OpenAI package error or API failure: {e}. Falling back to httpx call.")
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": model,
                "messages": messages,
                "temperature": temperature
            }
            if response_format:
                payload["response_format"] = response_format

            async with httpx.AsyncClient(timeout=60.0) as client:
                r = await client.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
                if r.status_code == 200:
                    return r.json()["choices"][0]["message"]["content"] or ""
                raise Exception(f"OpenAI HTTP error {r.status_code}: {r.text}")

    async def stream(self, prompt: str, model: str, temperature: float = 0.7) -> AsyncIterator[str]:
        try:
            import openai
            client = openai.AsyncOpenAI(api_key=self.api_key)
            response = await client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                stream=True
            )
            async for chunk in response:
                delta = chunk.choices[0].delta
                if delta.content:
                    yield delta.content
        except (ImportError, Exception) as e:
            logger.warning(f"OpenAI package error or API failure in stream: {e}. Falling back to httpx stream.")
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": temperature,
                "stream": True
            }
            async with httpx.AsyncClient(timeout=60.0) as client:
                async with client.stream("POST", "https://api.openai.com/v1/chat/completions", headers=headers, json=payload) as r:
                    if r.status_code != 200:
                        raise Exception(f"OpenAI HTTP stream error {r.status_code}")
                    async for line in r.aiter_lines():
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


class GeminiProviderWrapper(BaseLLMProvider):
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY", "")

    async def validate(self) -> bool:
        if not self.api_key:
            return False
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models?key={self.api_key}"
            async with httpx.AsyncClient(timeout=3.0) as client:
                r = await client.get(url)
                return r.status_code == 200
        except Exception:
            return False

    async def generate(self, prompt: str, model: str, temperature: float = 0.7) -> str:
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            model_instance = genai.GenerativeModel(model)
            response = await model_instance.generate_content_async(
                prompt,
                generation_config={"temperature": temperature}
            )
            return response.text or ""
        except (ImportError, Exception) as e:
            logger.warning(f"Gemini SDK error or API failure: {e}. Falling back to httpx call.")
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.api_key}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": temperature}
            }
            async with httpx.AsyncClient(timeout=60.0) as client:
                r = await client.post(url, json=payload)
                if r.status_code == 200:
                    data = r.json()
                    return data["candidates"][0]["content"]["parts"][0]["text"] or ""
                raise Exception(f"Gemini HTTP error {r.status_code}: {r.text}")

    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.7,
        response_format: Optional[Dict[str, Any]] = None
    ) -> str:
        # Convert standard openai messages role structure to gemini structure
        contents = []
        for msg in messages:
            role = "user" if msg["role"] == "user" else "model"
            contents.append({
                "role": role,
                "parts": [{"text": msg["content"]}]
            })
        
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            model_instance = genai.GenerativeModel(model)
            config = {"temperature": temperature}
            if response_format and response_format.get("type") == "json_object":
                config["response_mime_type"] = "application/json"
            response = await model_instance.generate_content_async(
                contents,
                generation_config=config
            )
            return response.text or ""
        except (ImportError, Exception) as e:
            logger.warning(f"Gemini SDK error or API failure in chat: {e}. Falling back to httpx call.")
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.api_key}"
            payload = {
                "contents": contents,
                "generationConfig": {"temperature": temperature}
            }
            if response_format and response_format.get("type") == "json_object":
                payload["generationConfig"]["responseMimeType"] = "application/json"

            async with httpx.AsyncClient(timeout=60.0) as client:
                r = await client.post(url, json=payload)
                if r.status_code == 200:
                    data = r.json()
                    return data["candidates"][0]["content"]["parts"][0]["text"] or ""
                raise Exception(f"Gemini HTTP error {r.status_code}: {r.text}")

    async def stream(self, prompt: str, model: str, temperature: float = 0.7) -> AsyncIterator[str]:
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            model_instance = genai.GenerativeModel(model)
            response = await model_instance.generate_content_async(
                prompt,
                generation_config={"temperature": temperature},
                stream=True
            )
            async for chunk in response:
                if chunk.text:
                    yield chunk.text
        except (ImportError, Exception) as e:
            logger.warning(f"Gemini SDK error or API failure in stream: {e}. Defaulting to full HTTP generation.")
            result = await self.generate(prompt, model, temperature)
            for word in result.split(" "):
                yield word + " "


class OllamaProviderWrapper(BaseLLMProvider):
    def __init__(self):
        self.api_url = os.getenv("OLLAMA_API_URL", "http://localhost:11434/api/generate")

    async def validate(self) -> bool:
        try:
            base_url = self.api_url.rsplit("/api/", 1)[0]
            async with httpx.AsyncClient(timeout=2.0) as client:
                r = await client.get(base_url)
                return r.status_code == 200
        except Exception:
            return False

    async def generate(self, prompt: str, model: str, temperature: float = 0.7) -> str:
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature}
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            r = await client.post(self.api_url, json=payload)
            if r.status_code == 200:
                return r.json().get("response", "")
            raise Exception(f"Ollama HTTP error {r.status_code}: {r.text}")

    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.7,
        response_format: Optional[Dict[str, Any]] = None
    ) -> str:
        chat_url = self.api_url.replace("/generate", "/chat")
        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature}
        }
        if response_format and response_format.get("type") == "json_object":
            payload["format"] = "json"

        async with httpx.AsyncClient(timeout=60.0) as client:
            r = await client.post(chat_url, json=payload)
            if r.status_code == 200:
                return r.json().get("message", {}).get("content", "")
            raise Exception(f"Ollama chat HTTP error {r.status_code}: {r.text}")

    async def stream(self, prompt: str, model: str, temperature: float = 0.7) -> AsyncIterator[str]:
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": True,
            "options": {"temperature": temperature}
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream("POST", self.api_url, json=payload) as r:
                if r.status_code != 200:
                    raise Exception(f"Ollama stream HTTP error {r.status_code}")
                async for line in r.aiter_lines():
                    if line:
                        try:
                            chunk = json.loads(line)
                            yield chunk.get("response", "")
                        except Exception:
                            pass


class DeepSeekProviderWrapper(BaseLLMProvider):
    def __init__(self):
        self.api_key = settings.DEEPSEEK_API_KEY or os.getenv("DEEPSEEK_API_KEY", "")

    async def validate(self) -> bool:
        if not self.api_key:
            return False
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                headers = {"Authorization": f"Bearer {self.api_key}"}
                r = await client.get("https://api.deepseek.com/models", headers=headers)
                return r.status_code == 200
        except Exception:
            return False

    async def generate(self, prompt: str, model: str, temperature: float = 0.7) -> str:
        messages = [{"role": "user", "content": prompt}]
        return await self.chat(messages, model, temperature)

    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.7,
        response_format: Optional[Dict[str, Any]] = None
    ) -> str:
        try:
            import openai
            client = openai.AsyncOpenAI(api_key=self.api_key, base_url="https://api.deepseek.com")
            extra_args = {}
            if response_format:
                extra_args["response_format"] = response_format
            model_name = model if model and "deepseek" in model else "deepseek-chat"
            response = await client.chat.completions.create(
                model=model_name,
                messages=messages,
                temperature=temperature,
                **extra_args
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.warning(f"DeepSeek SDK error or API failure: {e}. Falling back to httpx call.")
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            model_name = model if model and "deepseek" in model else "deepseek-chat"
            payload = {
                "model": model_name,
                "messages": messages,
                "temperature": temperature
            }
            if response_format:
                payload["response_format"] = response_format

            async with httpx.AsyncClient(timeout=60.0) as client:
                r = await client.post("https://api.deepseek.com/chat/completions", headers=headers, json=payload)
                if r.status_code == 200:
                    return r.json()["choices"][0]["message"]["content"] or ""
                raise Exception(f"DeepSeek HTTP error {r.status_code}: {r.text}")

    async def stream(self, prompt: str, model: str, temperature: float = 0.7) -> AsyncIterator[str]:
        try:
            import openai
            client = openai.AsyncOpenAI(api_key=self.api_key, base_url="https://api.deepseek.com")
            model_name = model if model and "deepseek" in model else "deepseek-chat"
            response = await client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                stream=True
            )
            async for chunk in response:
                delta = chunk.choices[0].delta
                if delta.content:
                    yield delta.content
        except Exception:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            model_name = model if model and "deepseek" in model else "deepseek-chat"
            payload = {
                "model": model_name,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": temperature,
                "stream": True
            }
            async with httpx.AsyncClient(timeout=60.0) as client:
                async with client.stream("POST", "https://api.deepseek.com/chat/completions", headers=headers, json=payload) as r:
                    if r.status_code != 200:
                        raise Exception(f"DeepSeek HTTP stream error {r.status_code}")
                    async for line in r.aiter_lines():
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


import asyncio
from app.core.reliability_helper import llm_circuit_breaker, retry_with_backoff, CircuitBreakerOpenException


class ReliableLLMProvider(BaseLLMProvider):
    def __init__(self, provider: BaseLLMProvider):
        self._provider = provider

    async def validate(self) -> bool:
        # Pings/validations are typically quick and don't need circuit breakers
        return await self._provider.validate()

    async def generate(self, prompt: str, model: str, temperature: float = 0.7) -> str:
        llm_circuit_breaker.check_state()
        
        @retry_with_backoff(retries=3, initial_delay=1.0, exception_types=(httpx.HTTPError, asyncio.TimeoutError))
        async def _call():
            return await asyncio.wait_for(
                self._provider.generate(prompt, model, temperature),
                timeout=30.0
            )

        try:
            res = await _call()
            llm_circuit_breaker.record_success()
            return res
        except Exception as e:
            llm_circuit_breaker.record_failure()
            logger.error(f"[AI RELIABILITY] LLM generate failed: {e}")
            raise e

    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.7,
        response_format: Optional[Dict[str, Any]] = None
    ) -> str:
        llm_circuit_breaker.check_state()
        
        @retry_with_backoff(retries=3, initial_delay=1.0, exception_types=(httpx.HTTPError, asyncio.TimeoutError))
        async def _call():
            return await asyncio.wait_for(
                self._provider.chat(messages, model, temperature, response_format),
                timeout=30.0
            )

        try:
            res = await _call()
            llm_circuit_breaker.record_success()
            return res
        except Exception as e:
            llm_circuit_breaker.record_failure()
            logger.error(f"[AI RELIABILITY] LLM chat failed: {e}")
            raise e

    async def stream(self, prompt: str, model: str, temperature: float = 0.7) -> AsyncIterator[str]:
        llm_circuit_breaker.check_state()
        try:
            # We yield chunks as they arrive. Connection timeout can be handled by provider or HTTPX.
            async for chunk in self._provider.stream(prompt, model, temperature):
                yield chunk
            llm_circuit_breaker.record_success()
        except Exception as e:
            llm_circuit_breaker.record_failure()
            logger.error(f"[AI RELIABILITY] LLM stream failed: {e}")
            raise e


class LLMProviderFactory:
    def __init__(self):
        self._providers: Dict[str, BaseLLMProvider] = {
            "omniroute": OmniRouteProviderWrapper(),
            "openai": OpenAIProviderWrapper(),
            "gemini": GeminiProviderWrapper(),
            "ollama": OllamaProviderWrapper(),
            "deepseek": DeepSeekProviderWrapper()
        }

    def get_provider(self, provider_name: Optional[str] = None) -> BaseLLMProvider:
        """Returns the configured LLM provider wrapper instance wrapped in a reliability layer."""
        name = (provider_name or settings.LLM_PROVIDER).lower()
        if name not in self._providers:
            logger.warning(f"Unknown provider '{name}'. Defaulting to 'omniroute'.")
            name = "omniroute"
        raw_provider = self._providers[name]
        return ReliableLLMProvider(raw_provider)


llm_factory = LLMProviderFactory()

