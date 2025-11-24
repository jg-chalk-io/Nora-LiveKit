"""Tests for BaseLLMClient interface."""

import pytest

from src.models import BaseLLMClient
from tests.mocks import MockLLMClient


class TestBaseLLMClient:
    """Test BaseLLMClient interface contract."""

    def test_base_client_is_abstract(self):
        """Test that BaseLLMClient cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseLLMClient()

    @pytest.mark.asyncio
    async def test_mock_client_generate(self):
        """Test mock client generate method."""
        client = MockLLMClient(responses=["test response"])
        response = await client.generate("test prompt")
        assert response == "test response"

    @pytest.mark.asyncio
    async def test_mock_client_stream(self):
        """Test mock client stream method."""
        client = MockLLMClient(responses=["test response"])
        tokens = []
        async for token in client.stream("test prompt"):
            tokens.append(token)
        assert len(tokens) > 0

    @pytest.mark.asyncio
    async def test_mock_client_health_check(self):
        """Test mock client health check."""
        client = MockLLMClient()
        is_healthy = await client.health_check()
        assert is_healthy is True

    @pytest.mark.asyncio
    async def test_mock_client_health_check_failure(self):
        """Test mock client health check with failure."""
        client = MockLLMClient(failure_mode="api_error")
        is_healthy = await client.health_check()
        assert is_healthy is False

    def test_mock_client_name_property(self):
        """Test mock client name property."""
        client = MockLLMClient(name="test_provider")
        assert client.name == "test_provider"

    def test_mock_client_model_property(self):
        """Test mock client model property."""
        client = MockLLMClient(model="test-model")
        assert client.model == "test-model"

    @pytest.mark.asyncio
    async def test_mock_client_timeout_error(self):
        """Test mock client timeout error."""
        client = MockLLMClient(failure_mode="timeout")
        with pytest.raises(TimeoutError):
            await client.generate("test prompt")

    @pytest.mark.asyncio
    async def test_mock_client_api_error(self):
        """Test mock client API error."""
        client = MockLLMClient(failure_mode="api_error")
        with pytest.raises(RuntimeError):
            await client.generate("test prompt")

    @pytest.mark.asyncio
    async def test_mock_client_multiple_responses(self):
        """Test mock client with multiple responses."""
        responses = ["response 1", "response 2", "response 3"]
        client = MockLLMClient(responses=responses)

        r1 = await client.generate("prompt 1")
        r2 = await client.generate("prompt 2")
        r3 = await client.generate("prompt 3")

        assert r1 == "response 1"
        assert r2 == "response 2"
        assert r3 == "response 3"

    @pytest.mark.asyncio
    async def test_mock_client_call_count(self):
        """Test mock client call counting."""
        client = MockLLMClient()
        assert client.get_call_count() == 0

        await client.generate("test 1")
        assert client.get_call_count() == 1

        await client.generate("test 2")
        assert client.get_call_count() == 2

    @pytest.mark.asyncio
    async def test_mock_client_reset(self):
        """Test mock client reset."""
        client = MockLLMClient()
        await client.generate("test")
        assert client.get_call_count() == 1

        client.reset()
        assert client.get_call_count() == 0
