"""Tests for configuration module."""

import os
import pytest
from nora_livekit.config import Config, VoiceConfig, setup_logging


class TestVoiceConfig:
    """Tests for VoiceConfig dataclass."""

    def test_voice_config_initialization(self):
        """Test VoiceConfig initialization with default values."""
        voice_config = VoiceConfig(deepgram_api_key="test-key")

        assert voice_config.deepgram_api_key == "test-key"
        assert voice_config.deepgram_model == "nova-2"
        assert voice_config.deepgram_language == "en-US"
        assert voice_config.cartesia_api_key == ""
        assert voice_config.cartesia_voice_id == "default-sonic-voice"
        assert voice_config.cartesia_speed == 1.0
        assert voice_config.cartesia_emotion == "neutral"
        assert voice_config.sample_rate == 16000
        assert voice_config.channels == 1
        assert voice_config.latency_target_ms == 500
        assert voice_config.vad_threshold == 0.5

    def test_voice_config_custom_values(self):
        """Test VoiceConfig initialization with custom values."""
        voice_config = VoiceConfig(
            deepgram_api_key="test-key",
            deepgram_model="nova-3",
            cartesia_api_key="cartesia-key",
            cartesia_speed=1.5,
            cartesia_emotion="cheerful",
            sample_rate=48000,
        )

        assert voice_config.deepgram_api_key == "test-key"
        assert voice_config.deepgram_model == "nova-3"
        assert voice_config.cartesia_api_key == "cartesia-key"
        assert voice_config.cartesia_speed == 1.5
        assert voice_config.cartesia_emotion == "cheerful"
        assert voice_config.sample_rate == 48000


class TestConfigInitialization:
    """Tests for Config class initialization."""

    def test_config_initialization_livekit_only(self):
        """Test Config initialization with LiveKit parameters only."""
        config = Config(
            livekit_url="wss://livekit.example.com",
            livekit_api_key="api-key",
            livekit_api_secret="api-secret",
        )

        assert config.livekit_url == "wss://livekit.example.com"
        assert config.livekit_api_key == "api-key"
        assert config.livekit_api_secret == "api-secret"
        assert config.health_check_port == 8080
        assert config.log_level == "INFO"
        assert config.log_format == "json"
        assert config.voice is None

    def test_config_initialization_with_voice(self):
        """Test Config initialization with voice configuration."""
        voice_config = VoiceConfig(deepgram_api_key="test-key")
        config = Config(
            livekit_url="wss://livekit.example.com",
            livekit_api_key="api-key",
            livekit_api_secret="api-secret",
            voice=voice_config,
        )

        assert config.voice is not None
        assert config.voice.deepgram_api_key == "test-key"

    def test_config_from_env_missing_livekit_url(self):
        """Test Config.from_env() raises error when LIVEKIT_URL is missing."""
        # Clear environment
        env_backup = os.environ.copy()
        os.environ.clear()

        try:
            with pytest.raises(ValueError) as exc_info:
                Config.from_env()

            assert "LIVEKIT_URL" in str(exc_info.value)
        finally:
            os.environ.clear()
            os.environ.update(env_backup)

    def test_config_from_env_missing_api_key(self):
        """Test Config.from_env() raises error when LIVEKIT_API_KEY is missing."""
        env_backup = os.environ.copy()
        os.environ.clear()

        try:
            os.environ["LIVEKIT_URL"] = "wss://livekit.example.com"

            with pytest.raises(ValueError) as exc_info:
                Config.from_env()

            assert "LIVEKIT_API_KEY" in str(exc_info.value)
        finally:
            os.environ.clear()
            os.environ.update(env_backup)

    def test_config_from_env_missing_api_secret(self):
        """Test Config.from_env() raises error when LIVEKIT_API_SECRET is missing."""
        env_backup = os.environ.copy()
        os.environ.clear()

        try:
            os.environ["LIVEKIT_URL"] = "wss://livekit.example.com"
            os.environ["LIVEKIT_API_KEY"] = "api-key"

            with pytest.raises(ValueError) as exc_info:
                Config.from_env()

            assert "LIVEKIT_API_SECRET" in str(exc_info.value)
        finally:
            os.environ.clear()
            os.environ.update(env_backup)

    def test_config_from_env_livekit_only(self):
        """Test Config.from_env() with only LiveKit configuration."""
        env_backup = os.environ.copy()
        os.environ.clear()

        try:
            os.environ["LIVEKIT_URL"] = "wss://livekit.example.com"
            os.environ["LIVEKIT_API_KEY"] = "api-key"
            os.environ["LIVEKIT_API_SECRET"] = "api-secret"

            config = Config.from_env()

            assert config.livekit_url == "wss://livekit.example.com"
            assert config.livekit_api_key == "api-key"
            assert config.livekit_api_secret == "api-secret"
            assert config.health_check_port == 8080
            assert config.voice is None
        finally:
            os.environ.clear()
            os.environ.update(env_backup)

    def test_config_from_env_with_custom_port(self):
        """Test Config.from_env() with custom health check port."""
        env_backup = os.environ.copy()
        os.environ.clear()

        try:
            os.environ["LIVEKIT_URL"] = "wss://livekit.example.com"
            os.environ["LIVEKIT_API_KEY"] = "api-key"
            os.environ["LIVEKIT_API_SECRET"] = "api-secret"
            os.environ["HEALTH_CHECK_PORT"] = "9000"

            config = Config.from_env()

            assert config.health_check_port == 9000
        finally:
            os.environ.clear()
            os.environ.update(env_backup)

    def test_config_from_env_with_logging_config(self):
        """Test Config.from_env() with logging configuration."""
        env_backup = os.environ.copy()
        os.environ.clear()

        try:
            os.environ["LIVEKIT_URL"] = "wss://livekit.example.com"
            os.environ["LIVEKIT_API_KEY"] = "api-key"
            os.environ["LIVEKIT_API_SECRET"] = "api-secret"
            os.environ["LOG_LEVEL"] = "DEBUG"
            os.environ["LOG_FORMAT"] = "text"

            config = Config.from_env()

            assert config.log_level == "DEBUG"
            assert config.log_format == "text"
        finally:
            os.environ.clear()
            os.environ.update(env_backup)

    def test_config_from_env_with_test_room(self):
        """Test Config.from_env() with test room configuration."""
        env_backup = os.environ.copy()
        os.environ.clear()

        try:
            os.environ["LIVEKIT_URL"] = "wss://livekit.example.com"
            os.environ["LIVEKIT_API_KEY"] = "api-key"
            os.environ["LIVEKIT_API_SECRET"] = "api-secret"
            os.environ["LIVEKIT_TEST_ROOM"] = "test-room-001"

            config = Config.from_env()

            assert config.test_room == "test-room-001"
        finally:
            os.environ.clear()
            os.environ.update(env_backup)

    def test_config_from_env_with_voice_config(self):
        """Test Config.from_env() with voice configuration."""
        env_backup = os.environ.copy()
        os.environ.clear()

        try:
            os.environ["LIVEKIT_URL"] = "wss://livekit.example.com"
            os.environ["LIVEKIT_API_KEY"] = "api-key"
            os.environ["LIVEKIT_API_SECRET"] = "api-secret"
            os.environ["DEEPGRAM_API_KEY"] = "deepgram-key"
            os.environ["CARTESIA_API_KEY"] = "cartesia-key"
            os.environ["DEEPGRAM_MODEL"] = "nova-3"
            os.environ["CARTESIA_SPEED"] = "1.5"

            config = Config.from_env()

            assert config.voice is not None
            assert config.voice.deepgram_api_key == "deepgram-key"
            assert config.voice.cartesia_api_key == "cartesia-key"
            assert config.voice.deepgram_model == "nova-3"
            assert config.voice.cartesia_speed == 1.5
        finally:
            os.environ.clear()
            os.environ.update(env_backup)

    def test_config_from_env_voice_config_defaults(self):
        """Test Config.from_env() voice config uses default values when not specified."""
        env_backup = os.environ.copy()
        os.environ.clear()

        try:
            os.environ["LIVEKIT_URL"] = "wss://livekit.example.com"
            os.environ["LIVEKIT_API_KEY"] = "api-key"
            os.environ["LIVEKIT_API_SECRET"] = "api-secret"
            os.environ["DEEPGRAM_API_KEY"] = "deepgram-key"

            config = Config.from_env()

            assert config.voice is not None
            assert config.voice.deepgram_model == "nova-2"
            assert config.voice.deepgram_language == "en-US"
            assert config.voice.cartesia_voice_id == "default-sonic-voice"
            assert config.voice.cartesia_speed == 1.0
            assert config.voice.sample_rate == 16000
        finally:
            os.environ.clear()
            os.environ.update(env_backup)


class TestLoggingSetup:
    """Tests for logging setup."""

    def test_setup_logging_json_format(self):
        """Test setup_logging configures JSON format logging."""
        config = Config(
            livekit_url="wss://livekit.example.com",
            livekit_api_key="api-key",
            livekit_api_secret="api-secret",
            log_format="json",
        )

        # Should not raise any exceptions
        setup_logging(config)

    def test_setup_logging_text_format(self):
        """Test setup_logging configures text format logging."""
        config = Config(
            livekit_url="wss://livekit.example.com",
            livekit_api_key="api-key",
            livekit_api_secret="api-secret",
            log_format="text",
        )

        # Should not raise any exceptions
        setup_logging(config)

    def test_setup_logging_debug_level(self):
        """Test setup_logging configures DEBUG log level."""
        config = Config(
            livekit_url="wss://livekit.example.com",
            livekit_api_key="api-key",
            livekit_api_secret="api-secret",
            log_level="DEBUG",
        )

        # Should not raise any exceptions
        setup_logging(config)
