"""Tests for configuration loader."""

import os
import pytest
from nora_livekit.config import Config


class TestConfigFromEnv:
    """Test Config.from_env() method."""

    def test_config_from_env_success(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test successful config loading from environment variables."""
        monkeypatch.setenv("LIVEKIT_URL", "wss://test.livekit.cloud")
        monkeypatch.setenv("LIVEKIT_API_KEY", "test-key")
        monkeypatch.setenv("LIVEKIT_API_SECRET", "test-secret")

        config = Config.from_env()

        assert config.livekit_url == "wss://test.livekit.cloud"
        assert config.livekit_api_key == "test-key"
        assert config.livekit_api_secret == "test-secret"
        assert config.health_check_port == 8080
        assert config.log_level == "INFO"
        assert config.log_format == "json"
        assert config.test_room is None

    def test_config_from_env_with_optional_vars(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test config loading with optional environment variables."""
        monkeypatch.setenv("LIVEKIT_URL", "wss://test.livekit.cloud")
        monkeypatch.setenv("LIVEKIT_API_KEY", "test-key")
        monkeypatch.setenv("LIVEKIT_API_SECRET", "test-secret")
        monkeypatch.setenv("HEALTH_CHECK_PORT", "9090")
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")
        monkeypatch.setenv("LOG_FORMAT", "text")
        monkeypatch.setenv("LIVEKIT_TEST_ROOM", "test-room-001")

        config = Config.from_env()

        assert config.health_check_port == 9090
        assert config.log_level == "DEBUG"
        assert config.log_format == "text"
        assert config.test_room == "test-room-001"

    def test_config_from_env_missing_livekit_url(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test config loading with missing LIVEKIT_URL."""
        monkeypatch.delenv("LIVEKIT_URL", raising=False)
        monkeypatch.setenv("LIVEKIT_API_KEY", "test-key")
        monkeypatch.setenv("LIVEKIT_API_SECRET", "test-secret")

        with pytest.raises(ValueError, match="LIVEKIT_URL is required"):
            Config.from_env()

    def test_config_from_env_missing_api_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test config loading with missing LIVEKIT_API_KEY."""
        monkeypatch.setenv("LIVEKIT_URL", "wss://test.livekit.cloud")
        monkeypatch.delenv("LIVEKIT_API_KEY", raising=False)
        monkeypatch.setenv("LIVEKIT_API_SECRET", "test-secret")

        with pytest.raises(ValueError, match="LIVEKIT_API_KEY is required"):
            Config.from_env()

    def test_config_from_env_missing_api_secret(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test config loading with missing LIVEKIT_API_SECRET."""
        monkeypatch.setenv("LIVEKIT_URL", "wss://test.livekit.cloud")
        monkeypatch.setenv("LIVEKIT_API_KEY", "test-key")
        monkeypatch.delenv("LIVEKIT_API_SECRET", raising=False)

        with pytest.raises(ValueError, match="LIVEKIT_API_SECRET is required"):
            Config.from_env()

    def test_config_from_env_invalid_port(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test config loading with invalid port number."""
        monkeypatch.setenv("LIVEKIT_URL", "wss://test.livekit.cloud")
        monkeypatch.setenv("LIVEKIT_API_KEY", "test-key")
        monkeypatch.setenv("LIVEKIT_API_SECRET", "test-secret")
        monkeypatch.setenv("HEALTH_CHECK_PORT", "invalid")

        with pytest.raises(ValueError):
            Config.from_env()

    def test_config_from_env_invalid_url_scheme(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test config loading with invalid URL scheme."""
        monkeypatch.setenv("LIVEKIT_URL", "http://test.livekit.cloud")  # Should be wss:// or ws://
        monkeypatch.setenv("LIVEKIT_API_KEY", "test-key")
        monkeypatch.setenv("LIVEKIT_API_SECRET", "test-secret")

        with pytest.raises(ValueError, match="LIVEKIT_URL must start with wss:// or ws://"):
            Config.from_env()


class TestConfigInitialization:
    """Test Config class initialization."""

    def test_config_dataclass_creation(self) -> None:
        """Test creating Config instance directly."""
        config = Config(
            livekit_url="wss://test.livekit.cloud",
            livekit_api_key="test-key",
            livekit_api_secret="test-secret",
        )

        assert config.livekit_url == "wss://test.livekit.cloud"
        assert config.livekit_api_key == "test-key"
        assert config.livekit_api_secret == "test-secret"
        assert config.health_check_port == 8080
        assert config.log_level == "INFO"
        assert config.log_format == "json"

    def test_config_with_custom_port(self) -> None:
        """Test creating Config with custom port."""
        config = Config(
            livekit_url="wss://test.livekit.cloud",
            livekit_api_key="test-key",
            livekit_api_secret="test-secret",
            health_check_port=9090,
        )

        assert config.health_check_port == 9090


class TestLoggingSetup:
    """Test logging configuration setup."""

    def test_setup_logging_configures_structlog(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that setup_logging configures structlog correctly."""
        from nora_livekit.config import setup_logging

        config = Config(
            livekit_url="wss://test.livekit.cloud",
            livekit_api_key="test-key",
            livekit_api_secret="test-secret",
            log_level="DEBUG",
        )

        # Should not raise an error
        setup_logging(config)
