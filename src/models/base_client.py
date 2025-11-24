"""Abstract base class for LLM client implementations."""

from abc import ABC, abstractmethod
from typing import AsyncIterator


class BaseLLMClient(ABC):
    """Abstract interface for LLM providers."""

    @abstractmethod
    async def generate(self, prompt: str, context: list[dict] | None = None) -> str:
        """Generate a single response from the LLM.

        Args:
            prompt: The user prompt/message
            context: Optional conversation history as list of dicts with 'role' and 'content'

        Returns:
            Generated response string

        Raises:
            Exception: If LLM generation fails
        """
        pass

    @abstractmethod
    async def stream(
        self, prompt: str, context: list[dict] | None = None
    ) -> AsyncIterator[str]:
        """Stream response tokens from the LLM.

        Args:
            prompt: The user prompt/message
            context: Optional conversation history

        Yields:
            Response tokens as strings

        Raises:
            Exception: If streaming fails
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Verify provider availability.

        Returns:
            True if provider is available, False otherwise
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the provider name."""
        pass

    @property
    @abstractmethod
    def model(self) -> str:
        """Return the model identifier."""
        pass
