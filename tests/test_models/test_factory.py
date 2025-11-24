"""Tests for LLMClientFactory."""

import pytest

from src.models import LLMClientFactory
from tests.mocks import MockLLMClient


class TestLLMClientFactory:
    """Test LLMClientFactory with fallback chain."""

    def test_factory_requires_clients(self):
        """Test that factory requires at least one client."""
        with pytest.raises(ValueError):
            LLMClientFactory([])

    def test_factory_initialization(self):
        """Test factory initialization with clients."""
        client = MockLLMClient(name="test")
        factory = LLMClientFactory([client])
        assert factory is not None

    @pytest.mark.asyncio
    async def test_factory_generate_success(self):
        """Test factory generate with successful client."""
        client = MockLLMClient(responses=["test response"])
        factory = LLMClientFactory([client])
        response = await factory.generate("test prompt")
        assert response == "test response"

    @pytest.mark.asyncio
    async def test_factory_fallback_chain(self):
        """Test factory fallback to next client on failure."""
        client1 = MockLLMClient(name="primary", failure_mode="api_error")
        client2 = MockLLMClient(name="secondary", responses=["fallback response"])
        factory = LLMClientFactory([client1, client2])

        response = await factory.generate("test prompt")
        assert response == "fallback response"

    @pytest.mark.asyncio
    async def test_factory_fallback_chain_all_fail(self):
        """Test factory when all clients fail."""
        client1 = MockLLMClient(failure_mode="api_error")
        client2 = MockLLMClient(failure_mode="timeout")
        factory = LLMClientFactory([client1, client2])

        with pytest.raises(RuntimeError):
            await factory.generate("test prompt")

    @pytest.mark.asyncio
    async def test_factory_fallback_callback(self):
        """Test factory fallback callback."""
        client1 = MockLLMClient(name="primary", failure_mode="api_error")
        client2 = MockLLMClient(name="secondary", responses=["response"])
        factory = LLMClientFactory([client1, client2])

        fallback_calls = []

        def fallback_callback(provider: str, error: Exception):
            fallback_calls.append((provider, str(error)))

        response = await factory.generate(
            "test prompt", fallback_callback=fallback_callback
        )

        assert response == "response"
        assert len(fallback_calls) == 1
        assert fallback_calls[0][0] == "primary"

    @pytest.mark.asyncio
    async def test_factory_health_check(self):
        """Test factory health check."""
        client1 = MockLLMClient(name="healthy", failure_mode=None)
        client2 = MockLLMClient(name="unhealthy", failure_mode="api_error")
        factory = LLMClientFactory([client1, client2])

        health = await factory.health_check()
        assert health["healthy"] is True
        assert health["unhealthy"] is False

    def test_factory_get_fallback_chain(self):
        """Test factory get fallback chain."""
        client1 = MockLLMClient(name="openai")
        client2 = MockLLMClient(name="anthropic")
        client3 = MockLLMClient(name="google")
        factory = LLMClientFactory([client1, client2, client3])

        chain = factory.get_fallback_chain()
        assert chain == ["openai", "anthropic", "google"]

    def test_factory_add_client(self):
        """Test factory add client."""
        client1 = MockLLMClient(name="primary")
        factory = LLMClientFactory([client1])
        assert len(factory.get_fallback_chain()) == 1

        client2 = MockLLMClient(name="secondary")
        factory.add_client(client2)
        assert len(factory.get_fallback_chain()) == 2
        assert factory.get_fallback_chain() == ["primary", "secondary"]

    @pytest.mark.asyncio
    async def test_factory_stream(self):
        """Test factory stream method."""
        client = MockLLMClient(responses=["test response"])
        factory = LLMClientFactory([client])

        tokens = []
        async for token in factory.stream("test prompt"):
            tokens.append(token)

        assert len(tokens) > 0

    @pytest.mark.asyncio
    async def test_factory_stream_with_fallback(self):
        """Test factory stream with fallback."""
        client1 = MockLLMClient(name="primary", failure_mode="timeout")
        client2 = MockLLMClient(name="secondary", responses=["fallback"])
        factory = LLMClientFactory([client1, client2])

        tokens = []
        async for token in factory.stream("test prompt"):
            tokens.append(token)

        assert len(tokens) > 0
