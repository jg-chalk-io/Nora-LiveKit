"""Mock LLM client for testing."""

from typing import AsyncIterator

from src.models import BaseLLMClient


class MockLLMClient(BaseLLMClient):
    """Deterministic mock LLM client for testing."""

    def __init__(
        self,
        name: str = "mock",
        model: str = "mock-model",
        responses: list[str] | None = None,
        failure_mode: str | None = None,
    ):
        """Initialize mock client.

        Args:
            name: Provider name
            model: Model identifier
            responses: List of responses to return
            failure_mode: 'timeout', 'api_error', or None for success
        """
        self._name = name
        self._model = model
        self._responses = responses or ["Mock response"]
        self._failure_mode = failure_mode
        self._call_count = 0
        self._generated_count = 0

    @property
    def name(self) -> str:
        """Return provider name."""
        return self._name

    @property
    def model(self) -> str:
        """Return model identifier."""
        return self._model

    async def generate(self, prompt: str, context: list[dict] | None = None) -> str:
        """Generate mock response.

        Args:
            prompt: The user prompt
            context: Optional conversation history

        Returns:
            Mock response

        Raises:
            TimeoutError: If failure_mode is 'timeout'
            RuntimeError: If failure_mode is 'api_error'
        """
        self._call_count += 1

        if self._failure_mode == "timeout":
            raise TimeoutError("Mock timeout")
        elif self._failure_mode == "api_error":
            raise RuntimeError("Mock API error")

        if self._generated_count < len(self._responses):
            response = self._responses[self._generated_count]
            self._generated_count += 1
            return response
        else:
            return self._responses[-1] if self._responses else "Mock response"

    async def stream(
        self, prompt: str, context: list[dict] | None = None
    ) -> AsyncIterator[str]:
        """Stream mock response tokens.

        Args:
            prompt: The user prompt
            context: Optional conversation history

        Yields:
            Mock response tokens
        """
        if self._failure_mode == "timeout":
            raise TimeoutError("Mock timeout")
        elif self._failure_mode == "api_error":
            raise RuntimeError("Mock API error")

        response = await self.generate(prompt, context)
        for token in response.split():
            yield token + " "

    async def health_check(self) -> bool:
        """Check health status.

        Returns:
            False if failure_mode is set, True otherwise
        """
        return self._failure_mode is None

    def get_call_count(self) -> int:
        """Get number of generate calls.

        Returns:
            Number of calls
        """
        return self._call_count

    def reset(self) -> None:
        """Reset call counters."""
        self._call_count = 0
        self._generated_count = 0
