"""Tests for ConversationContext data model and message management.

Tests cover REQ-F-CTX-001 through REQ-F-CTX-005.
"""

import pytest
from datetime import datetime, timezone
from nora_livekit.conversation.context import (
    ConversationContext,
    ConversationPhase,
    Message,
    ParticipantMetadata,
)


class TestMessage:
    """Test Message dataclass."""

    def test_message_creation(self) -> None:
        """Test creating a message with required fields."""
        msg = Message(
            role="user",
            content="Hello",
            timestamp=datetime.now(timezone.utc),
        )
        assert msg.role == "user"
        assert msg.content == "Hello"
        assert msg.participant_id is None
        assert msg.metadata == {}

    def test_message_with_participant(self) -> None:
        """Test creating a message with participant info."""
        now = datetime.now(timezone.utc)
        msg = Message(
            role="assistant",
            content="Hi there",
            timestamp=now,
            participant_id="user-123",
            metadata={"latency_ms": 250},
        )
        assert msg.participant_id == "user-123"
        assert msg.metadata["latency_ms"] == 250


class TestParticipantMetadata:
    """Test ParticipantMetadata dataclass."""

    def test_participant_creation(self) -> None:
        """Test creating participant metadata."""
        now = datetime.now(timezone.utc)
        participant = ParticipantMetadata(
            participant_id="user-123",
            name="Alice",
            join_time=now,
        )
        assert participant.participant_id == "user-123"
        assert participant.name == "Alice"
        assert participant.join_time == now
        assert participant.preferences == {}

    def test_participant_with_preferences(self) -> None:
        """Test participant with preferences."""
        now = datetime.now(timezone.utc)
        participant = ParticipantMetadata(
            participant_id="user-123",
            name="Bob",
            join_time=now,
            preferences={"language": "en", "voice_speed": 1.2},
        )
        assert participant.preferences["language"] == "en"
        assert participant.preferences["voice_speed"] == 1.2


class TestConversationPhase:
    """Test ConversationPhase enum."""

    def test_phase_values(self) -> None:
        """Test that all phases exist and have correct values."""
        assert ConversationPhase.GREETING.value == "greeting"
        assert ConversationPhase.ACTIVE.value == "active"
        assert ConversationPhase.CLOSING.value == "closing"


class TestConversationContextInitialization:
    """Test ConversationContext initialization."""

    def test_context_creation_default(self) -> None:
        """Test creating context with default max_history."""
        ctx = ConversationContext()
        assert ctx.max_history == 20
        assert ctx.phase == ConversationPhase.GREETING
        assert ctx.get_history() == []
        assert ctx.session_id is not None

    def test_context_creation_custom_max_history(self) -> None:
        """Test creating context with custom max_history."""
        ctx = ConversationContext(max_history=50)
        assert ctx.max_history == 50


class TestMessageManagement:
    """Test REQ-F-CTX-001: Message History."""

    def test_add_user_message(self) -> None:
        """Test adding a user message."""
        ctx = ConversationContext()
        ctx.add_message("user", "Hello")

        history = ctx.get_history()
        assert len(history) == 1
        assert history[0].role == "user"
        assert history[0].content == "Hello"

    def test_add_assistant_message(self) -> None:
        """Test adding an assistant message."""
        ctx = ConversationContext()
        ctx.add_message("assistant", "Hi there")

        history = ctx.get_history()
        assert len(history) == 1
        assert history[0].role == "assistant"
        assert history[0].content == "Hi there"

    def test_add_multiple_messages(self) -> None:
        """Test adding multiple messages in sequence."""
        ctx = ConversationContext()
        ctx.add_message("user", "Hello")
        ctx.add_message("assistant", "Hi")
        ctx.add_message("user", "How are you?")

        history = ctx.get_history()
        assert len(history) == 3
        assert history[0].content == "Hello"
        assert history[1].content == "Hi"
        assert history[2].content == "How are you?"

    def test_message_has_timestamp(self) -> None:
        """Test that messages have timestamps."""
        ctx = ConversationContext()
        before = datetime.now(timezone.utc)
        ctx.add_message("user", "Test")
        after = datetime.now(timezone.utc)

        history = ctx.get_history()
        assert before <= history[0].timestamp <= after

    def test_add_message_with_participant_id(self) -> None:
        """Test adding message with participant_id."""
        ctx = ConversationContext()
        ctx.add_message("user", "Hello", participant_id="user-123")

        history = ctx.get_history()
        assert history[0].participant_id == "user-123"


class TestHistoryLimit:
    """Test REQ-F-CTX-002: History Limit Enforcement."""

    def test_history_not_pruned_below_limit(self) -> None:
        """Test that history is not pruned when below max_history."""
        ctx = ConversationContext(max_history=20)
        for i in range(15):
            ctx.add_message("user", f"Message {i}")

        assert len(ctx.get_history()) == 15

    def test_history_pruned_above_limit(self) -> None:
        """Test that oldest messages are pruned when exceeding max_history."""
        ctx = ConversationContext(max_history=5)
        for i in range(10):
            ctx.add_message("user", f"Message {i}")

        history = ctx.get_history()
        assert len(history) == 5
        # Oldest messages (0-4) should be removed, newest (5-9) should remain
        assert history[0].content == "Message 5"
        assert history[-1].content == "Message 9"

    def test_history_limit_is_enforced(self) -> None:
        """Test that history limit is strictly enforced."""
        ctx = ConversationContext(max_history=3)
        for i in range(100):
            ctx.add_message("user", f"Message {i}")
            assert len(ctx.get_history()) <= 3

    def test_clear_history(self) -> None:
        """Test clearing conversation history."""
        ctx = ConversationContext()
        ctx.add_message("user", "Message 1")
        ctx.add_message("user", "Message 2")
        assert len(ctx.get_history()) == 2

        ctx.clear_history()
        assert len(ctx.get_history()) == 0


class TestGetHistory:
    """Test get_history with optional limit."""

    def test_get_history_default(self) -> None:
        """Test getting full history."""
        ctx = ConversationContext()
        for i in range(5):
            ctx.add_message("user", f"Message {i}")

        history = ctx.get_history()
        assert len(history) == 5

    def test_get_history_with_limit(self) -> None:
        """Test getting history with custom limit."""
        ctx = ConversationContext()
        for i in range(10):
            ctx.add_message("user", f"Message {i}")

        history = ctx.get_history(limit=3)
        assert len(history) == 3
        # Should return most recent 3
        assert history[0].content == "Message 7"
        assert history[1].content == "Message 8"
        assert history[2].content == "Message 9"

    def test_get_history_limit_larger_than_history(self) -> None:
        """Test getting history when limit is larger than actual history."""
        ctx = ConversationContext()
        for i in range(3):
            ctx.add_message("user", f"Message {i}")

        history = ctx.get_history(limit=100)
        assert len(history) == 3


class TestParticipantManagement:
    """Test REQ-F-CTX-003: Participant Metadata Management."""

    def test_add_participant(self) -> None:
        """Test adding a participant."""
        ctx = ConversationContext()
        ctx.add_participant("user-123", "Alice")

        participant = ctx.get_participant("user-123")
        assert participant is not None
        assert participant.participant_id == "user-123"
        assert participant.name == "Alice"

    def test_add_participant_without_name(self) -> None:
        """Test adding participant without a name."""
        ctx = ConversationContext()
        ctx.add_participant("user-456")

        participant = ctx.get_participant("user-456")
        assert participant is not None
        assert participant.participant_id == "user-456"
        assert participant.name is None

    def test_get_nonexistent_participant(self) -> None:
        """Test getting a participant that doesn't exist."""
        ctx = ConversationContext()
        assert ctx.get_participant("nonexistent") is None

    def test_add_participant_creates_metadata(self) -> None:
        """Test that add_participant creates metadata with join_time."""
        ctx = ConversationContext()
        before = datetime.now(timezone.utc)
        ctx.add_participant("user-123", "Bob")
        after = datetime.now(timezone.utc)

        participant = ctx.get_participant("user-123")
        assert participant is not None
        assert before <= participant.join_time <= after


class TestPhaseTransitions:
    """Test REQ-F-CTX-004: Conversation Phase Tracking."""

    def test_initial_phase_is_greeting(self) -> None:
        """Test that initial phase is GREETING."""
        ctx = ConversationContext()
        assert ctx.phase == ConversationPhase.GREETING

    def test_transition_to_active(self) -> None:
        """Test transitioning from GREETING to ACTIVE."""
        ctx = ConversationContext()
        ctx.set_phase(ConversationPhase.ACTIVE)
        assert ctx.phase == ConversationPhase.ACTIVE

    def test_transition_to_closing(self) -> None:
        """Test transitioning to CLOSING phase."""
        ctx = ConversationContext()
        ctx.set_phase(ConversationPhase.ACTIVE)
        ctx.set_phase(ConversationPhase.CLOSING)
        assert ctx.phase == ConversationPhase.CLOSING

    def test_invalid_phase_transition_rejected(self) -> None:
        """Test that invalid phase transitions are rejected."""
        ctx = ConversationContext()
        # Try invalid transition: GREETING -> CLOSING (should require ACTIVE first)
        with pytest.raises(ValueError):
            ctx.set_phase(ConversationPhase.CLOSING)

    def test_valid_transitions(self) -> None:
        """Test all valid phase transitions."""
        # GREETING -> ACTIVE
        ctx = ConversationContext()
        ctx.set_phase(ConversationPhase.ACTIVE)
        assert ctx.phase == ConversationPhase.ACTIVE

        # ACTIVE -> CLOSING
        ctx.set_phase(ConversationPhase.CLOSING)
        assert ctx.phase == ConversationPhase.CLOSING


class TestLLMFormatConversion:
    """Test REQ-F-CTX-005: LLM Format Conversion."""

    def test_format_for_llm_empty(self) -> None:
        """Test formatting empty history for LLM."""
        ctx = ConversationContext()
        formatted = ctx.format_for_llm()
        assert formatted == []

    def test_format_for_llm_single_message(self) -> None:
        """Test formatting single message for LLM."""
        ctx = ConversationContext()
        ctx.add_message("user", "Hello")

        formatted = ctx.format_for_llm()
        assert len(formatted) == 1
        assert formatted[0]["role"] == "user"
        assert formatted[0]["content"] == "Hello"

    def test_format_for_llm_multiple_messages(self) -> None:
        """Test formatting multiple messages for LLM."""
        ctx = ConversationContext()
        ctx.add_message("user", "Hello")
        ctx.add_message("assistant", "Hi there")
        ctx.add_message("user", "How are you?")

        formatted = ctx.format_for_llm()
        assert len(formatted) == 3
        assert formatted[0] == {"role": "user", "content": "Hello"}
        assert formatted[1] == {"role": "assistant", "content": "Hi there"}
        assert formatted[2] == {"role": "user", "content": "How are you?"}

    def test_format_for_llm_respects_history_limit(self) -> None:
        """Test that format_for_llm respects max_history."""
        ctx = ConversationContext(max_history=3)
        for i in range(5):
            ctx.add_message("user", f"Message {i}")

        formatted = ctx.format_for_llm()
        assert len(formatted) == 3
        # Should only contain messages 2, 3, 4 (0-indexed)
        assert formatted[0]["content"] == "Message 2"
        assert formatted[1]["content"] == "Message 3"
        assert formatted[2]["content"] == "Message 4"

    def test_format_for_llm_has_correct_keys(self) -> None:
        """Test that formatted messages have role and content only."""
        ctx = ConversationContext()
        ctx.add_message("user", "Test")

        formatted = ctx.format_for_llm()
        assert set(formatted[0].keys()) == {"role", "content"}


class TestConversationContextIntegration:
    """Integration tests for ConversationContext."""

    def test_mixed_operations(self) -> None:
        """Test complex scenario with mixed operations."""
        ctx = ConversationContext(max_history=10)

        # Add participants
        ctx.add_participant("user-123", "Alice")
        ctx.add_participant("user-456", "Bob")

        # Add messages
        ctx.add_message("user", "Hello from Alice", participant_id="user-123")
        ctx.add_message("assistant", "Hello!")
        ctx.add_message("user", "Hello from Bob", participant_id="user-456")
        ctx.add_message("assistant", "Hi Bob!")

        # Verify state
        assert len(ctx.get_history()) == 4
        assert ctx.get_participant("user-123").name == "Alice"
        assert ctx.get_participant("user-456").name == "Bob"

        # Transition phase
        ctx.set_phase(ConversationPhase.ACTIVE)
        assert ctx.phase == ConversationPhase.ACTIVE

        # Format for LLM
        formatted = ctx.format_for_llm()
        assert len(formatted) == 4
        assert formatted[0]["content"] == "Hello from Alice"
