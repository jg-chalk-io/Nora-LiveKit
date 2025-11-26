"""Silence watchdog for proactive silence detection.

Implements Core Rule #3 from nora.md: Proactive Silence Detection.
Monitors for 5-second silence after questions and triggers follow-up.

Satisfies REQ-F-NORA-SILENCE-001 through REQ-F-NORA-SILENCE-004.
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Callable, Optional, Awaitable

import structlog

logger = structlog.get_logger(__name__)


class SilenceAction(str, Enum):
    """Actions to take after silence detection."""

    FIRST_CHECK = "first_check"  # "Are you still there?"
    SECOND_CHECK = "second_check"  # "I'm having trouble hearing you..."
    SAFE_TRANSFER = "safe_transfer"  # Transfer after 3rd silence


@dataclass
class SilenceEvent:
    """Event data for silence detection."""

    action: SilenceAction
    silence_count: int
    original_question: str
    timestamp: datetime


# Type alias for silence handlers
SilenceHandler = Callable[[SilenceEvent], Awaitable[None]]


class SilenceWatchdog:
    """Monitors for silence after questions and triggers follow-up.

    Implements the proactive silence detection from nora.md:
    1. After 5s silence: "Are you still there?"
    2. After another 5s: "I'm having trouble hearing you..."
    3. After third silence: Safe transfer to Vet Wise

    Satisfies: REQ-F-NORA-SILENCE-001, REQ-F-NORA-SILENCE-002,
               REQ-F-NORA-SILENCE-003, REQ-F-NORA-SILENCE-004
    """

    # Silence thresholds
    SILENCE_TIMEOUT_SECONDS = 5.0
    MAX_SILENCE_CHECKS = 3

    # Response messages
    FIRST_CHECK_MESSAGE = "Are you still there?"
    SECOND_CHECK_MESSAGE = "I'm having trouble hearing you. Are you still there?"
    TRANSFER_MESSAGE = "To be safe, I'm connecting you to our 24/7 partner Vet Wise."

    def __init__(
        self,
        on_silence: Optional[SilenceHandler] = None,
    ) -> None:
        """Initialize silence watchdog.

        Args:
            on_silence: Async callback when silence is detected
        """
        self._on_silence = on_silence
        self._current_question: Optional[str] = None
        self._silence_count: int = 0
        self._watchdog_task: Optional[asyncio.Task] = None
        self._last_speech_time: datetime = datetime.now(timezone.utc)
        self._active: bool = False

    async def start_watching(self, question: str) -> None:
        """Start watching for silence after asking a question.

        Satisfies: REQ-F-NORA-SILENCE-001

        Args:
            question: The question that was just asked
        """
        # Cancel any existing watchdog
        await self.stop_watching()

        self._current_question = question
        self._silence_count = 0
        self._last_speech_time = datetime.now(timezone.utc)
        self._active = True

        # Start the watchdog task
        self._watchdog_task = asyncio.create_task(self._watchdog_loop())

        logger.debug(
            "nora.silence.watchdog_started",
            question=question[:50],
        )

    async def stop_watching(self) -> None:
        """Stop the silence watchdog.

        Called when user responds or conversation ends.
        """
        self._active = False
        self._current_question = None

        if self._watchdog_task and not self._watchdog_task.done():
            self._watchdog_task.cancel()
            try:
                await self._watchdog_task
            except asyncio.CancelledError:
                pass

        self._watchdog_task = None

        logger.debug("nora.silence.watchdog_stopped")

    def on_speech_received(self) -> None:
        """Signal that speech was received from user.

        Resets the silence timer but doesn't stop the watchdog.
        """
        self._last_speech_time = datetime.now(timezone.utc)
        # Don't reset silence_count here - that happens in stop_watching
        # This allows us to continue monitoring after partial responses

    async def _watchdog_loop(self) -> None:
        """Main watchdog loop that monitors for silence.

        Satisfies: REQ-F-NORA-SILENCE-002, REQ-F-NORA-SILENCE-003
        """
        while self._active and self._silence_count < self.MAX_SILENCE_CHECKS:
            try:
                # Wait for silence timeout
                await asyncio.sleep(self.SILENCE_TIMEOUT_SECONDS)

                # Check if still active (could have been stopped)
                if not self._active:
                    break

                # Check elapsed time since last speech
                elapsed = (
                    datetime.now(timezone.utc) - self._last_speech_time
                ).total_seconds()

                if elapsed >= self.SILENCE_TIMEOUT_SECONDS:
                    self._silence_count += 1
                    await self._handle_silence()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("nora.silence.watchdog_error", error=str(e))
                break

    async def _handle_silence(self) -> None:
        """Handle detected silence based on count.

        Satisfies: REQ-F-NORA-SILENCE-004
        """
        if self._silence_count == 1:
            action = SilenceAction.FIRST_CHECK
            message = self.FIRST_CHECK_MESSAGE
        elif self._silence_count == 2:
            action = SilenceAction.SECOND_CHECK
            message = self.SECOND_CHECK_MESSAGE
        else:
            action = SilenceAction.SAFE_TRANSFER
            message = self.TRANSFER_MESSAGE

        event = SilenceEvent(
            action=action,
            silence_count=self._silence_count,
            original_question=self._current_question or "",
            timestamp=datetime.now(timezone.utc),
        )

        logger.info(
            "nora.silence.detected",
            action=action.value,
            silence_count=self._silence_count,
            original_question=self._current_question[:50] if self._current_question else "",
        )

        # Call the handler if provided
        if self._on_silence:
            await self._on_silence(event)

        # If this was the third check, stop watching (transfer will happen)
        if self._silence_count >= self.MAX_SILENCE_CHECKS:
            await self.stop_watching()

    def get_response_for_action(self, action: SilenceAction) -> str:
        """Get the response text for a silence action.

        Args:
            action: The silence action

        Returns:
            Response text to speak
        """
        responses = {
            SilenceAction.FIRST_CHECK: self.FIRST_CHECK_MESSAGE,
            SilenceAction.SECOND_CHECK: self.SECOND_CHECK_MESSAGE,
            SilenceAction.SAFE_TRANSFER: self.TRANSFER_MESSAGE,
        }
        return responses.get(action, "")

    @property
    def is_active(self) -> bool:
        """Check if watchdog is currently active."""
        return self._active

    @property
    def current_silence_count(self) -> int:
        """Get current silence check count."""
        return self._silence_count
