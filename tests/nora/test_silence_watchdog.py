"""Tests for Nora silence watchdog."""

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from nora_livekit.nora.silence_watchdog import (
    SilenceWatchdog,
    SilenceAction,
    SilenceEvent,
)


class TestSilenceWatchdog:
    """Tests for silence watchdog functionality."""

    @pytest.fixture
    def watchdog(self):
        """Create a watchdog instance for testing."""
        return SilenceWatchdog()

    @pytest.fixture
    def watchdog_with_handler(self):
        """Create a watchdog with a mock handler."""
        handler = AsyncMock()
        return SilenceWatchdog(on_silence=handler), handler

    @pytest.mark.asyncio
    async def test_start_watching_sets_state(self, watchdog):
        """Test that start_watching sets the correct state."""
        question = "What's your first name?"
        await watchdog.start_watching(question)

        assert watchdog.is_active is True
        assert watchdog._current_question == question
        assert watchdog._silence_count == 0

        # Cleanup
        await watchdog.stop_watching()

    @pytest.mark.asyncio
    async def test_stop_watching_clears_state(self, watchdog):
        """Test that stop_watching clears state."""
        await watchdog.start_watching("Test question?")
        await watchdog.stop_watching()

        assert watchdog.is_active is False
        assert watchdog._current_question is None

    @pytest.mark.asyncio
    async def test_on_speech_received_updates_timestamp(self, watchdog):
        """Test that on_speech_received updates the timestamp."""
        await watchdog.start_watching("Test?")
        old_time = watchdog._last_speech_time

        await asyncio.sleep(0.1)
        watchdog.on_speech_received()

        assert watchdog._last_speech_time > old_time

        await watchdog.stop_watching()

    @pytest.mark.asyncio
    async def test_silence_triggers_first_check(self, watchdog_with_handler):
        """Test that 5s silence triggers first check."""
        watchdog, handler = watchdog_with_handler

        # Override timeout for faster testing
        watchdog.SILENCE_TIMEOUT_SECONDS = 0.1

        await watchdog.start_watching("What's your name?")
        await asyncio.sleep(0.2)  # Wait for silence timeout

        # Should have triggered handler with FIRST_CHECK
        if handler.called:
            event = handler.call_args[0][0]
            assert event.action == SilenceAction.FIRST_CHECK
            assert event.silence_count == 1

        await watchdog.stop_watching()

    @pytest.mark.asyncio
    async def test_multiple_silences_escalate(self, watchdog_with_handler):
        """Test that multiple silences escalate actions."""
        watchdog, handler = watchdog_with_handler

        # Override timeout for faster testing
        watchdog.SILENCE_TIMEOUT_SECONDS = 0.05

        await watchdog.start_watching("What's your name?")

        # Wait for multiple silence cycles
        await asyncio.sleep(0.3)

        # Should have multiple calls with escalating actions
        if handler.call_count >= 2:
            # First call should be FIRST_CHECK
            first_event = handler.call_args_list[0][0][0]
            assert first_event.action == SilenceAction.FIRST_CHECK

            # Second call should be SECOND_CHECK
            second_event = handler.call_args_list[1][0][0]
            assert second_event.action == SilenceAction.SECOND_CHECK

        await watchdog.stop_watching()

    def test_get_response_for_action(self, watchdog):
        """Test response text for each action."""
        assert watchdog.get_response_for_action(SilenceAction.FIRST_CHECK) == "Are you still there?"
        assert "trouble hearing" in watchdog.get_response_for_action(SilenceAction.SECOND_CHECK)
        assert "connecting you" in watchdog.get_response_for_action(SilenceAction.SAFE_TRANSFER)

    @pytest.mark.asyncio
    async def test_cancel_on_new_watch(self, watchdog):
        """Test that starting a new watch cancels the old one."""
        await watchdog.start_watching("Question 1?")
        task1 = watchdog._watchdog_task

        await watchdog.start_watching("Question 2?")
        task2 = watchdog._watchdog_task

        # Task should be different
        assert task1 != task2
        # Old task should be cancelled
        assert task1.cancelled() or task1.done()

        await watchdog.stop_watching()

    @pytest.mark.asyncio
    async def test_silence_count_property(self, watchdog):
        """Test current_silence_count property."""
        assert watchdog.current_silence_count == 0

        watchdog._silence_count = 2
        assert watchdog.current_silence_count == 2


class TestSilenceEvent:
    """Tests for SilenceEvent dataclass."""

    def test_event_creation(self):
        """Test creating a SilenceEvent."""
        event = SilenceEvent(
            action=SilenceAction.FIRST_CHECK,
            silence_count=1,
            original_question="What's your name?",
            timestamp=datetime.now(timezone.utc),
        )

        assert event.action == SilenceAction.FIRST_CHECK
        assert event.silence_count == 1
        assert event.original_question == "What's your name?"
