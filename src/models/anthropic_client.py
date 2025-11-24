"""Anthropic Claude API adapter."""

import os
from typing import AsyncIterator

from .base_client import BaseLLMClient


class AnthropicClient(BaseLLMClient):
    """Anthropic Claude API adapter."""

    def __init__(self, model: str = "claude-3-5-sonnet-20241022", api_key: str | None = None):
        """Initialize Anthropic client.

        Args:
            model: Model identifier (default: claude-3-5-sonnet-20241022)
            api_key: API key (uses ANTHROPIC_API_KEY env var if not provided)
        """
        self._model = model
        self._api_key = api_key or os.getenv("ANTHROPIC_API_KEY", "")
        if not self._api_key:
            raise ValueError("Anthropic API key not provided and ANTHROPIC_API_KEY not set")

    @property
    def name(self) -> str:
        """Return provider name."""
        return "anthropic"

    @property
    def model(self) -> str:
        """Return model identifier."""
        return self._model

    async def generate(self, prompt: str, context: list[dict] | None = None) -> str:
        """Generate response using Anthropic API.

        Args:
            prompt: The user prompt
            context: Optional conversation history

        Returns:
            Generated response
        """
        try:
            from anthropic import AsyncAnthropic

            client = AsyncAnthropic(api_key=self._api_key)
            messages = context or []
            messages.append({"role": "user", "content": prompt})

            response = await client.messages.create(
                model=self._model, max_tokens=500, messages=messages
            )
            return response.content[0].text or ""
        except Exception as e:
            raise RuntimeError(f"Anthropic generation failed: {str(e)}")

    async def stream(
        self, prompt: str, context: list[dict] | None = None
    ) -> AsyncIterator[str]:
        """Stream response tokens from Anthropic API.

        Args:
            prompt: The user prompt
            context: Optional conversation history

        Yields:
            Response tokens
        """
        try:
            from anthropic import AsyncAnthropic

            client = AsyncAnthropic(api_key=self._api_key)
            messages = context or []
            messages.append({"role": "user", "content": prompt})

            with await client.messages.stream(
                model=self._model, max_tokens=500, messages=messages
            ) as stream:
                async for text in stream.text_stream:
                    yield text
        except Exception as e:
            raise RuntimeError(f"Anthropic streaming failed: {str(e)}")

    async def health_check(self) -> bool:
        """Check if Anthropic API is accessible.

        Returns:
            True if accessible, False otherwise
        """
        try:
            from anthropic import AsyncAnthropic

            client = AsyncAnthropic(api_key=self._api_key)
            response = await client.messages.create(
                model=self._model, max_tokens=1, messages=[{"role": "user", "content": "hi"}]
            )
            return response.content[0].text is not None
        except Exception:
            return False
