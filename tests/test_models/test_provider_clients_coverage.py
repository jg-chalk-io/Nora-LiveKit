"""Additional coverage tests for Google and Ollama client initialization and error paths."""

import os
import pytest
from unittest.mock import patch, AsyncMock
from src.models.google_client import GoogleClient
from src.models.ollama_client import OllamaClient


class TestGoogleClientCoverage:
    """Additional test coverage for Google client."""

    def test_initialization_with_api_key(self):
        """Test Google client initialization with provided API key."""
        client = GoogleClient(model="gemini-1.5-pro", api_key="test-key-123")
        assert client.model == "gemini-1.5-pro"
        assert client.name == "google"

    def test_initialization_with_default_model(self):
        """Test Google client with default model."""
        client = GoogleClient(api_key="test-key")
        assert client.model == "gemini-2.0-flash"

    def test_initialization_from_env_variable(self):
        """Test Google client from GOOGLE_API_KEY env var."""
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "env-key-456"}):
            client = GoogleClient()
            assert client.model == "gemini-2.0-flash"

    def test_initialization_missing_api_key(self):
        """Test Google client fails without API key."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="Google API key not provided"):
                GoogleClient()

    def test_initialization_api_key_priority(self):
        """Test provided API key takes priority."""
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "env-key"}):
            client = GoogleClient(api_key="provided-key")
            assert client.model == "gemini-2.0-flash"

    def test_name_property(self):
        """Test name property."""
        client = GoogleClient(api_key="test-key")
        assert client.name == "google"

    def test_model_property(self):
        """Test model property."""
        client = GoogleClient(model="gemini-1.5-flash", api_key="test-key")
        assert client.model == "gemini-1.5-flash"

    def test_model_defaults(self):
        """Test Google client model defaults."""
        client1 = GoogleClient(api_key="test-key")
        client2 = GoogleClient(api_key="test-key", model="custom-model")
        assert client1.model == "gemini-2.0-flash"
        assert client2.model == "custom-model"


class TestOllamaClientCoverage:
    """Additional test coverage for Ollama client."""

    def test_initialization_with_base_url(self):
        """Test Ollama client with provided base URL."""
        client = OllamaClient(model="llama2", base_url="http://ollama.local:11434")
        assert client.model == "llama2"
        assert client.name == "ollama"

    def test_initialization_with_default_model(self):
        """Test Ollama client with default model."""
        client = OllamaClient(base_url="http://localhost:11434")
        assert client.model == "mistral"

    def test_initialization_from_env_variable(self):
        """Test Ollama client from OLLAMA_BASE_URL env var."""
        with patch.dict(os.environ, {"OLLAMA_BASE_URL": "http://ollama-server:11434"}):
            client = OllamaClient()
            assert client.model == "mistral"

    def test_initialization_default_base_url(self):
        """Test Ollama client uses default base URL."""
        with patch.dict(os.environ, {}, clear=True):
            client = OllamaClient()
            assert client.model == "mistral"

    def test_initialization_base_url_priority(self):
        """Test provided base URL takes priority."""
        with patch.dict(os.environ, {"OLLAMA_BASE_URL": "http://env-url:11434"}):
            client = OllamaClient(base_url="http://provided-url:11434")
            assert client.model == "mistral"

    def test_name_property(self):
        """Test name property."""
        client = OllamaClient(base_url="http://localhost:11434")
        assert client.name == "ollama"

    def test_model_property(self):
        """Test model property."""
        client = OllamaClient(model="neural-chat", base_url="http://localhost:11434")
        assert client.model == "neural-chat"

    def test_model_defaults(self):
        """Test Ollama client model defaults."""
        client1 = OllamaClient(base_url="http://localhost:11434")
        client2 = OllamaClient(model="llama2", base_url="http://localhost:11434")
        assert client1.model == "mistral"
        assert client2.model == "llama2"
