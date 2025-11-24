"""LLM client factory with fallback chain support."""

import asyncio
import logging
from typing import Callable

from .base_client import BaseLLMClient

logger = logging.getLogger(__name__)


class LLMClientFactory:
    """Factory for managing LLM clients with automatic fallback."""

    def __init__(
        self,
        clients: list[BaseLLMClient],
        timeout: float = 30.0,
        max_retries: int = 1,
    ):
        """Initialize LLM client factory with fallback chain.

        Args:
            clients: List of LLM clients in fallback order
            timeout: Timeout per client request in seconds
            max_retries: Maximum retries per client before fallback
        """
        if not clients:
            raise ValueError("At least one LLM client must be provided")
        self._clients = clients
        self._timeout = timeout
        self._max_retries = max_retries
        self._current_client_idx = 0

    async def generate(
        self,
        prompt: str,
        context: list[dict] | None = None,
        fallback_callback: Callable[[str, Exception], None] | None = None,
    ) -> str:
        """Generate response with automatic fallback.

        Args:
            prompt: User prompt
            context: Optional conversation context
            fallback_callback: Optional callback when fallback occurs (provider_name, error)

        Returns:
            Generated response

        Raises:
            RuntimeError: If all clients in fallback chain fail
        """
        last_error = None

        for client in self._clients:
            try:
                logger.info(f"Attempting generation with {client.name}")
                response = await asyncio.wait_for(
                    client.generate(prompt, context), timeout=self._timeout
                )
                return response
            except asyncio.TimeoutError as e:
                last_error = e
                logger.warning(
                    f"{client.name} generation timed out after {self._timeout}s"
                )
                if fallback_callback:
                    fallback_callback(client.name, e)
            except Exception as e:
                last_error = e
                logger.warning(f"{client.name} generation failed: {str(e)}")
                if fallback_callback:
                    fallback_callback(client.name, e)

        raise RuntimeError(
            f"All LLM clients failed. Last error: {str(last_error)}"
        )

    async def stream(
        self,
        prompt: str,
        context: list[dict] | None = None,
        fallback_callback: Callable[[str, Exception], None] | None = None,
    ):
        """Stream response tokens with automatic fallback.

        Args:
            prompt: User prompt
            context: Optional conversation context
            fallback_callback: Optional callback when fallback occurs

        Yields:
            Response tokens

        Raises:
            RuntimeError: If all clients in fallback chain fail
        """
        last_error = None

        for client in self._clients:
            try:
                logger.info(f"Attempting streaming with {client.name}")

                stream_iterator = client.stream(prompt, context)
                async for token in stream_iterator:
                    yield token
                return
            except asyncio.TimeoutError as e:
                last_error = e
                logger.warning(
                    f"{client.name} streaming timed out after {self._timeout}s"
                )
                if fallback_callback:
                    fallback_callback(client.name, e)
            except Exception as e:
                last_error = e
                logger.warning(f"{client.name} streaming failed: {str(e)}")
                if fallback_callback:
                    fallback_callback(client.name, e)

        raise RuntimeError(
            f"All LLM clients failed during streaming. Last error: {str(last_error)}"
        )

    async def health_check(self) -> dict[str, bool]:
        """Check health of all clients in fallback chain.

        Returns:
            Dictionary mapping client names to health status
        """
        health_status = {}
        for client in self._clients:
            try:
                is_healthy = await asyncio.wait_for(
                    client.health_check(), timeout=self._timeout
                )
                health_status[client.name] = is_healthy
                logger.info(f"{client.name} health check: {is_healthy}")
            except Exception as e:
                health_status[client.name] = False
                logger.warning(f"{client.name} health check failed: {str(e)}")

        return health_status

    def get_fallback_chain(self) -> list[str]:
        """Get the fallback chain order.

        Returns:
            List of provider names in fallback order
        """
        return [client.name for client in self._clients]

    def add_client(self, client: BaseLLMClient) -> None:
        """Add a client to the end of the fallback chain.

        Args:
            client: LLM client to add
        """
        self._clients.append(client)
        logger.info(f"Added {client.name} to fallback chain")
