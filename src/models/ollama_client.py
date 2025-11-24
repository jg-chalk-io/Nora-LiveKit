"""Ollama local LLM adapter."""

import os
from typing import AsyncIterator

from .base_client import BaseLLMClient


class OllamaClient(BaseLLMClient):
    """Ollama local LLM client adapter."""

    def __init__(self, model: str = "mistral", base_url: str | None = None):
        """Initialize Ollama client.

        Args:
            model: Model identifier (default: mistral)
            base_url: Ollama base URL (uses OLLAMA_BASE_URL env var or http://localhost:11434)
        """
        self._model = model
        self._base_url = base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

    @property
    def name(self) -> str:
        """Return provider name."""
        return "ollama"

    @property
    def model(self) -> str:
        """Return model identifier."""
        return self._model

    async def generate(self, prompt: str, context: list[dict] | None = None) -> str:
        """Generate response using Ollama API.

        Args:
            prompt: The user prompt
            context: Optional conversation history

        Returns:
            Generated response
        """
        try:
            from ollama import AsyncClient

            client = AsyncClient(base_url=self._base_url)
            messages = context or []
            messages.append({"role": "user", "content": prompt})

            response = await client.chat(model=self._model, messages=messages, stream=False)
            return response["message"]["content"] or ""
        except Exception as e:
            raise RuntimeError(f"Ollama generation failed: {str(e)}")

    async def stream(
        self, prompt: str, context: list[dict] | None = None
    ) -> AsyncIterator[str]:
        """Stream response tokens from Ollama API.

        Args:
            prompt: The user prompt
            context: Optional conversation history

        Yields:
            Response tokens
        """
        try:
            from ollama import AsyncClient

            client = AsyncClient(base_url=self._base_url)
            messages = context or []
            messages.append({"role": "user", "content": prompt})

            async for chunk in await client.chat(
                model=self._model, messages=messages, stream=True
            ):
                if chunk["message"]["content"]:
                    yield chunk["message"]["content"]
        except Exception as e:
            raise RuntimeError(f"Ollama streaming failed: {str(e)}")

    async def health_check(self) -> bool:
        """Check if Ollama server is accessible.

        Returns:
            True if accessible, False otherwise
        """
        try:
            from ollama import AsyncClient

            client = AsyncClient(base_url=self._base_url)
            # Try to list models as a health check
            models = await client.list()
            return bool(models.get("models"))
        except Exception:
            return False
