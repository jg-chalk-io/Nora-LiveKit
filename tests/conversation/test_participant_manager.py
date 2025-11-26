"""Tests for ParticipantManager (multi-user support).

Tests cover REQ-F-PART-001 through REQ-F-PART-005.
"""

import pytest
from datetime import datetime, timezone
from nora_livekit.conversation.context import ConversationContext
from nora_livekit.conversation.participant_manager import (
    ParticipantManager,
    ParticipantActivity,
)


class TestParticipantActivity:
    """Test ParticipantActivity dataclass."""

    def test_participant_activity_creation(self) -> None:
        """Test creating ParticipantActivity."""
        now = datetime.now(timezone.utc)
        activity = ParticipantActivity(
            participant_id="user-123",
            join_time=now,
            leave_time=None,
            last_activity=now,
            message_count=5,
            is_active=True,
        )
        assert activity.participant_id == "user-123"
        assert activity.is_active is True
        assert activity.message_count == 5


class TestParticipantManagerInitialization:
    """Test ParticipantManager initialization."""

    def test_initialization(self) -> None:
        """Test initializing ParticipantManager."""
        ctx = ConversationContext()
        manager = ParticipantManager(ctx)
        assert manager.context == ctx


class TestParticipantJoin:
    """Test REQ-F-PART-001: Participant Join Tracking."""

    def test_add_participant(self) -> None:
        """Test adding a participant."""
        ctx = ConversationContext()
        manager = ParticipantManager(ctx)

        manager.add_participant("user-123", "Alice")

        activity = manager.get_participant_stats("user-123")
        assert activity is not None
        assert activity.participant_id == "user-123"
        assert activity.is_active is True

    def test_add_participant_without_name(self) -> None:
        """Test adding participant without name."""
        ctx = ConversationContext()
        manager = ParticipantManager(ctx)

        manager.add_participant("user-456")

        activity = manager.get_participant_stats("user-456")
        assert activity is not None
        assert activity.is_active is True


class TestParticipantLeave:
    """Test REQ-F-PART-002: Participant Leave Tracking."""

    def test_remove_participant(self) -> None:
        """Test removing a participant."""
        ctx = ConversationContext()
        manager = ParticipantManager(ctx)

        manager.add_participant("user-123", "Alice")
        manager.remove_participant("user-123")

        activity = manager.get_participant_stats("user-123")
        assert activity is not None
        assert activity.is_active is False
        assert activity.leave_time is not None


class TestActivityTracking:
    """Test REQ-F-PART-003: Activity Timestamp Updates."""

    def test_update_activity(self) -> None:
        """Test updating participant activity."""
        ctx = ConversationContext()
        manager = ParticipantManager(ctx)

        manager.add_participant("user-123", "Alice")
        before = datetime.now(timezone.utc)
        manager.update_activity("user-123")
        after = datetime.now(timezone.utc)

        activity = manager.get_participant_stats("user-123")
        assert activity is not None
        assert before <= activity.last_activity <= after


class TestActiveParticipantsQuery:
    """Test REQ-F-PART-004: Active Participants Query."""

    def test_get_active_participants(self) -> None:
        """Test getting active participants."""
        ctx = ConversationContext()
        manager = ParticipantManager(ctx)

        manager.add_participant("user-123", "Alice")
        manager.add_participant("user-456", "Bob")

        active = manager.get_active_participants()
        assert len(active) == 2
        assert active[0].participant_id in ["user-123", "user-456"]

    def test_get_active_participants_excludes_inactive(self) -> None:
        """Test that inactive participants are excluded."""
        ctx = ConversationContext()
        manager = ParticipantManager(ctx)

        manager.add_participant("user-123", "Alice")
        manager.add_participant("user-456", "Bob")
        manager.remove_participant("user-456")

        active = manager.get_active_participants()
        assert len(active) == 1
        assert active[0].participant_id == "user-123"

    def test_get_active_participants_ordered_by_join_time(self) -> None:
        """Test that active participants are ordered by join time."""
        ctx = ConversationContext()
        manager = ParticipantManager(ctx)

        manager.add_participant("user-123", "Alice")
        manager.add_participant("user-456", "Bob")
        manager.add_participant("user-789", "Charlie")

        active = manager.get_active_participants()
        assert len(active) == 3
        # Should be in join order
        assert active[0].participant_id == "user-123"
        assert active[1].participant_id == "user-456"
        assert active[2].participant_id == "user-789"


class TestParticipantStatistics:
    """Test REQ-F-PART-005: Participant Statistics."""

    def test_get_participant_stats(self) -> None:
        """Test getting participant statistics."""
        ctx = ConversationContext()
        manager = ParticipantManager(ctx)

        manager.add_participant("user-123", "Alice")
        manager.update_activity("user-123")

        stats = manager.get_participant_stats("user-123")
        assert stats is not None
        assert stats.participant_id == "user-123"
        assert stats.is_active is True

    def test_get_stats_nonexistent_participant(self) -> None:
        """Test getting stats for nonexistent participant."""
        ctx = ConversationContext()
        manager = ParticipantManager(ctx)

        stats = manager.get_participant_stats("nonexistent")
        assert stats is None
