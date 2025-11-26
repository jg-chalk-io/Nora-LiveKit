"""Conversation context management for Nora LiveKit agent.

Manages in-memory conversation state including message history,
participant metadata, and conversation phase tracking.

Satisfies REQ-F-CTX-001 through REQ-F-CTX-005.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal


class ConversationPhase(Enum):
    """Conversation lifecycle phases."""

    GREETING = "greeting"
    ACTIVE = "active"
    CLOSING = "closing"


@dataclass
class Message:
    """Represents a single conversation message."""

    role: Literal["user", "assistant", "system"]
    content: str
    timestamp: datetime
    participant_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ParticipantMetadata:
    """Metadata for a conversation participant."""

    participant_id: str
    name: str | None
    join_time: datetime
    preferences: dict[str, Any] = field(default_factory=dict)


class ConversationContext:
    """Manages in-memory conversation state and history.

    Satisfies: REQ-F-CTX-001, REQ-F-CTX-002, REQ-F-CTX-003,
               REQ-F-CTX-004, REQ-F-CTX-005
    """

    def __init__(self, max_history: int = 20) -> None:
        """Initialize conversation context with history limit.

        Args:
            max_history: Maximum number of messages to retain (default: 20)
        """
        self._history: list[Message] = []
        self._participants: dict[str, ParticipantMetadata] = {}
        self._phase: ConversationPhase = ConversationPhase.GREETING
        self._max_history: int = max_history
        self._session_id: str = str(uuid.uuid4())
        self._created_at: datetime = datetime.now(timezone.utc)

    @property
    def max_history(self) -> int:
        """Get max history limit."""
        return self._max_history

    @property
    def phase(self) -> ConversationPhase:
        """Get current conversation phase."""
        return self._phase

    @property
    def session_id(self) -> str:
        """Get unique session ID."""
        return self._session_id

    def add_message(
        self,
        role: str,
        content: str,
        participant_id: str | None = None,
    ) -> None:
        """Add message to history and auto-prune if limit exceeded.

        Satisfies: REQ-F-CTX-001, REQ-F-CTX-002

        Args:
            role: Message role (user/assistant/system)
            content: Message content text
            participant_id: ID of speaking participant (optional)
        """
        message = Message(
            role=role,  # type: ignore
            content=content,
            timestamp=datetime.now(timezone.utc),
            participant_id=participant_id,
        )
        self._history.append(message)

        # Auto-prune if exceeded max_history
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history :]

    def get_history(self, limit: int | None = None) -> list[Message]:
        """Get conversation history with optional limit.

        Satisfies: REQ-F-CTX-001

        Args:
            limit: Optional limit on number of messages to return

        Returns:
            List of Message objects
        """
        if limit is None:
            return self._history.copy()

        # Return most recent 'limit' messages
        return self._history[-limit:].copy()

    def add_participant(
        self,
        participant_id: str,
        name: str | None = None,
    ) -> None:
        """Add or update participant metadata.

        Satisfies: REQ-F-CTX-003

        Args:
            participant_id: Unique participant identifier
            name: Human-readable participant name (optional)
        """
        self._participants[participant_id] = ParticipantMetadata(
            participant_id=participant_id,
            name=name,
            join_time=datetime.now(timezone.utc),
        )

    def get_participant(
        self,
        participant_id: str,
    ) -> ParticipantMetadata | None:
        """Get participant metadata by ID.

        Satisfies: REQ-F-CTX-003

        Args:
            participant_id: Unique participant identifier

        Returns:
            ParticipantMetadata or None if not found
        """
        return self._participants.get(participant_id)

    def set_phase(self, phase: ConversationPhase) -> None:
        """Update conversation phase with validation.

        Satisfies: REQ-F-CTX-004

        Valid transitions:
        - GREETING -> ACTIVE
        - ACTIVE -> CLOSING
        - Any phase can transition to itself (no-op)

        Args:
            phase: Target ConversationPhase

        Raises:
            ValueError: If transition is invalid (e.g., GREETING -> CLOSING)
        """
        # Allow transitioning to same phase (no-op)
        if phase == self._phase:
            return

        # Validate transition path
        valid_transitions = {
            ConversationPhase.GREETING: {ConversationPhase.ACTIVE},
            ConversationPhase.ACTIVE: {ConversationPhase.CLOSING},
            ConversationPhase.CLOSING: set(),  # No transitions from CLOSING
        }

        if phase not in valid_transitions[self._phase]:
            raise ValueError(
                f"Invalid phase transition: {self._phase.value} -> {phase.value}"
            )

        self._phase = phase

    def format_for_llm(self) -> list[dict[str, str]]:
        """Format conversation history for LLM API.

        Returns OpenAI/Anthropic compatible message list with
        "role" and "content" keys only.

        Satisfies: REQ-F-CTX-005

        Returns:
            List of dicts with "role" and "content" keys
        """
        return [
            {"role": msg.role, "content": msg.content}
            for msg in self._history
        ]

    def clear_history(self) -> None:
        """Clear conversation history (for testing)."""
        self._history = []
