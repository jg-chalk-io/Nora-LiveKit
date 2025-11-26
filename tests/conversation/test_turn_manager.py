"""Tests for TurnManager (turn-taking detection).

Tests cover REQ-F-TURN-001 through REQ-F-TURN-005.
"""

import pytest
from datetime import datetime, timezone
from nora_livekit.conversation.turn_manager import (
    TurnManager,
    TurnEvent,
    TurnData,
)


class TestTurnEvent:
    """Test TurnEvent enum."""

    def test_turn_events_exist(self) -> None:
        """Test that all turn events are defined."""
        assert hasattr(TurnEvent, "USER_TURN_START")
        assert hasattr(TurnEvent, "USER_TURN_END")
        assert hasattr(TurnEvent, "AGENT_TURN_START")
        assert hasattr(TurnEvent, "AGENT_TURN_END")
        assert hasattr(TurnEvent, "INTERRUPTION")


class TestTurnData:
    """Test TurnData dataclass."""

    def test_turn_data_creation(self) -> None:
        """Test creating TurnData."""
        now = datetime.now(timezone.utc)
        turn_data = TurnData(
            event=TurnEvent.USER_TURN_END,
            participant_id="user-123",
            timestamp=now,
        )
        assert turn_data.event == TurnEvent.USER_TURN_END
        assert turn_data.participant_id == "user-123"
        assert turn_data.timestamp == now


class TestTurnManagerInitialization:
    """Test TurnManager initialization."""

    def test_default_initialization(self) -> None:
        """Test initializing TurnManager with defaults."""
        manager = TurnManager()
        assert manager.vad_threshold == 0.5
        assert manager.min_speech_duration_ms == 300
        assert manager.silence_duration_ms == 700

    def test_custom_initialization(self) -> None:
        """Test initializing TurnManager with custom values."""
        manager = TurnManager(
            vad_threshold=0.6,
            min_speech_duration_ms=200,
            silence_duration_ms=800,
        )
        assert manager.vad_threshold == 0.6
        assert manager.min_speech_duration_ms == 200
        assert manager.silence_duration_ms == 800


class TestAgentSpeakingState:
    """Test REQ-F-TURN-004: Turn suppression during agent speech."""

    def test_agent_speaking_initially_false(self) -> None:
        """Test that agent_speaking is initially False."""
        manager = TurnManager()
        assert manager.agent_speaking is False

    def test_set_agent_speaking_true(self) -> None:
        """Test setting agent_speaking to True."""
        manager = TurnManager()
        manager.set_agent_speaking(True)
        assert manager.agent_speaking is True

    def test_set_agent_speaking_false(self) -> None:
        """Test setting agent_speaking to False."""
        manager = TurnManager()
        manager.set_agent_speaking(True)
        manager.set_agent_speaking(False)
        assert manager.agent_speaking is False
