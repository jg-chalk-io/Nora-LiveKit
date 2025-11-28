"""Nora workflow agents using LiveKit Agent pattern.

Each agent:
1. Has specific instructions for its phase
2. Uses Tasks for data collection (not tools that can loop!)
3. Returns handoffs to other agents via tool returns
4. Preserves context across transitions

Agent Flow:
    GreeterAgent (triage)
        ├── returns UrgentTransferAgent (needs urgent help)
        ├── returns MessageFlowAgent (can wait for callback)
        └── returns CriticalEmergencyAgent (life-threatening)

    UrgentTransferAgent
        └── CollectUrgentInfoTask → transferFromAiTriageWithMetadata()

    MessageFlowAgent
        └── CollectMessageInfoTask → collectNameNumberConcernPetName()

    CriticalEmergencyAgent
        └── CollectCriticalInfoTask → transferFromAiTriageWithMetadata()
"""

import os
import structlog
from typing import Optional, AsyncIterator, List, Any
from dataclasses import dataclass

from livekit.agents import Agent, AgentSession, function_tool, RunContext, get_job_context


async def _async_iter_frames(frames: List[Any]) -> AsyncIterator[Any]:
    """Convert a list of audio frames to an async iterator.

    session.say(audio=...) expects AsyncIterable[rtc.AudioFrame],
    so we need to convert our pre-synthesized list to an async iterator.
    """
    for frame in frames:
        yield frame

from .data import SessionContext, UrgentTransferData, MessageFlowData, CriticalEmergencyData
from .tasks import CollectUrgentInfoTask, CollectMessageInfoTask, CollectCriticalInfoTask

logger = structlog.get_logger(__name__)

# Configuration
OFFICE_NAME = os.getenv("OFFICE_NAME", "Humber Veterinary Clinic")


class GreeterAgent(Agent):
    """Phase 1: Greets callers and triages to appropriate flow.

    This is the initial agent. It:
    1. Greets the caller
    2. Listens to their concern
    3. Asks triage question (urgent or can wait?)
    4. Returns handoff to appropriate specialist agent

    IMPORTANT: Routing tools return new agents (proper handoff pattern).
    This prevents the infinite loop bug.
    """

    def __init__(
        self,
        chat_ctx=None,
        session_context: Optional[SessionContext] = None,
        prewarmed_greeting_audio: Optional[list] = None,
        prewarmed_greeting_text: Optional[str] = None,
    ):
        # Load prompts from files if available, otherwise use defaults
        instructions = self._load_greeter_instructions()

        super().__init__(
            instructions=instructions,
            chat_ctx=chat_ctx,
        )

        self._context = session_context or SessionContext()
        self._prewarmed_greeting_audio = prewarmed_greeting_audio
        self._prewarmed_greeting_text = prewarmed_greeting_text

    def _load_greeter_instructions(self) -> str:
        """Load greeter prompt from file or use default."""
        # Try to load from prompts directory
        prompt_path = os.path.join(
            os.path.dirname(__file__),
            "..", "..", "..", "..",
            "prompts", "phase1_greeter.md"
        )

        try:
            if os.path.exists(prompt_path):
                with open(prompt_path) as f:
                    return f.read()
        except Exception:
            pass

        # Default instructions
        return f"""You are Nora, the virtual assistant for {OFFICE_NAME}.

## PERSONALITY
- Warm, friendly, and genuinely caring
- Empathetic - acknowledge emotions before jumping to solutions
- Efficient but not cold

## GREETING
If office is closed: "Thank you for calling {OFFICE_NAME}. The office is currently closed, but I'm Nora, the virtual assistant here to help. How can I assist you?"

## EMPATHY FIRST
When caller mentions a problem, acknowledge it warmly:
- "I'm so sorry to hear that about [pet name]."
- "I can hear how worried you are. Let me help."

## TRIAGE
After hearing their concern, ask: "Does your pet need immediate medical assistance, or can this wait for our office staff to return your call?"

## ROUTING
- If URGENT (yes, immediate, urgent, ASAP): Call route_to_urgent_transfer()
- If CAN WAIT (no, not urgent, can wait): Call route_to_message_flow()
- If CRITICAL EMERGENCY (hit by car, not breathing, seizure, unconscious): Call route_to_critical_emergency()

IMPORTANT: Call the routing tool and STOP. The new agent will take over."""

    async def on_enter(self) -> None:
        """Greet the caller when agent starts.

        Uses pre-synthesized audio if available for instant playback (no TTS delay).
        Falls back to generate_reply() if no prewarmed audio.
        """
        # If we have pre-synthesized greeting audio, use it for instant playback
        if self._prewarmed_greeting_audio and self._prewarmed_greeting_text:
            logger.info(
                "greeter.using_prewarmed_audio",
                audio_frames=len(self._prewarmed_greeting_audio),
                text_len=len(self._prewarmed_greeting_text),
            )
            # session.say() with audio skips TTS entirely - instant playback
            # Convert list to async iterator (session.say expects AsyncIterable)
            await self.session.say(
                text=self._prewarmed_greeting_text,
                audio=_async_iter_frames(self._prewarmed_greeting_audio),
            )
            return

        # Fallback: No prewarmed audio, use generate_reply() (slower)
        logger.info("greeter.no_prewarmed_audio_fallback")
        if self._context.is_clinic_open:
            await self.session.generate_reply(
                instructions=f"Greet: 'Thank you for calling {self._context.office_name}. We're currently open but assisting other callers. I'm Nora, the virtual assistant. How can I help you today?'"
            )
        else:
            await self.session.generate_reply(
                instructions=f"Greet: 'Thank you for calling {self._context.office_name}. The office is currently closed, but I'm Nora, the virtual assistant here to help. How can I assist you?'"
            )

    @function_tool()
    async def route_to_urgent_transfer(
        self,
        context: RunContext,
        pet_name: str = "",
        species: str = "",
        reason: str = "",
    ) -> tuple:
        """Route to urgent transfer when pet needs immediate (non-life-threatening) help.

        Call this when caller confirms their pet needs URGENT assistance.
        Returns handoff to UrgentTransferAgent.
        """
        logger.info(
            "greeter.routing_to_urgent",
            pet_name=pet_name,
            species=species,
            reason=reason,
        )

        # Update context with collected info
        self._context.pet_name = pet_name
        self._context.species = species
        self._context.reason = reason
        self._context.triage_result = "urgent"

        # Return new agent (proper handoff pattern)
        # The tuple format is (Agent, return_message)
        return (
            UrgentTransferAgent(
                chat_ctx=self.chat_ctx,
                session_context=self._context,
            ),
            "Transferring to urgent care flow",
        )

    @function_tool()
    async def route_to_message_flow(
        self,
        context: RunContext,
        pet_name: str = "",
        species: str = "",
        reason: str = "",
    ) -> tuple:
        """Route to message flow when request can wait for callback.

        Call this when caller confirms it's NOT urgent and can wait.
        Returns handoff to MessageFlowAgent.
        """
        logger.info(
            "greeter.routing_to_message",
            pet_name=pet_name,
            species=species,
            reason=reason,
        )

        self._context.pet_name = pet_name
        self._context.species = species
        self._context.reason = reason
        self._context.triage_result = "can_wait"

        return (
            MessageFlowAgent(
                chat_ctx=self.chat_ctx,
                session_context=self._context,
            ),
            "Transferring to message flow",
        )

    @function_tool()
    async def route_to_critical_emergency(
        self,
        context: RunContext,
        pet_name: str = "",
        species: str = "",
        emergency_type: str = "",
    ) -> tuple:
        """Route to critical emergency for LIFE-THREATENING situations.

        Call ONLY for: hit by car, not breathing, seizure, unconscious, appears dead.
        Returns handoff to CriticalEmergencyAgent.
        """
        logger.info(
            "greeter.routing_to_critical",
            pet_name=pet_name,
            emergency_type=emergency_type,
        )

        self._context.pet_name = pet_name
        self._context.species = species
        self._context.reason = emergency_type
        self._context.triage_result = "critical_emergency"

        return (
            CriticalEmergencyAgent(
                chat_ctx=self.chat_ctx,
                session_context=self._context,
            ),
            "Transferring to critical emergency",
        )

    @function_tool()
    async def queryCorpus(
        self,
        context: RunContext,
        query: str,
    ) -> str:
        """Look up pet breed/species information.

        Use when caller mentions a breed name and you need to confirm the species.
        Example: queryCorpus("Yorkie") -> "Yorkshire Terrier is a dog breed"
        """
        # Simple breed lookup - in production, this would query a real corpus
        breed_map = {
            "yorkie": "Yorkshire Terrier (dog)",
            "labrador": "Labrador Retriever (dog)",
            "siamese": "Siamese (cat)",
            "persian": "Persian (cat)",
            "golden": "Golden Retriever (dog)",
            "husky": "Siberian Husky (dog)",
            "beagle": "Beagle (dog)",
            "maine coon": "Maine Coon (cat)",
            "bulldog": "Bulldog (dog)",
            "poodle": "Poodle (dog)",
        }

        query_lower = query.lower()
        for breed, full_name in breed_map.items():
            if breed in query_lower:
                return f"{query} is a {full_name}"

        return f"Could not find specific breed info for '{query}'. Ask the caller directly."


class UrgentTransferAgent(Agent):
    """Phase 2A: Handles urgent (but not life-threatening) transfers.

    Uses CollectUrgentInfoTask to gather all required info, then
    executes the transfer to Vet Wise.

    NO routing tools - once here, we collect and transfer.
    """

    def __init__(
        self,
        chat_ctx=None,
        session_context: Optional[SessionContext] = None,
    ):
        super().__init__(
            instructions="""You are Nora, continuing an urgent call.
The caller's pet needs immediate assistance.

## URGENCY PACING
- Faster pace than normal - the caller is worried
- Brief acknowledgments: "Got it." "Thank you."
- Show you understand: "I know time matters here."
- Ask one question at a time, move quickly between questions

## TONE
- Empathetic but efficient
- Reassuring: "I'm getting you connected to help right away."
- Calm confidence, not panic

Collect information quickly and transfer to Vet Wise (24/7 partner).""",
            chat_ctx=chat_ctx,
        )
        self._context = session_context or SessionContext()

    async def on_enter(self) -> None:
        """Start the data collection task."""
        logger.info("urgent_transfer_agent.started")

        # Set expectations first
        await self.session.generate_reply(
            instructions="Say: 'I understand. Let me get you connected to Vet Wise—they're our 24/7 partner staffed by registered veterinary technicians who can help. I just need a few quick details first.'"
        )

        # Run the data collection task
        initial_context = {
            "pet_name": self._context.pet_name,
            "species": self._context.species,
            "reason": self._context.reason,
            "caller_phone": self._context.caller_phone,
        }

        collected_data: UrgentTransferData = await CollectUrgentInfoTask(
            chat_ctx=self.chat_ctx,
            initial_context=initial_context,
        )

        # Task completed - execute transfer
        logger.info(
            "urgent_transfer_agent.data_collected",
            first_name=collected_data.first_name,
            pet_name=collected_data.pet_name,
        )

        # Execute the transfer
        await self._execute_transfer(collected_data)

    async def _execute_transfer(self, data: UrgentTransferData) -> None:
        """Execute the transfer to Vet Wise with collected metadata."""
        logger.info(
            "urgent_transfer_agent.executing_transfer",
            callback=data.callback_number[:4] + "...",
            first_name=data.first_name,
        )

        # Announce transfer
        await self.session.generate_reply(
            instructions="Say: 'Thank you, I have all the details. Please stay on the line while I connect you to Vet Wise.'"
        )

        # In production: trigger SIP transfer, webhook, etc.
        # For now, log and simulate
        logger.info(
            "TRANSFER_EXECUTED",
            to="VetWise",
            callback_number=data.callback_number,
            first_name=data.first_name,
            last_name=data.last_name,
            pet_name=data.pet_name,
            pet_age=data.pet_age,
            species=data.species,
            breed=data.breed,
            urgency_reason=data.urgency_reason,
        )

        # In a real implementation, you would:
        # 1. Call your transfer API/webhook
        # 2. Initiate SIP transfer
        # 3. Handle transfer failure with fallback


class MessageFlowAgent(Agent):
    """Phase 2B: Handles non-urgent callback messages.

    Uses CollectMessageInfoTask to gather info, then saves
    the message for office staff to return the call.
    """

    def __init__(
        self,
        chat_ctx=None,
        session_context: Optional[SessionContext] = None,
    ):
        super().__init__(
            instructions="""You are Nora, taking a message for a callback.
This is NOT urgent - the caller can wait for office staff.
Be friendly and thorough in collecting their information.""",
            chat_ctx=chat_ctx,
        )
        self._context = session_context or SessionContext()

    async def on_enter(self) -> None:
        """Start the message collection task."""
        logger.info("message_flow_agent.started")

        pet_ref = self._context.pet_name or "your pet"
        await self.session.generate_reply(
            instructions=f"Say: 'I can take a message for you about {pet_ref}. Our staff will call you back as soon as possible. Let me get a few details.'"
        )

        initial_context = {
            "pet_name": self._context.pet_name,
            "species": self._context.species,
            "reason": self._context.reason,
            "caller_phone": self._context.caller_phone,
        }

        collected_data: MessageFlowData = await CollectMessageInfoTask(
            chat_ctx=self.chat_ctx,
            initial_context=initial_context,
        )

        logger.info(
            "message_flow_agent.data_collected",
            first_name=collected_data.first_name,
            concern_preview=collected_data.concern[:30],
        )

        await self._save_message(collected_data)

    async def _save_message(self, data: MessageFlowData) -> None:
        """Save the callback message."""
        logger.info(
            "MESSAGE_SAVED",
            callback_number=data.callback_number,
            first_name=data.first_name,
            last_name=data.last_name,
            pet_name=data.pet_name,
            concern=data.concern,
        )

        await self.session.generate_reply(
            instructions=f"Say: 'Thank you, {data.first_name}. I've recorded your message and our staff will call you back at the number you provided. Is there anything else I can help you with before you go?'"
        )

        # In production: call webhook to save message, send notification, etc.


class CriticalEmergencyAgent(Agent):
    """Phase 2C: Handles life-threatening emergencies.

    FASTEST PATH - minimal data collection, immediate transfer.
    Uses CollectCriticalInfoTask for only essential info.
    """

    def __init__(
        self,
        chat_ctx=None,
        session_context: Optional[SessionContext] = None,
    ):
        super().__init__(
            instructions="""CRITICAL EMERGENCY - FASTEST PACE.
The caller has a pet in a life-threatening situation.

## CRITICAL URGENCY PACING
- DIRECT and EFFICIENT - no pleasantries
- Minimal words, fastest pace
- Skip "thank you" and transitions
- Every second counts

## TONE
- Calm but URGENT
- Confident: You know exactly what to do
- Reassuring: "I'm connecting you right now."

## DATA COLLECTION
Collect ONLY: callback number confirmation and first name.
Then transfer IMMEDIATELY.

Example: "Is [phone] the best callback? [wait] Your first name? [wait] Connecting you now."
""",
            chat_ctx=chat_ctx,
        )
        self._context = session_context or SessionContext()

    async def on_enter(self) -> None:
        """Immediately start collecting minimal info."""
        logger.info(
            "critical_emergency_agent.started",
            emergency_type=self._context.reason,
        )

        pet_ref = self._context.pet_name or "your pet"
        await self.session.generate_reply(
            instructions=f"Say urgently but calmly: 'Given the urgency with {pet_ref}, I'm connecting you to Vet Wise immediately for help. I just need to confirm one thing.'"
        )

        initial_context = {
            "pet_name": self._context.pet_name,
            "species": self._context.species,
            "emergency_type": self._context.reason,
            "caller_phone": self._context.caller_phone,
        }

        collected_data: CriticalEmergencyData = await CollectCriticalInfoTask(
            chat_ctx=self.chat_ctx,
            initial_context=initial_context,
        )

        logger.info(
            "critical_emergency_agent.data_collected",
            first_name=collected_data.first_name,
        )

        await self._execute_emergency_transfer(collected_data)

    async def _execute_emergency_transfer(self, data: CriticalEmergencyData) -> None:
        """Execute immediate transfer for critical emergency."""
        logger.info(
            "CRITICAL_TRANSFER_EXECUTED",
            to="VetWise",
            callback_number=data.callback_number,
            first_name=data.first_name,
            emergency_type=data.emergency_type,
            pet_name=data.pet_name,
        )

        await self.session.generate_reply(
            instructions="Say: 'Connecting you now. Stay on the line.'"
        )

        # In production: immediate SIP transfer with highest priority
