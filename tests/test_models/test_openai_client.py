"""Tests for OpenAI client implementation."""

import os
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from src.models.openai_client import OpenAIClient


class TestOpenAIClientInitialization:
    """Test OpenAI client initialization."""

    def test_initialization_with_api_key(self):
        """Test client initialization with provided API key."""
        client = OpenAIClient(model="gpt-4", api_key="test-key-123")
        assert client.model == "gpt-4"
        assert client.name == "openai"

    def test_initialization_with_default_model(self):
        """Test client initialization with default model."""
        client = OpenAIClient(api_key="test-key-123")
        assert client.model == "gpt-4-turbo"

    def test_initialization_from_env_variable(self):
        """Test client initialization from OPENAI_API_KEY environment variable."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "env-key-456"}):
            client = OpenAIClient()
            assert client.model == "gpt-4-turbo"

    def test_initialization_missing_api_key(self):
        """Test client initialization fails without API key."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="OpenAI API key not provided"):
                OpenAIClient()

    def test_initialization_api_key_priority(self):
        """Test that provided API key takes priority over env variable."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "env-key"}):
            client = OpenAIClient(api_key="provided-key")
            # Verify the client was created with provided key
            assert client.model == "gpt-4-turbo"


class TestOpenAIClientProperties:
    """Test OpenAI client property accessors."""

    def test_name_property(self):
        """Test name property returns 'openai'."""
        client = OpenAIClient(api_key="test-key")
        assert client.name == "openai"

    def test_model_property(self):
        """Test model property returns correct model identifier."""
        client = OpenAIClient(model="gpt-3.5-turbo", api_key="test-key")
        assert client.model == "gpt-3.5-turbo"

    def test_model_property_default(self):
        """Test model property with default value."""
        client = OpenAIClient(api_key="test-key")
        assert client.model == "gpt-4-turbo"


class TestOpenAIClientGenerate:
    """Test OpenAI client generate method."""

    @pytest.mark.asyncio
    async def test_generate_success(self):
        """Test successful generate call."""
        client = OpenAIClient(api_key="test-key")

        mock_response = AsyncMock()
        mock_response.choices[0].message.content = "Test response"

        with patch("openai.AsyncOpenAI") as mock_openai:
            mock_client_instance = AsyncMock()
            mock_openai.return_value = mock_client_instance
            mock_client_instance.chat.completions.create.return_value = mock_response

            response = await client.generate("test prompt")
            assert response == "Test response"

    @pytest.mark.asyncio
    async def test_generate_with_context(self):
        """Test generate with conversation context."""
        client = OpenAIClient(api_key="test-key")

        mock_response = AsyncMock()
        mock_response.choices[0].message.content = "Contextual response"

        with patch("openai.AsyncOpenAI") as mock_openai:
            mock_client_instance = AsyncMock()
            mock_openai.return_value = mock_client_instance
            mock_client_instance.chat.completions.create.return_value = mock_response

            context = [{"role": "user", "content": "previous message"}]
            response = await client.generate("new prompt", context)
            assert response == "Contextual response"

            # Verify context was passed correctly
            call_args = mock_client_instance.chat.completions.create.call_args
            assert call_args[1]["messages"][0]["role"] == "user"
            assert call_args[1]["messages"][0]["content"] == "previous message"

    @pytest.mark.asyncio
    async def test_generate_empty_response(self):
        """Test generate with empty response."""
        client = OpenAIClient(api_key="test-key")

        mock_response = AsyncMock()
        mock_response.choices[0].message.content = None

        with patch("openai.AsyncOpenAI") as mock_openai:
            mock_client_instance = AsyncMock()
            mock_openai.return_value = mock_client_instance
            mock_client_instance.chat.completions.create.return_value = mock_response

            response = await client.generate("test prompt")
            assert response == ""

    @pytest.mark.asyncio
    async def test_generate_api_error(self):
        """Test generate with API error."""
        client = OpenAIClient(api_key="test-key")

        with patch("openai.AsyncOpenAI") as mock_openai:
            mock_client_instance = AsyncMock()
            mock_openai.return_value = mock_client_instance
            mock_client_instance.chat.completions.create.side_effect = Exception("API Error")

            with pytest.raises(RuntimeError, match="OpenAI generation failed"):
                await client.generate("test prompt")

    @pytest.mark.asyncio
    async def test_generate_import_error(self):
        """Test generate handles import errors gracefully."""
        client = OpenAIClient(api_key="test-key")

        with patch("openai.AsyncOpenAI", side_effect=ImportError("openai not installed")):
            with pytest.raises(RuntimeError, match="OpenAI generation failed"):
                await client.generate("test prompt")

    @pytest.mark.asyncio
    async def test_generate_temperature_and_max_tokens(self):
        """Test that generate uses correct temperature and max_tokens."""
        client = OpenAIClient(api_key="test-key")

        mock_response = AsyncMock()
        mock_response.choices[0].message.content = "Response"

        with patch("openai.AsyncOpenAI") as mock_openai:
            mock_client_instance = AsyncMock()
            mock_openai.return_value = mock_client_instance
            mock_client_instance.chat.completions.create.return_value = mock_response

            await client.generate("test prompt")

            call_args = mock_client_instance.chat.completions.create.call_args
            assert call_args[1]["temperature"] == 0.7
            assert call_args[1]["max_tokens"] == 500


class TestOpenAIClientStream:
    """Test OpenAI client stream method."""

    @pytest.mark.asyncio
    async def test_stream_success(self):
        """Test successful stream call."""
        client = OpenAIClient(api_key="test-key")

        # Create mock chunks
        mock_chunk1 = AsyncMock()
        mock_chunk1.choices[0].delta.content = "Hello "
        mock_chunk2 = AsyncMock()
        mock_chunk2.choices[0].delta.content = "world"

        with patch("openai.AsyncOpenAI") as mock_openai:
            mock_client_instance = AsyncMock()
            mock_openai.return_value = mock_client_instance

            # Create async iterator for stream
            async def async_chunk_generator():
                yield mock_chunk1
                yield mock_chunk2

            mock_client_instance.chat.completions.create.return_value = async_chunk_generator()

            tokens = []
            async for token in client.stream("test prompt"):
                tokens.append(token)

            assert tokens == ["Hello ", "world"]

    @pytest.mark.asyncio
    async def test_stream_with_context(self):
        """Test stream with conversation context."""
        client = OpenAIClient(api_key="test-key")

        mock_chunk = AsyncMock()
        mock_chunk.choices[0].delta.content = "Response"

        with patch("openai.AsyncOpenAI") as mock_openai:
            mock_client_instance = AsyncMock()
            mock_openai.return_value = mock_client_instance

            async def async_chunk_generator():
                yield mock_chunk

            mock_client_instance.chat.completions.create.return_value = async_chunk_generator()

            context = [{"role": "assistant", "content": "previous response"}]
            tokens = []
            async for token in client.stream("new prompt", context):
                tokens.append(token)

            assert len(tokens) > 0

    @pytest.mark.asyncio
    async def test_stream_empty_delta(self):
        """Test stream handles empty delta content."""
        client = OpenAIClient(api_key="test-key")

        mock_chunk1 = AsyncMock()
        mock_chunk1.choices[0].delta.content = None
        mock_chunk2 = AsyncMock()
        mock_chunk2.choices[0].delta.content = "Text"

        with patch("openai.AsyncOpenAI") as mock_openai:
            mock_client_instance = AsyncMock()
            mock_openai.return_value = mock_client_instance

            async def async_chunk_generator():
                yield mock_chunk1
                yield mock_chunk2

            mock_client_instance.chat.completions.create.return_value = async_chunk_generator()

            tokens = []
            async for token in client.stream("test prompt"):
                tokens.append(token)

            assert tokens == ["Text"]

    @pytest.mark.asyncio
    async def test_stream_api_error(self):
        """Test stream with API error."""
        client = OpenAIClient(api_key="test-key")

        with patch("openai.AsyncOpenAI") as mock_openai:
            mock_client_instance = AsyncMock()
            mock_openai.return_value = mock_client_instance
            mock_client_instance.chat.completions.create.side_effect = Exception("API Error")

            with pytest.raises(RuntimeError, match="OpenAI streaming failed"):
                async for _ in client.stream("test prompt"):
                    pass

    @pytest.mark.asyncio
    async def test_stream_configuration(self):
        """Test that stream uses correct parameters."""
        client = OpenAIClient(api_key="test-key")

        mock_chunk = AsyncMock()
        mock_chunk.choices[0].delta.content = "Response"

        with patch("openai.AsyncOpenAI") as mock_openai:
            mock_client_instance = AsyncMock()
            mock_openai.return_value = mock_client_instance

            async def async_chunk_generator():
                yield mock_chunk

            mock_client_instance.chat.completions.create.return_value = async_chunk_generator()

            async for _ in client.stream("test prompt"):
                pass

            call_args = mock_client_instance.chat.completions.create.call_args
            assert call_args[1]["temperature"] == 0.7
            assert call_args[1]["max_tokens"] == 500
            assert call_args[1]["stream"] is True


class TestOpenAIClientHealthCheck:
    """Test OpenAI client health check method."""

    @pytest.mark.asyncio
    async def test_health_check_success(self):
        """Test successful health check."""
        client = OpenAIClient(api_key="test-key")

        mock_response = AsyncMock()
        mock_response.choices[0].message.content = "ok"

        with patch("openai.AsyncOpenAI") as mock_openai:
            mock_client_instance = AsyncMock()
            mock_openai.return_value = mock_client_instance
            mock_client_instance.chat.completions.create.return_value = mock_response

            result = await client.health_check()
            assert result is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self):
        """Test health check with API error."""
        client = OpenAIClient(api_key="test-key")

        with patch("openai.AsyncOpenAI") as mock_openai:
            mock_client_instance = AsyncMock()
            mock_openai.return_value = mock_client_instance
            mock_client_instance.chat.completions.create.side_effect = Exception("Connection failed")

            result = await client.health_check()
            assert result is False

    @pytest.mark.asyncio
    async def test_health_check_none_response(self):
        """Test health check with None response."""
        client = OpenAIClient(api_key="test-key")

        mock_response = AsyncMock()
        mock_response.choices[0].message.content = None

        with patch("openai.AsyncOpenAI") as mock_openai:
            mock_client_instance = AsyncMock()
            mock_openai.return_value = mock_client_instance
            mock_client_instance.chat.completions.create.return_value = mock_response

            result = await client.health_check()
            assert result is False

    @pytest.mark.asyncio
    async def test_health_check_uses_minimal_tokens(self):
        """Test that health check uses minimal API call."""
        client = OpenAIClient(api_key="test-key")

        mock_response = AsyncMock()
        mock_response.choices[0].message.content = "ok"

        with patch("openai.AsyncOpenAI") as mock_openai:
            mock_client_instance = AsyncMock()
            mock_openai.return_value = mock_client_instance
            mock_client_instance.chat.completions.create.return_value = mock_response

            await client.health_check()

            call_args = mock_client_instance.chat.completions.create.call_args
            assert call_args[1]["max_tokens"] == 1
