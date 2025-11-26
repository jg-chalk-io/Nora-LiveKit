"""Tests for Nora state management."""

import pytest

from nora_livekit.nora.state import NoraState, NoraFlow


class TestNoraState:
    """Tests for NoraState Pydantic model."""

    def test_default_values(self):
        """Test default state values."""
        state = NoraState()

        assert state.is_the_clinic_open is False
        assert state.caller_phone == ""
        assert state.callback_number is None
        assert state.first_name is None
        assert state.last_name is None
        assert state.pet_name is None
        assert state.flow == NoraFlow.GREETING
        assert state.silence_checks == 0
        assert state.debug_mode is False

    def test_initialization_with_values(self):
        """Test state initialization with custom values."""
        state = NoraState(
            is_the_clinic_open=True,
            caller_phone="4165550198",
            first_name="John",
            pet_name="Max",
            flow=NoraFlow.TRIAGE,
        )

        assert state.is_the_clinic_open is True
        assert state.caller_phone == "4165550198"
        assert state.first_name == "John"
        assert state.pet_name == "Max"
        assert state.flow == NoraFlow.TRIAGE

    def test_reset_silence_tracking(self):
        """Test reset_silence_tracking method."""
        state = NoraState(
            last_question="What's your name?",
            silence_checks=2,
        )

        state.reset_silence_tracking()

        assert state.last_question is None
        assert state.silence_checks == 0

    def test_set_question(self):
        """Test set_question method."""
        state = NoraState(silence_checks=3)

        state.set_question("What's your first name?")

        assert state.last_question == "What's your first name?"
        assert state.silence_checks == 0

    def test_increment_silence_check(self):
        """Test increment_silence_check method."""
        state = NoraState()

        result = state.increment_silence_check()
        assert result == 1
        assert state.silence_checks == 1

        result = state.increment_silence_check()
        assert result == 2
        assert state.silence_checks == 2

    def test_has_minimum_transfer_data(self):
        """Test has_minimum_transfer_data method."""
        state = NoraState()
        assert state.has_minimum_transfer_data() is False

        state.callback_number = "4165550198"
        assert state.has_minimum_transfer_data() is False

        state.first_name = "John"
        assert state.has_minimum_transfer_data() is True

    def test_has_full_transfer_data(self):
        """Test has_full_transfer_data method."""
        state = NoraState()
        assert state.has_full_transfer_data() is False

        state.callback_number = "4165550198"
        state.first_name = "John"
        state.pet_name = "Max"
        assert state.has_full_transfer_data() is False

        state.urgency_reason = "Hit by car"
        assert state.has_full_transfer_data() is True

    def test_has_message_data(self):
        """Test has_message_data method."""
        state = NoraState()
        assert state.has_message_data() is False

        state.callback_number = "4165550198"
        state.first_name = "John"
        assert state.has_message_data() is False

        state.concern_description = "Prescription refill for heartworm medication"
        assert state.has_message_data() is True

    def test_to_prompt_context(self):
        """Test to_prompt_context serialization."""
        state = NoraState(
            is_the_clinic_open=True,
            first_name="John",
            pet_name="Max",
            flow=NoraFlow.MESSAGE,
        )

        context = state.to_prompt_context()

        assert "is_the_clinic_open" in context
        assert "true" in context.lower()
        assert "John" in context
        assert "Max" in context
        assert "message" in context.lower()

        # Should not include None values
        assert "last_name" not in context or "null" not in context


class TestNoraFlow:
    """Tests for NoraFlow enum."""

    def test_flow_values(self):
        """Test all flow enum values."""
        assert NoraFlow.GREETING == "greeting"
        assert NoraFlow.TRIAGE == "triage"
        assert NoraFlow.URGENT == "urgent"
        assert NoraFlow.MESSAGE == "message"
        assert NoraFlow.CRITICAL == "critical"
        assert NoraFlow.CLOSING == "closing"

    def test_flow_assignment(self):
        """Test flow assignment in state."""
        state = NoraState()

        state.flow = NoraFlow.TRIAGE
        assert state.flow == NoraFlow.TRIAGE

        state.flow = NoraFlow.CRITICAL
        assert state.flow == NoraFlow.CRITICAL
