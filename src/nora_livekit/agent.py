"""Nora LiveKit Agent - Foundation agent with voice pipeline support (SPEC-LIVEKIT-001 & SPEC-LIVEKIT-002)."""

import asyncio
import structlog
from typing import Optional

from nora_livekit.config import Config

logger = structlog.get_logger(__name__)


class NoraAgent:
    """Foundation agent for Nora LiveKit integration with voice pipeline support."""

    def __init__(self, config: Config) -> None:
        """Initialize Nora agent with configuration.

        Args:
            config: Configuration instance
        """
        self.config = config
        self.room = None
        self._shutdown_event = asyncio.Event()
        self._running = False

    async def start(self) -> None:
        """Start the agent and join the LiveKit room.

        This is the main entry point for agent initialization.
        """
        logger.info("agent.starting", url=self.config.livekit_url)
        self._running = True
        logger.info("agent.started")

    async def stop(self) -> None:
        """Stop the agent and cleanup resources."""
        logger.info("agent.stopping")
        self._running = False
        self._shutdown_event.set()
        logger.info("agent.stopped")

    @property
    def is_running(self) -> bool:
        """Check if agent is running."""
        return self._running
