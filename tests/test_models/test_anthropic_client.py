"""Tests for Anthropic client implementation."""

import os
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from src.models.anthropic_client import AnthropicClient


class TestAnthropicClientInitialization:
    """Test Anthropic client initialization."""

    def test_initialization_with_api_key(self):
        """Test client initialization with provided API key."""
        client = AnthropicClient(model="claude-3-sonnet-20240229", api_key="test-key-123")
        assert client.model == "claude-3-sonnet-20240229"
        assert client.name == "anthropic"

    def test_initialization_with_default_model(self):
        """Test client initialization with default model."""
        client = AnthropicClient(api_key="test-key-123")
        assert client.model == "claude-3-5-sonnet-20241022"

    def test_initialization_from_env_variable(self):
        """Test client initialization from ANTHROPIC_API_KEY environment variable."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "env-key-456"}):
            client = AnthropicClient()
            assert client.model == "claude-3-5-sonnet-20241022"

    def test_initialization_missing_api_key(self):
        """Test client initialization fails without API key."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="Anthropic API key not provided"):
                AnthropicClient()

    def test_initialization_api_key_priority(self):
        """Test that provided API key takes priority over env variable."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "env-key"}):
            client = AnthropicClient(api_key="provided-key")
            assert client.model == "claude-3-5-sonnet-20241022"


class TestAnthropicClientProperties:
    """Test Anthropic client property accessors."""

    def test_name_property(self):
        """Test name property returns 'anthropic'."""
        client = AnthropicClient(api_key="test-key")
        assert client.name == "anthropic"

    def test_model_property(self):
        """Test model property returns correct model identifier."""
        client = AnthropicClient(model="claude-3-opus-20240229", api_key="test-key")
        assert client.model == "claude-3-opus-20240229"

    def test_model_property_default(self):
        """Test model property with default value."""
        client = AnthropicClient(api_key="test-key")
        assert client.model == "claude-3-5-sonnet-20241022"


class TestAnthropicClientGenerate:
    """Test Anthropic client generate method."""

    @pytest.mark.asyncio
    async def test_generate_success(self):
        """Test successful generate call."""
        client = AnthropicClient(api_key="test-key")

        mock_response = AsyncMock()
        mock_response.content = [AsyncMock(text="Test response")]

        with patch("anthropic.AsyncAnthropic") as mock_anthropic:
            mock_client_instance = AsyncMock()
            mock_anthropic.return_value = mock_client_instance
            mock_client_instance.messages.create.return_value = mock_response

            response = await client.generate("test prompt")
            assert response == "Test response"

    @pytest.mark.asyncio
    async def test_generate_with_context(self):
        """Test generate with conversation context."""
        client = AnthropicClient(api_key="test-key")

        mock_response = AsyncMock()
        mock_response.content = [AsyncMock(text="Contextual response")]

        with patch("anthropic.AsyncAnthropic") as mock_anthropic:
            mock_client_instance = AsyncMock()
            mock_anthropic.return_value = mock_client_instance
            mock_client_instance.messages.create.return_value = mock_response

            context = [{"role": "user", "content": "previous message"}]
            response = await client.generate("new prompt", context)
            assert response == "Contextual response"

            # Verify context was passed correctly
            call_args = mock_client_instance.messages.create.call_args
            assert call_args[1]["messages"][0]["role"] == "user"
            assert call_args[1]["messages"][0]["content"] == "previous message"

    @pytest.mark.asyncio
    async def test_generate_empty_response(self):
        """Test generate with empty response."""
        client = AnthropicClient(api_key="test-key")

        mock_response = AsyncMock()
        mock_response.content = [AsyncMock(text=None)]

        with patch("anthropic.AsyncAnthropic") as mock_anthropic:
            mock_client_instance = AsyncMock()
            mock_anthropic.return_value = mock_client_instance
            mock_client_instance.messages.create.return_value = mock_response

            response = await client.generate("test prompt")
            assert response == ""

    @pytest.mark.asyncio
    async def test_generate_api_error(self):
        """Test generate with API error."""
        client = AnthropicClient(api_key="test-key")

        with patch("anthropic.AsyncAnthropic") as mock_anthropic:
            mock_client_instance = AsyncMock()
            mock_anthropic.return_value = mock_client_instance
            mock_client_instance.messages.create.side_effect = Exception("API Error")

            with pytest.raises(RuntimeError, match="Anthropic generation failed"):
                await client.generate("test prompt")

    @pytest.mark.asyncio
    async def test_generate_import_error(self):
        """Test generate handles import errors gracefully."""
        client = AnthropicClient(api_key="test-key")

        with patch("anthropic.AsyncAnthropic", side_effect=ImportError("anthropic not installed")):
            with pytest.raises(RuntimeError, match="Anthropic generation failed"):
                await client.generate("test prompt")

    @pytest.mark.asyncio
    async def test_generate_max_tokens(self):
        """Test that generate uses correct max_tokens."""
        client = AnthropicClient(api_key="test-key")

        mock_response = AsyncMock()
        mock_response.content = [AsyncMock(text="Response")]

        with patch("anthropic.AsyncAnthropic") as mock_anthropic:
            mock_client_instance = AsyncMock()
            mock_anthropic.return_value = mock_client_instance
            mock_client_instance.messages.create.return_value = mock_response

            await client.generate("test prompt")

            call_args = mock_client_instance.messages.create.call_args
            assert call_args[1]["max_tokens"] == 500


class TestAnthropicClientStream:
    """Test Anthropic client stream method."""

    @pytest.mark.asyncio
    async def test_stream_initialization(self):
        """Test stream initialization with context."""
        client = AnthropicClient(api_key="test-key", model="claude-3-opus-20240229")

        # Verify stream method exists and is callable
        assert hasattr(client, "stream")
        assert callable(client.stream)

    @pytest.mark.asyncio
    async def test_stream_with_context(self):
        """Test stream with conversation context."""
        client = AnthropicClient(api_key="test-key")

        with patch("anthropic.AsyncAnthropic") as mock_anthropic:
            mock_client_instance = AsyncMock()
            mock_anthropic.return_value = mock_client_instance

            # Simulate stream error to test error handling
            mock_client_instance.messages.stream.side_effect = Exception("Stream error")

            context = [{"role": "assistant", "content": "previous response"}]

            with pytest.raises(RuntimeError, match="Anthropic streaming failed"):
                async for _ in client.stream("new prompt", context):
                    pass

    @pytest.mark.asyncio
    async def test_stream_api_error(self):
        """Test stream with API error."""
        client = AnthropicClient(api_key="test-key")

        with patch("anthropic.AsyncAnthropic") as mock_anthropic:
            mock_client_instance = AsyncMock()
            mock_anthropic.return_value = mock_client_instance
            mock_client_instance.messages.stream.side_effect = Exception("API Error")

            with pytest.raises(RuntimeError, match="Anthropic streaming failed"):
                async for _ in client.stream("test prompt"):
                    pass

    @pytest.mark.asyncio
    async def test_stream_configuration(self):
        """Test that stream uses correct parameters."""
        client = AnthropicClient(api_key="test-key")

        mock_stream = AsyncMock()
        mock_stream.__aenter__ = AsyncMock(return_value=mock_stream)
        mock_stream.__aexit__ = AsyncMock(return_value=None)
        mock_stream.text_stream = iter(["Response"])

        with patch("anthropic.AsyncAnthropic") as mock_anthropic:
            mock_client_instance = AsyncMock()
            mock_anthropic.return_value = mock_client_instance
            mock_client_instance.messages.stream.return_value = mock_stream

            async for _ in client.stream("test prompt"):
                pass

            call_args = mock_client_instance.messages.stream.call_args
            assert call_args[1]["max_tokens"] == 500


class TestAnthropicClientHealthCheck:
    """Test Anthropic client health check method."""

    @pytest.mark.asyncio
    async def test_health_check_success(self):
        """Test successful health check."""
        client = AnthropicClient(api_key="test-key")

        mock_response = AsyncMock()
        mock_response.content = [AsyncMock(text="ok")]

        with patch("anthropic.AsyncAnthropic") as mock_anthropic:
            mock_client_instance = AsyncMock()
            mock_anthropic.return_value = mock_client_instance
            mock_client_instance.messages.create.return_value = mock_response

            result = await client.health_check()
            assert result is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self):
        """Test health check with API error."""
        client = AnthropicClient(api_key="test-key")

        with patch("anthropic.AsyncAnthropic") as mock_anthropic:
            mock_client_instance = AsyncMock()
            mock_anthropic.return_value = mock_client_instance
            mock_client_instance.messages.create.side_effect = Exception("Connection failed")

            result = await client.health_check()
            assert result is False

    @pytest.mark.asyncio
    async def test_health_check_none_response(self):
        """Test health check with None response."""
        client = AnthropicClient(api_key="test-key")

        mock_response = AsyncMock()
        mock_response.content = [AsyncMock(text=None)]

        with patch("anthropic.AsyncAnthropic") as mock_anthropic:
            mock_client_instance = AsyncMock()
            mock_anthropic.return_value = mock_client_instance
            mock_client_instance.messages.create.return_value = mock_response

            result = await client.health_check()
            assert result is False

    @pytest.mark.asyncio
    async def test_health_check_uses_minimal_tokens(self):
        """Test that health check uses minimal API call."""
        client = AnthropicClient(api_key="test-key")

        mock_response = AsyncMock()
        mock_response.content = [AsyncMock(text="ok")]

        with patch("anthropic.AsyncAnthropic") as mock_anthropic:
            mock_client_instance = AsyncMock()
            mock_anthropic.return_value = mock_client_instance
            mock_client_instance.messages.create.return_value = mock_response

            await client.health_check()

            call_args = mock_client_instance.messages.create.call_args
            assert call_args[1]["max_tokens"] == 1
