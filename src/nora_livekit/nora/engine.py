"""Nora-enhanced conversation engine.

Extends the base ConversationEngine with Nora-specific behaviors:
- Silence watchdog (5s "Are you still there?")
- Emergency keyword detection
- Single question enforcement
- Phone number SSML formatting
- Nora system prompt injection

Satisfies REQ-F-NORA-ENGINE-001 through REQ-F-NORA-ENGINE-008.
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Callable, Awaitable

import structlog

from nora_livekit.conversation.context import ConversationContext, ConversationPhase
from nora_livekit.conversation.engine import ConversationEngine, ConversationEngineConfig
from nora_livekit.conversation.llm import LLMIntegration, LLMResponse
from nora_livekit.conversation.turn_manager import TurnManager
from nora_livekit.nora.silence_watchdog import (
    SilenceWatchdog,
    SilenceEvent,
    SilenceAction,
)
from nora_livekit.nora.state import NoraState, NoraFlow
from nora_livekit.nora.text_processor import NoraTextProcessor
from nora_livekit.nora.tools import NoraTools, get_tool_definitions

logger = structlog.get_logger(__name__)

# Type aliases
SpeakCallback = Callable[[str], Awaitable[None]]
TransferCallback = Callable[[dict], Awaitable[None]]
HangupCallback = Callable[[], Awaitable[None]]


@dataclass
class NoraEngineConfig(ConversationEngineConfig):
    """Configuration for Nora conversation engine."""

    # Office configuration
    office_name: str = "Paws & Claws Veterinary"
    office_hours: str = "Monday–Friday 8 AM–6 PM"
    hospital_address: str = "123 Main St, Toronto, ON"
    office_website: str = "https://pawsclaws.example.com"
    office_phone: str = "4165550198"
    is_clinic_open: bool = False

    # Nora-specific settings
    use_ssml: bool = True
    silence_timeout_seconds: float = 5.0


class NoraConversationEngine(ConversationEngine):
    """Nora-enhanced conversation engine with veterinary workflows.

    Extends ConversationEngine with Nora-specific behaviors while
    maintaining the robust base architecture from SPEC-003.

    Satisfies: REQ-F-NORA-ENGINE-001, REQ-F-NORA-ENGINE-002,
               REQ-F-NORA-ENGINE-003, REQ-F-NORA-ENGINE-004,
               REQ-F-NORA-ENGINE-005, REQ-F-NORA-ENGINE-006,
               REQ-F-NORA-ENGINE-007, REQ-F-NORA-ENGINE-008
    """

    def __init__(
        self,
        config: NoraEngineConfig,
        context: ConversationContext,
        llm: LLMIntegration,
        turn_manager: TurnManager,
        caller_phone: str = "",
        on_speak: Optional[SpeakCallback] = None,
        on_transfer: Optional[TransferCallback] = None,
        on_hangup: Optional[HangupCallback] = None,
    ) -> None:
        """Initialize Nora conversation engine.

        Satisfies: REQ-F-NORA-ENGINE-001

        Args:
            config: NoraEngineConfig with office details
            context: ConversationContext instance
            llm: LLMIntegration instance
            turn_manager: TurnManager instance
            caller_phone: Caller's phone number
            on_speak: Callback to speak text via TTS
            on_transfer: Callback when transfer is triggered
            on_hangup: Callback when call should end
        """
        super().__init__(config, context, llm, turn_manager)

        self.nora_config = config

        # Initialize Nora state
        self.nora_state = NoraState(
            is_the_clinic_open=config.is_clinic_open,
            caller_phone=caller_phone,
        )

        # Initialize Nora-specific components
        self.text_processor = NoraTextProcessor()
        self.silence_watchdog = SilenceWatchdog(
            on_silence=self._handle_silence_event,
        )
        self.tools = NoraTools(
            on_transfer=self._handle_tool_transfer,
            on_message_saved=self._handle_tool_message,
        )

        # Callbacks
        self._on_speak = on_speak
        self._on_transfer = on_transfer
        self._on_hangup = on_hangup

        # Load system prompt
        self._system_prompt = self._load_and_render_prompt()

    def _load_and_render_prompt(self) -> str:
        """Load and render the Nora system prompt with variables.

        Satisfies: REQ-F-NORA-ENGINE-002

        Returns:
            Rendered system prompt
        """
        prompt_path = (
            Path(__file__).parent.parent / "prompts" / "nora_system.md"
        )

        try:
            template = prompt_path.read_text()
        except FileNotFoundError:
            logger.warning(
                "nora.engine.prompt_not_found",
                path=str(prompt_path),
            )
            # Return a minimal fallback prompt
            return self._get_fallback_prompt()

        # Replace template variables
        prompt = template.replace("{{office_name}}", self.nora_config.office_name)
        prompt = prompt.replace(
            "{{is_the_clinic_open}}",
            "yes" if self.nora_config.is_clinic_open else "no",
        )
        prompt = prompt.replace("{{office_hours}}", self.nora_config.office_hours)
        prompt = prompt.replace("{{hospital_address}}", self.nora_config.hospital_address)
        prompt = prompt.replace("{{office_website}}", self.nora_config.office_website)
        prompt = prompt.replace("{{office_phone}}", self.nora_config.office_phone)

        # Replace caller phone digits for callback procedure
        caller_digits = " ".join(self.nora_state.caller_phone) if self.nora_state.caller_phone else "unknown"
        prompt = prompt.replace("{{caller_phone_digits}}", caller_digits)
        prompt = prompt.replace("{{caller_phone_number}}", self.nora_state.caller_phone or "unknown")

        return prompt

    def _get_fallback_prompt(self) -> str:
        """Get a minimal fallback prompt if main prompt fails to load."""
        return f"""You are Nora, the virtual assistant for {self.nora_config.office_name}.

CRITICAL RULES:
1. Ask ONE question at a time and STOP after the question mark
2. Never ask for multiple pieces of information in a single question
3. If silence for 5 seconds, say "Are you still there?"
4. Never provide medical advice - transfer to Vet Wise instead

The clinic is currently {'open' if self.nora_config.is_clinic_open else 'closed'}.
Hours: {self.nora_config.office_hours}
"""

    async def start(self) -> None:
        """Start conversation engine with Nora greeting.

        Satisfies: REQ-F-NORA-ENGINE-003
        """
        await super().start()

        # Generate Nora-specific greeting
        greeting = self._get_greeting()
        await self._speak(greeting)

        # Start silence watchdog for greeting response
        await self.silence_watchdog.start_watching(
            "How can I help you?" if "How can I" in greeting else greeting
        )

    def _get_greeting(self) -> str:
        """Get the appropriate Nora greeting based on clinic status.

        Returns:
            Greeting text
        """
        base = f"Thank you for calling {self.nora_config.office_name}."

        if self.nora_config.is_clinic_open:
            return (
                f"{base} We're currently open but assisting other callers. "
                "I'm Nora, the virtual assistant. How can I help you today?"
            )
        else:
            return (
                f"{base} The office is currently closed, but I'm Nora, "
                "the virtual assistant here to help. How can I assist you?"
            )

    async def process_transcription(
        self,
        text: str,
        participant_id: str = "default",
    ) -> str:
        """Process transcribed text with Nora-specific handling.

        Satisfies: REQ-F-NORA-ENGINE-004, REQ-F-NORA-ENGINE-005

        Args:
            text: Transcribed user text
            participant_id: ID of speaking participant

        Returns:
            Response text for TTS synthesis
        """
        if not self._running:
            return self.config.fallback_response

        # Signal that speech was received (for silence watchdog)
        self.silence_watchdog.on_speech_received()
        await self.silence_watchdog.stop_watching()

        # Reset silence tracking in state
        self.nora_state.reset_silence_tracking()

        # Check for emergency keywords FIRST (before any other processing)
        is_emergency, emergency_type, keyword = self.text_processor.detect_emergency(text)

        if is_emergency:
            return await self._handle_emergency(text, emergency_type, keyword)

        # Check for DEBUG command
        if text.strip().upper() == "DEBUG":
            return await self._handle_debug()

        # Process with base engine
        try:
            # Add user message to context
            self.context.add_message("user", text, participant_id=participant_id)
            self.participant_manager.update_activity(participant_id)
            self._last_message_time = datetime.now(timezone.utc)

            # Generate response with Nora system prompt
            response = await self._generate_nora_response()

            # Post-process response for Nora requirements
            processed_text = self._post_process_response(response.text)

            # Add assistant response to context
            self.context.add_message("assistant", processed_text)

            # Start silence watchdog if response ends with question
            if processed_text.rstrip().endswith("?"):
                self.nora_state.set_question(processed_text)
                await self.silence_watchdog.start_watching(processed_text)

            logger.info(
                "nora.response_generated",
                participant_id=participant_id,
                tokens=response.tokens_used,
                latency_ms=response.latency_ms,
                flow=self.nora_state.flow,
            )

            return processed_text

        except Exception as e:
            logger.error("nora.transcription_processing_error", error=str(e))
            return self.config.fallback_response

    async def _generate_nora_response(self) -> LLMResponse:
        """Generate response using LLM with Nora state injection.

        Satisfies: REQ-F-NORA-ENGINE-006

        Returns:
            LLMResponse from LLM
        """
        # Inject current state into system prompt
        state_context = f"\n\nCURRENT STATE:\n{self.nora_state.to_prompt_context()}"
        full_prompt = self._system_prompt + state_context

        return await self.llm.generate_response(
            self.context,
            system_prompt=full_prompt,
        )

    def _post_process_response(self, text: str) -> str:
        """Post-process LLM response for Nora requirements.

        Satisfies: REQ-F-NORA-ENGINE-007

        Args:
            text: Raw LLM response

        Returns:
            Processed text ready for TTS
        """
        # Apply full processing pipeline
        return self.text_processor.process_for_tts(
            text,
            use_ssml=self.nora_config.use_ssml,
        )

    async def _handle_emergency(
        self,
        text: str,
        emergency_type: Optional[str],
        keyword: str,
    ) -> str:
        """Handle detected emergency in user speech.

        Satisfies: REQ-F-NORA-ENGINE-005

        Args:
            text: Full user text
            emergency_type: "critical" or "triage"
            keyword: The matched keyword

        Returns:
            Response text
        """
        logger.info(
            "nora.emergency_detected",
            type=emergency_type,
            keyword=keyword,
        )

        # Update flow state
        if emergency_type == "critical":
            self.nora_state.flow = NoraFlow.CRITICAL
            # Type B: We know what's happening, skip to minimal collection
            return (
                "Given the urgency, I'm connecting you to Vet Wise, "
                "our live 24/7 triage service for immediate help. "
                f"First, I can see you're calling from {self._format_phone_for_speech()}. "
                "In case we get disconnected, is that the best number to call you back on?"
            )
        else:
            self.nora_state.flow = NoraFlow.TRIAGE
            # Type A: Need to ask what's happening
            pet_ref = self.nora_state.pet_name or "your pet"
            return f"I understand this is urgent. What's happening with {pet_ref}?"

    async def _handle_debug(self) -> str:
        """Handle DEBUG command activation.

        Returns:
            Debug state dump
        """
        self.nora_state.debug_mode = True
        logger.info("nora.debug_mode_activated")

        # Build state summary
        state_dump = self.nora_state.model_dump(exclude_none=True)
        state_lines = [f"  - {k}: {v}" for k, v in state_dump.items() if v]

        return (
            "DEBUG MODE ACTIVATED. Here are the variables I've collected:\n"
            + "\n".join(state_lines)
            + "\n\nTool executions: None yet\n\n"
            "Would you like to continue where we left off, or start over?"
        )

    async def _handle_silence_event(self, event: SilenceEvent) -> None:
        """Handle silence detection events from watchdog.

        Satisfies: REQ-F-NORA-ENGINE-008

        Args:
            event: SilenceEvent with details
        """
        response = self.silence_watchdog.get_response_for_action(event.action)

        if event.action == SilenceAction.SAFE_TRANSFER:
            # Trigger safe transfer
            await self._speak(response)
            await self._trigger_safe_transfer()
        else:
            # Speak the silence check message
            await self._speak(response)

    async def _trigger_safe_transfer(self) -> None:
        """Trigger safe transfer after multiple silence timeouts."""
        logger.info("nora.safe_transfer_triggered")

        # Call transfer tool
        await self.tools.transfer_from_ai_triage_with_metadata(
            callback_number=self.nora_state.caller_phone or "unknown",
            first_name=self.nora_state.first_name or "Unknown",
            urgency_reason="No response after multiple attempts",
        )

        # Trigger transfer callback
        if self._on_transfer:
            await self._on_transfer({
                "callback_number": self.nora_state.caller_phone,
                "first_name": self.nora_state.first_name,
                "urgency_reason": "No response after multiple attempts",
            })

        # End call
        if self._on_hangup:
            await self._on_hangup()

    def _handle_tool_transfer(self, tool_name: str, data: dict) -> None:
        """Handle transfer tool execution."""
        logger.info(
            "nora.tool.transfer_executed",
            tool=tool_name,
            data=data,
        )
        # Update state based on tool data
        if data.get("callback_number"):
            self.nora_state.callback_number = data["callback_number"]
        if data.get("first_name"):
            self.nora_state.first_name = data["first_name"]

    def _handle_tool_message(self, tool_name: str, data: dict) -> None:
        """Handle message tool execution."""
        logger.info(
            "nora.tool.message_executed",
            tool=tool_name,
            data=data,
        )

    async def _speak(self, text: str) -> None:
        """Speak text via TTS callback.

        Args:
            text: Text to speak
        """
        if self._on_speak:
            # Process text for TTS
            processed = self._post_process_response(text)
            await self._on_speak(processed)
        else:
            logger.debug("nora.speak_no_callback", text=text[:50])

    def _format_phone_for_speech(self) -> str:
        """Format caller phone for speech with SSML or fallback."""
        if not self.nora_state.caller_phone:
            return "an unknown number"

        return self.text_processor.format_phone_for_tts(
            self.nora_state.caller_phone,
            use_ssml=self.nora_config.use_ssml,
        )

    async def stop(self) -> None:
        """Stop conversation engine and cleanup Nora components."""
        await self.silence_watchdog.stop_watching()
        await super().stop()
        logger.info("nora.engine_stopped")
