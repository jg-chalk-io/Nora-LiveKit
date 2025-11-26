"""Participant tracking for multi-user conversations.

Manages participant join/leave events, activity tracking, and statistics.

Satisfies REQ-F-PART-001 through REQ-F-PART-005.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import structlog

from nora_livekit.conversation.context import ConversationContext

logger = structlog.get_logger(__name__)


@dataclass
class ParticipantActivity:
    """Tracks participant activity in conversation."""

    participant_id: str
    join_time: datetime
    leave_time: datetime | None
    last_activity: datetime
    message_count: int
    is_active: bool


class ParticipantManager:
    """Manages multiple participants in conversation room.

    Satisfies: REQ-F-PART-001, REQ-F-PART-002, REQ-F-PART-003,
               REQ-F-PART-004, REQ-F-PART-005
    """

    def __init__(self, context: ConversationContext) -> None:
        """Initialize participant manager with conversation context.

        Args:
            context: ConversationContext instance
        """
        self.context = context
        self._participants: dict[str, ParticipantActivity] = {}

    def add_participant(
        self,
        participant_id: str,
        name: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Add new participant to conversation.

        Satisfies: REQ-F-PART-001

        Args:
            participant_id: Unique participant identifier
            name: Human-readable participant name (optional)
            metadata: Additional participant metadata (optional)
        """
        now = datetime.now(timezone.utc)
        self._participants[participant_id] = ParticipantActivity(
            participant_id=participant_id,
            join_time=now,
            leave_time=None,
            last_activity=now,
            message_count=0,
            is_active=True,
        )

        # Also add to conversation context
        self.context.add_participant(participant_id, name)

        logger.info("participant_joined", participant_id=participant_id, name=name)

    def remove_participant(self, participant_id: str) -> None:
        """Mark participant as inactive (left conversation).

        Satisfies: REQ-F-PART-002

        Args:
            participant_id: Unique participant identifier
        """
        if participant_id in self._participants:
            self._participants[participant_id].is_active = False
            self._participants[participant_id].leave_time = datetime.now(timezone.utc)

            logger.info("participant_left", participant_id=participant_id)

    def update_activity(self, participant_id: str) -> None:
        """Update participant's last activity timestamp.

        Satisfies: REQ-F-PART-003

        Args:
            participant_id: Unique participant identifier
        """
        if participant_id in self._participants:
            self._participants[participant_id].last_activity = datetime.now(
                timezone.utc
            )
            self._participants[participant_id].message_count += 1

    def get_active_participants(self) -> list[ParticipantActivity]:
        """Get list of currently active participants.

        Satisfies: REQ-F-PART-004

        Returns:
            List of active ParticipantActivity sorted by join_time
        """
        active = [
            p for p in self._participants.values() if p.is_active
        ]
        # Sort by join_time
        return sorted(active, key=lambda p: p.join_time)

    def get_participant_stats(
        self,
        participant_id: str,
    ) -> ParticipantActivity | None:
        """Get activity statistics for specific participant.

        Satisfies: REQ-F-PART-005

        Args:
            participant_id: Unique participant identifier

        Returns:
            ParticipantActivity or None if not found
        """
        return self._participants.get(participant_id)
