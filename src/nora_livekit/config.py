"""Configuration loader for Nora LiveKit Agent."""

import logging
import os
from dataclasses import dataclass

import structlog


@dataclass
class Config:
    """Configuration for Nora LiveKit Agent.

    Attributes:
        livekit_url: WebSocket URL to LiveKit server (e.g., wss://your-instance.livekit.cloud)
        livekit_api_key: LiveKit API key for authentication
        livekit_api_secret: LiveKit API secret for token generation
        health_check_port: Port for FastAPI health check endpoint (default: 8080)
        log_level: Logging level (default: INFO)
        log_format: Log output format, "json" for structured logs (default: json)
        test_room: Optional test room name for development (default: None)
    """

    livekit_url: str
    livekit_api_key: str
    livekit_api_secret: str
    health_check_port: int = 8080
    log_level: str = "INFO"
    log_format: str = "json"
    test_room: str | None = None

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables.

        Required environment variables:
            - LIVEKIT_URL: WebSocket URL to LiveKit server
            - LIVEKIT_API_KEY: LiveKit API key
            - LIVEKIT_API_SECRET: LiveKit API secret

        Optional environment variables:
            - HEALTH_CHECK_PORT: Health check port (default: 8080)
            - LOG_LEVEL: Logging level (default: INFO)
            - LOG_FORMAT: Log output format (default: json)
            - LIVEKIT_TEST_ROOM: Test room name for development

        Returns:
            Config instance loaded from environment variables

        Raises:
            ValueError: If required environment variables are missing or invalid
        """
        # Load required variables
        url = os.getenv("LIVEKIT_URL")
        if not url:
            raise ValueError("LIVEKIT_URL is required")

        # Validate URL scheme
        if not url.startswith(("wss://", "ws://")):
            raise ValueError("LIVEKIT_URL must start with wss:// or ws://")

        api_key = os.getenv("LIVEKIT_API_KEY")
        if not api_key:
            raise ValueError("LIVEKIT_API_KEY is required")

        api_secret = os.getenv("LIVEKIT_API_SECRET")
        if not api_secret:
            raise ValueError("LIVEKIT_API_SECRET is required")

        # Load optional variables with defaults
        try:
            health_check_port = int(os.getenv("HEALTH_CHECK_PORT", "8080"))
        except ValueError:
            raise ValueError("HEALTH_CHECK_PORT must be a valid integer")

        log_level = os.getenv("LOG_LEVEL", "INFO")
        log_format = os.getenv("LOG_FORMAT", "json")
        test_room = os.getenv("LIVEKIT_TEST_ROOM")

        return cls(
            livekit_url=url,
            livekit_api_key=api_key,
            livekit_api_secret=api_secret,
            health_check_port=health_check_port,
            log_level=log_level,
            log_format=log_format,
            test_room=test_room,
        )


def setup_logging(config: Config) -> None:
    """Configure structlog for JSON output.

    Args:
        config: Configuration instance containing log level and format settings
    """
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure standard logging
    logging.basicConfig(
        level=getattr(logging, config.log_level.upper()),
        format="%(message)s",
    )
