"""Conversation engine orchestrator.

Orchestrates conversation flow, integrates all components, manages lifecycle.

Satisfies REQ-F-ENG-001 through REQ-F-ENG-007.
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

import structlog

from nora_livekit.conversation.context import ConversationContext, ConversationPhase
from nora_livekit.conversation.llm import LLMIntegration
from nora_livekit.conversation.participant_manager import ParticipantManager
from nora_livekit.conversation.turn_manager import TurnManager, TurnEvent, TurnData

logger = structlog.get_logger(__name__)


@dataclass
class ConversationEngineConfig:
    """Configuration for ConversationEngine."""

    max_history: int = 20
    idle_timeout_seconds: int = 120
    enable_interruptions: bool = True
    fallback_response: str = "I'm having trouble right now. Please try again."


class ConversationEngine:
    """Orchestrates conversation flow with context, LLM, and turn management.

    Satisfies: REQ-F-ENG-001, REQ-F-ENG-002, REQ-F-ENG-003,
               REQ-F-ENG-004, REQ-F-ENG-005, REQ-F-ENG-006, REQ-F-ENG-007
    """

    def __init__(
        self,
        config: ConversationEngineConfig,
        context: ConversationContext,
        llm: LLMIntegration,
        turn_manager: TurnManager,
    ) -> None:
        """Initialize conversation engine with dependencies.

        Satisfies: REQ-F-ENG-001

        Args:
            config: ConversationEngineConfig
            context: ConversationContext instance
            llm: LLMIntegration instance
            turn_manager: TurnManager instance
        """
        self.config = config
        self.context = context
        self.llm = llm
        self.turn_manager = turn_manager
        self.participant_manager = ParticipantManager(context)
        self._running = False
        self._last_message_time: Optional[datetime] = None
        self._idle_timeout_task: Optional[asyncio.Task[None]] = None

    async def start(self) -> None:
        """Start conversation engine and generate initial greeting.

        Satisfies: REQ-F-ENG-002
        """
        if self._running:
            return

        self._running = True
        self._last_message_time = datetime.now(timezone.utc)

        logger.info("conversation_engine_started", phase=self.context.phase.value)

        # Generate initial greeting
        greeting = await self._generate_greeting()
        logger.info("greeting_generated", text=greeting)

    async def stop(self) -> None:
        """Stop conversation engine and cleanup."""
        self._running = False
        if self._idle_timeout_task:
            self._idle_timeout_task.cancel()

        logger.info("conversation_engine_stopped")

    async def process_transcription(
        self,
        text: str,
        participant_id: str = "default",
    ) -> str:
        """Process transcribed text and generate response.

        This is the main entry point for conversation processing.
        Called by VoicePipeline._handle_transcription().

        Satisfies: REQ-F-ENG-003, REQ-F-ENG-004

        Args:
            text: Transcribed user text
            participant_id: ID of speaking participant

        Returns:
            Response text for TTS synthesis
        """
        if not self._running:
            return self.config.fallback_response

        try:
            # Add user message to context
            self.context.add_message("user", text, participant_id=participant_id)
            self.participant_manager.update_activity(participant_id)
            self._last_message_time = datetime.now(timezone.utc)

            # Check if should transition to ACTIVE phase
            if self._should_transition_to_active():
                self.context.set_phase(ConversationPhase.ACTIVE)
                logger.info("transitioned_to_active_phase")

            # Generate response using LLM
            llm_response = asyncio.create_task(
                self.llm.generate_response(self.context)
            )
            response = await asyncio.wait_for(llm_response, timeout=5.0)

            # Add assistant response to context
            self.context.add_message("assistant", response.text)

            logger.info(
                "response_generated",
                participant_id=participant_id,
                tokens=response.tokens_used,
                latency_ms=response.latency_ms,
            )

            return response.text

        except Exception as e:
            logger.error("transcription_processing_error", error=str(e))
            return self.config.fallback_response

    async def handle_turn_event(self, turn_data: TurnData) -> None:
        """Handle turn-taking events from TurnManager.

        Satisfies: REQ-F-ENG-005

        Args:
            turn_data: TurnData with event details
        """
        if turn_data.event == TurnEvent.INTERRUPTION:
            logger.info("user_interruption_detected")
            if self.config.enable_interruptions:
                # Stop current TTS playback and reset buffer
                # (handled by VoicePipeline)
                pass

    async def _generate_greeting(self) -> str:
        """Generate initial greeting message.

        Satisfies: REQ-F-ENG-002

        Returns:
            Greeting text
        """
        try:
            response = await self.llm.generate_response(self.context)
            self.context.add_message("assistant", response.text)
            return response.text
        except Exception as e:
            logger.error("greeting_generation_error", error=str(e))
            fallback = "Hello! How can I help you today?"
            self.context.add_message("assistant", fallback)
            return fallback

    async def _handle_idle_timeout(self) -> None:
        """Handle conversation idle timeout and transition to closing.

        Satisfies: REQ-F-ENG-006
        """
        while self._running:
            try:
                # Check idle timeout
                if self._last_message_time:
                    elapsed = (
                        datetime.now(timezone.utc) - self._last_message_time
                    ).total_seconds()
                    if (
                        elapsed > self.config.idle_timeout_seconds
                        and self.context.phase != ConversationPhase.CLOSING
                    ):
                        self.context.set_phase(ConversationPhase.CLOSING)
                        logger.info("idle_timeout_triggered")

                await asyncio.sleep(10)  # Check every 10 seconds

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("idle_timeout_error", error=str(e))

    def _should_transition_to_active(self) -> bool:
        """Check if conversation should transition from greeting to active.

        Satisfies: REQ-F-ENG-007

        Returns:
            True if should transition to ACTIVE phase
        """
        if self.context.phase != ConversationPhase.GREETING:
            return False

        # Transition to ACTIVE after receiving 1+ user messages
        user_messages = [m for m in self.context.get_history() if m.role == "user"]
        return len(user_messages) >= 1

    def _should_transition_to_closing(self) -> bool:
        """Check if conversation should transition to closing phase.

        Satisfies: REQ-F-ENG-006

        Returns:
            True if should transition to CLOSING phase
        """
        if self.context.phase == ConversationPhase.CLOSING:
            return False

        # Check idle timeout
        if self._last_message_time:
            elapsed = (
                datetime.now(timezone.utc) - self._last_message_time
            ).total_seconds()
            return elapsed > self.config.idle_timeout_seconds

        return False
