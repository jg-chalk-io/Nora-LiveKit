"""OpenAI API adapter."""

import os
from typing import AsyncIterator

from .base_client import BaseLLMClient


class OpenAIClient(BaseLLMClient):
    """OpenAI GPT-4/GPT-3.5 API adapter."""

    def __init__(self, model: str = "gpt-4-turbo", api_key: str | None = None):
        """Initialize OpenAI client.

        Args:
            model: Model identifier (default: gpt-4-turbo)
            api_key: API key (uses OPENAI_API_KEY env var if not provided)
        """
        self._model = model
        self._api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        if not self._api_key:
            raise ValueError("OpenAI API key not provided and OPENAI_API_KEY not set")

    @property
    def name(self) -> str:
        """Return provider name."""
        return "openai"

    @property
    def model(self) -> str:
        """Return model identifier."""
        return self._model

    async def generate(self, prompt: str, context: list[dict] | None = None) -> str:
        """Generate response using OpenAI API.

        Args:
            prompt: The user prompt
            context: Optional conversation history

        Returns:
            Generated response
        """
        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(api_key=self._api_key)
            messages = context or []
            messages.append({"role": "user", "content": prompt})

            response = await client.chat.completions.create(
                model=self._model, messages=messages, temperature=0.7, max_tokens=500
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            raise RuntimeError(f"OpenAI generation failed: {str(e)}")

    async def stream(
        self, prompt: str, context: list[dict] | None = None
    ) -> AsyncIterator[str]:
        """Stream response tokens from OpenAI API.

        Args:
            prompt: The user prompt
            context: Optional conversation history

        Yields:
            Response tokens
        """
        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(api_key=self._api_key)
            messages = context or []
            messages.append({"role": "user", "content": prompt})

            stream = await client.chat.completions.create(
                model=self._model,
                messages=messages,
                temperature=0.7,
                max_tokens=500,
                stream=True,
            )

            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            raise RuntimeError(f"OpenAI streaming failed: {str(e)}")

    async def health_check(self) -> bool:
        """Check if OpenAI API is accessible.

        Returns:
            True if accessible, False otherwise
        """
        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(api_key=self._api_key)
            # Try a minimal API call
            response = await client.chat.completions.create(
                model=self._model, messages=[{"role": "user", "content": "hi"}], max_tokens=1
            )
            return response.choices[0].message.content is not None
        except Exception:
            return False
