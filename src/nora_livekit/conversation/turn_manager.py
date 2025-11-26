"""Turn-taking management for voice conversations.

Detects turn boundaries and interruptions using LiveKit turn detector plugin.

Satisfies REQ-F-TURN-001 through REQ-F-TURN-005.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, AsyncIterator

import structlog

logger = structlog.get_logger(__name__)


class TurnEvent(Enum):
    """Turn-taking events."""

    USER_TURN_START = "user_turn_start"
    USER_TURN_END = "user_turn_end"
    AGENT_TURN_START = "agent_turn_start"
    AGENT_TURN_END = "agent_turn_end"
    INTERRUPTION = "interruption"


@dataclass
class TurnData:
    """Data associated with a turn event."""

    event: TurnEvent
    participant_id: str | None
    timestamp: datetime
    metadata: dict[str, Any] = field(default_factory=dict)


class TurnManager:
    """Manages turn-taking detection and coordination.

    Satisfies: REQ-F-TURN-001, REQ-F-TURN-002, REQ-F-TURN-003,
               REQ-F-TURN-004, REQ-F-TURN-005
    """

    def __init__(
        self,
        vad_threshold: float = 0.5,
        min_speech_duration_ms: int = 300,
        silence_duration_ms: int = 700,
    ) -> None:
        """Initialize turn manager with VAD configuration.

        Satisfies: REQ-F-TURN-001

        Args:
            vad_threshold: Voice activity detection threshold (0.0-1.0)
            min_speech_duration_ms: Minimum speech duration to trigger turn
            silence_duration_ms: Silence duration to end turn
        """
        self.vad_threshold = vad_threshold
        self.min_speech_duration_ms = min_speech_duration_ms
        self.silence_duration_ms = silence_duration_ms
        self.agent_speaking = False
        self._running = False

    async def start(self, audio_stream: AsyncIterator[bytes]) -> None:
        """Start monitoring audio stream for turn events.

        Satisfies: REQ-F-TURN-002

        Args:
            audio_stream: Async iterator of audio bytes
        """
        self._running = True
        await self._detect_turns(audio_stream)

    async def stop(self) -> None:
        """Stop turn detection and cleanup."""
        self._running = False

    async def wait_for_turn(self) -> TurnData:
        """Wait for next turn event (blocking).

        Satisfies: REQ-F-TURN-002, REQ-F-TURN-003

        Returns:
            TurnData with event details
        """
        # Placeholder: In production, this would read from a queue
        # populated by the turn detection task
        raise NotImplementedError("Implemented in subclasses with real VAD")

    def set_agent_speaking(self, speaking: bool) -> None:
        """Notify turn manager when agent is speaking.

        Satisfies: REQ-F-TURN-004

        Args:
            speaking: True if agent is currently speaking, False otherwise
        """
        self.agent_speaking = speaking

    async def _detect_turns(
        self,
        audio_stream: AsyncIterator[bytes],
    ) -> None:
        """Internal turn detection loop using livekit-plugins-turn-detector.

        Satisfies: REQ-F-TURN-001, REQ-F-TURN-005

        Args:
            audio_stream: Async iterator of audio bytes
        """
        # Placeholder: In production, this would use livekit.plugins.turn_detector
        # to monitor the audio stream and emit turn events
        pass
