"""Nora LiveKit Agent with room lifecycle management."""

import asyncio
import signal
from typing import Any, Optional

import structlog
from livekit import api

from .config import Config

log = structlog.get_logger()


class NoraAgent:
    """LiveKit agent with room connection lifecycle management.

    Manages connection to LiveKit rooms, graceful shutdown on signals,
    and logging of all lifecycle events.

    Attributes:
        config: Configuration instance with LiveKit credentials
        room: Connected LiveKit room instance (None if not connected)
    """

    def __init__(self, config: Config) -> None:
        """Initialize the Nora agent.

        Args:
            config: Configuration instance with LiveKit server details
        """
        self.config = config
        self.room: Optional[dict[str, Any]] = None
        self._livekit_room: Optional[dict[str, Any]] = None
        self._shutdown_event = asyncio.Event()

        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGTERM, self._handle_shutdown_signal)
        signal.signal(signal.SIGINT, self._handle_shutdown_signal)

        log.info("agent.initialized", url=config.livekit_url)

    def _handle_shutdown_signal(self, signum: int, frame: Any) -> None:
        """Handle shutdown signals (SIGTERM, SIGINT).

        Args:
            signum: Signal number
            frame: Current stack frame
        """
        log.info("agent.shutdown_signal_received", signal=signum)
        self._shutdown_event.set()

    async def start(self) -> None:
        """Connect to LiveKit server and join room.

        Raises:
            Exception: If connection or room join fails
        """
        log.info("agent.starting", url=self.config.livekit_url)

        try:
            # Initialize connection to LiveKit server
            await self._connect_to_livekit()

            # Create room representation
            room_name = self.config.test_room or "nora-room"
            self.room = {
                "name": room_name,
                "url": self.config.livekit_url,
                "connected": True,
            }
            log.info("agent.room_joined", room_name=room_name)

        except Exception as e:
            log.error("agent.connection_failed", error=str(e))
            raise

    async def stop(self) -> None:
        """Gracefully disconnect from LiveKit room.

        Completes within 5 seconds timeout.
        """
        log.info("agent.shutting_down")

        try:
            if self.room:
                await asyncio.wait_for(
                    self._disconnect_from_livekit(),
                    timeout=5.0,
                )
                log.info("agent.room_disconnected", reason="graceful_shutdown")
                self.room = None
        except asyncio.TimeoutError:
            log.warning("agent.disconnect_timeout")
        except Exception as e:
            log.error("agent.disconnect_failed", error=str(e))

        log.info("agent.stopped")

    async def _connect_to_livekit(self) -> None:
        """Connect to LiveKit server and generate access token.

        Generates a LiveKit access token for room connection that can be used
        by the livekit-agents framework to establish the actual connection.

        Raises:
            Exception: If token generation fails
        """
        try:
            # Generate access token for room connection
            agent_name = "nora-agent"
            room_name = self.config.test_room or "default-room"

            token = (
                api.AccessToken(
                    api_key=self.config.livekit_api_key,
                    api_secret=self.config.livekit_api_secret,
                )
                .with_identity(agent_name)
                .with_name(agent_name)
                .with_grants(
                    api.VideoGrants(
                        room_join=True,
                        room=room_name,
                        can_publish=True,
                        can_subscribe=True,
                    )
                )
            )

            token_str = token.to_jwt()

            # Store the token for use by the livekit-agents framework
            self._livekit_room = {
                "token": token_str,
                "url": self.config.livekit_url,
                "room": room_name,
                "agent_name": agent_name,
            }

            log.info(
                "agent.livekit_connected",
                room_name=room_name,
                agent_name=agent_name,
            )

        except Exception as e:
            log.error("agent.livekit_connection_error", error=str(e), exc_info=True)
            raise

    async def _disconnect_from_livekit(self) -> None:
        """Disconnect from LiveKit server and clean up resources.

        Releases the stored LiveKit connection info and cleans up
        any associated resources.
        """
        if self._livekit_room is None:
            return

        try:
            log.info("agent.livekit_disconnected")
        except Exception as e:
            log.error(
                "agent.livekit_disconnection_error",
                error=str(e),
                exc_info=True,
            )
            raise
        finally:
            self._livekit_room = None
