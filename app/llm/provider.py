"""Groq (OpenAI-compatible) provider. Used only when LLM_PROVIDER=groq."""
import json
import os

import requests

from app.llm.base import BaseLLM, LLMError
from app.llm.mock import MockLLM


class GroqLLM(BaseLLM):
    def __init__(self, api_key: str, base_url: str, model: str, timeout: int = 60):
        if not api_key:
            raise LLMError("GROQ_API_KEY is not set")
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def complete_json(self, system: str, user: str) -> dict:
        try:
            resp = requests.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "temperature": 0.7,
                    "response_format": {"type": "json_object"},
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                },
                timeout=self.timeout,
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
        except requests.RequestException as e:
            raise LLMError(f"groq request failed: {e}") from e
        except (KeyError, IndexError, ValueError) as e:
            raise LLMError(f"groq response shape error: {e}") from e
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as e:
            raise LLMError(f"groq returned non-JSON content: {e}") from e
        if not isinstance(parsed, dict):
            raise LLMError("groq returned JSON that is not an object")
        return parsed


def get_llm() -> BaseLLM:
    provider = os.getenv("LLM_PROVIDER", "mock").strip().lower()
    if provider == "groq":
        return GroqLLM(
            api_key=os.getenv("GROQ_API_KEY", ""),
            base_url=os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1"),
            model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
        )
    if provider == "mock":
        return MockLLM()
    raise LLMError(f"unknown LLM_PROVIDER: {provider!r}")
