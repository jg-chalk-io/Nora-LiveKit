"""Configuration management for Nora LiveKit agent with voice pipeline support."""

import os
import logging
import structlog
from dataclasses import dataclass
from typing import Optional


@dataclass
class ConversationConfig:
    """Conversation engine configuration.

    Satisfies: REQ-IR-CONFIG-001
    """

    # LLM Configuration
    llm_provider: str = "openai"  # "openai" or "anthropic"
    llm_api_key: str = ""
    llm_model: str = "gpt-4"  # or "claude-3-sonnet-20240229"
    llm_temperature: float = 0.7
    llm_max_tokens: int = 150

    # Context Configuration
    max_history: int = 20

    # Turn Detection Configuration
    vad_threshold: float = 0.5
    min_speech_duration_ms: int = 300
    silence_duration_ms: int = 700

    # Conversation Behavior
    idle_timeout_seconds: int = 120  # 2 minutes
    enable_interruptions: bool = True
    fallback_response: str = "I'm having trouble right now. Please try again."


@dataclass
class VoiceConfig:
    """Voice pipeline configuration."""

    deepgram_api_key: str
    deepgram_model: str = "nova-2"
    deepgram_language: str = "en-US"
    cartesia_api_key: str = ""
    cartesia_voice_id: str = "default-sonic-voice"
    cartesia_speed: float = 1.0
    cartesia_emotion: str = "neutral"
    sample_rate: int = 16000
    channels: int = 1
    latency_target_ms: int = 500
    vad_threshold: float = 0.5


@dataclass
class Config:
    """Main configuration for Nora LiveKit agent."""

    livekit_url: str
    livekit_api_key: str
    livekit_api_secret: str
    health_check_port: int = 8080
    log_level: str = "INFO"
    log_format: str = "json"
    test_room: Optional[str] = None
    voice: Optional[VoiceConfig] = None
    conversation: Optional[ConversationConfig] = None

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables.

        Required environment variables:
        - LIVEKIT_URL: LiveKit server WebSocket URL
        - LIVEKIT_API_KEY: LiveKit API key
        - LIVEKIT_API_SECRET: LiveKit API secret

        Optional environment variables for voice pipeline:
        - DEEPGRAM_API_KEY: Deepgram STT API key
        - CARTESIA_API_KEY: Cartesia TTS API key
        - Other voice configuration variables

        Returns:
            Config: Configuration instance loaded from environment

        Raises:
            ValueError: If required environment variables are missing
        """
        # Load required LiveKit configuration
        livekit_url = os.getenv("LIVEKIT_URL")
        livekit_api_key = os.getenv("LIVEKIT_API_KEY")
        livekit_api_secret = os.getenv("LIVEKIT_API_SECRET")

        if not livekit_url:
            raise ValueError("Missing required environment variable: LIVEKIT_URL")
        if not livekit_api_key:
            raise ValueError("Missing required environment variable: LIVEKIT_API_KEY")
        if not livekit_api_secret:
            raise ValueError("Missing required environment variable: LIVEKIT_API_SECRET")

        # Load optional LiveKit configuration
        health_check_port = int(os.getenv("HEALTH_CHECK_PORT", "8080"))
        log_level = os.getenv("LOG_LEVEL", "INFO")
        log_format = os.getenv("LOG_FORMAT", "json")
        test_room = os.getenv("LIVEKIT_TEST_ROOM")

        # Load voice configuration if available
        voice_config = None
        deepgram_api_key = os.getenv("DEEPGRAM_API_KEY")

        if deepgram_api_key:
            voice_config = VoiceConfig(
                deepgram_api_key=deepgram_api_key,
                deepgram_model=os.getenv("DEEPGRAM_MODEL", "nova-2"),
                deepgram_language=os.getenv("DEEPGRAM_LANGUAGE", "en-US"),
                cartesia_api_key=os.getenv("CARTESIA_API_KEY", ""),
                cartesia_voice_id=os.getenv("CARTESIA_VOICE_ID", "default-sonic-voice"),
                cartesia_speed=float(os.getenv("CARTESIA_SPEED", "1.0")),
                cartesia_emotion=os.getenv("CARTESIA_EMOTION", "neutral"),
                sample_rate=int(os.getenv("VOICE_SAMPLE_RATE", "16000")),
                channels=int(os.getenv("VOICE_CHANNELS", "1")),
                latency_target_ms=int(os.getenv("VOICE_LATENCY_TARGET", "500")),
                vad_threshold=float(os.getenv("VAD_THRESHOLD", "0.5")),
            )

        # Load conversation configuration if available
        conversation_config = None
        llm_api_key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")

        if llm_api_key:
            llm_provider = os.getenv("LLM_PROVIDER", "openai")

            conversation_config = ConversationConfig(
                llm_provider=llm_provider,
                llm_api_key=llm_api_key,
                llm_model=os.getenv(
                    "LLM_MODEL",
                    "gpt-4" if llm_provider == "openai"
                    else "claude-3-sonnet-20240229"
                ),
                llm_temperature=float(os.getenv("LLM_TEMPERATURE", "0.7")),
                llm_max_tokens=int(os.getenv("LLM_MAX_TOKENS", "150")),
                max_history=int(os.getenv("CONVERSATION_MAX_HISTORY", "20")),
                vad_threshold=float(os.getenv("VAD_THRESHOLD", "0.5")),
                min_speech_duration_ms=int(
                    os.getenv("MIN_SPEECH_DURATION_MS", "300")
                ),
                silence_duration_ms=int(
                    os.getenv("SILENCE_DURATION_MS", "700")
                ),
                idle_timeout_seconds=int(
                    os.getenv("IDLE_TIMEOUT_SECONDS", "120")
                ),
                enable_interruptions=os.getenv(
                    "ENABLE_INTERRUPTIONS", "true"
                ).lower() == "true",
                fallback_response=os.getenv(
                    "FALLBACK_RESPONSE",
                    "I'm having trouble right now. Please try again."
                ),
            )

        return cls(
            livekit_url=livekit_url,
            livekit_api_key=livekit_api_key,
            livekit_api_secret=livekit_api_secret,
            health_check_port=health_check_port,
            log_level=log_level,
            log_format=log_format,
            test_room=test_room,
            voice=voice_config,
            conversation=conversation_config,
        )


def setup_logging(config: Config) -> None:
    """Configure structured logging using structlog.

    Args:
        config: Configuration instance with logging settings
    """
    log_level = getattr(logging, config.log_level.upper(), logging.INFO)

    if config.log_format == "json":
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.processors.JSONRenderer(),
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )
    else:
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.dev.ConsoleRenderer(),
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Clear existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Add console handler
    handler = logging.StreamHandler()
    handler.setLevel(log_level)
    root_logger.addHandler(handler)
