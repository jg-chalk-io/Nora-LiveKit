"""Google Gemini API adapter."""

import os
from typing import AsyncIterator

from .base_client import BaseLLMClient


class GoogleClient(BaseLLMClient):
    """Google Gemini API adapter."""

    def __init__(self, model: str = "gemini-2.0-flash", api_key: str | None = None):
        """Initialize Google Gemini client.

        Args:
            model: Model identifier (default: gemini-2.0-flash)
            api_key: API key (uses GOOGLE_API_KEY env var if not provided)
        """
        self._model = model
        self._api_key = api_key or os.getenv("GOOGLE_API_KEY", "")
        if not self._api_key:
            raise ValueError("Google API key not provided and GOOGLE_API_KEY not set")

    @property
    def name(self) -> str:
        """Return provider name."""
        return "google"

    @property
    def model(self) -> str:
        """Return model identifier."""
        return self._model

    async def generate(self, prompt: str, context: list[dict] | None = None) -> str:
        """Generate response using Google Gemini API.

        Args:
            prompt: The user prompt
            context: Optional conversation history

        Returns:
            Generated response
        """
        try:
            import google.generativeai as genai

            genai.configure(api_key=self._api_key)
            model = genai.GenerativeModel(self._model)

            # Convert context to chat history format
            chat_history = context or []
            chat = model.start_chat(history=chat_history)

            response = await chat.send_message_async(prompt)
            return response.text or ""
        except Exception as e:
            raise RuntimeError(f"Google Gemini generation failed: {str(e)}")

    async def stream(
        self, prompt: str, context: list[dict] | None = None
    ) -> AsyncIterator[str]:
        """Stream response tokens from Google Gemini API.

        Args:
            prompt: The user prompt
            context: Optional conversation history

        Yields:
            Response tokens
        """
        try:
            import google.generativeai as genai

            genai.configure(api_key=self._api_key)
            model = genai.GenerativeModel(self._model)

            # Convert context to chat history format
            chat_history = context or []
            chat = model.start_chat(history=chat_history)

            response = await chat.send_message_async(prompt, stream=True)
            async for chunk in response:
                if chunk.text:
                    yield chunk.text
        except Exception as e:
            raise RuntimeError(f"Google Gemini streaming failed: {str(e)}")

    async def health_check(self) -> bool:
        """Check if Google Gemini API is accessible.

        Returns:
            True if accessible, False otherwise
        """
        try:
            import google.generativeai as genai

            genai.configure(api_key=self._api_key)
            model = genai.GenerativeModel(self._model)
            response = await model.generate_content_async("test")
            return response.text is not None
        except Exception:
            return False
