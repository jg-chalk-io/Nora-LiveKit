"""Data collection tasks for Nora workflows.

Tasks are focused units that:
1. Collect specific information from the caller
2. Have their own dedicated tools (no routing tools!)
3. Call complete() when all required data is gathered
4. Return typed results to the parent agent

This prevents the infinite loop bug because:
- Tasks don't have routing tools
- Tasks yield control when complete() is called
- Parent agent handles what happens next
"""

import structlog
from dataclasses import dataclass, field
from typing import Optional

from livekit.agents import AgentTask, function_tool, RunContext

from .data import UrgentTransferData, MessageFlowData, CriticalEmergencyData

logger = structlog.get_logger(__name__)


class CollectUrgentInfoTask(AgentTask[UrgentTransferData]):
    """Task to collect information for urgent transfers.

    Collects:
    - Callback number (confirm or get new)
    - First name
    - Last name (optional - skip if rushed)
    - Pet name (confirm from context or ask)
    - Pet age
    - Species/breed
    - Urgency details

    Uses individual tools for each piece of info, allowing
    the LLM to collect in natural conversational order.
    """

    def __init__(
        self,
        chat_ctx=None,
        initial_context: Optional[dict] = None,
    ):
        """Initialize the urgent info collection task.

        Args:
            chat_ctx: Conversation context to preserve
            initial_context: Pre-filled data from greeter (pet_name, species, etc.)
        """
        super().__init__(
            instructions="""You are collecting information for an urgent veterinary case.

RULES:
1. Ask ONE question at a time, then STOP and wait for the answer
2. Be efficient - the caller is worried about their pet
3. Use the record_* tools to save each piece of information
4. The task will automatically complete when required info is gathered

REQUIRED INFO:
- Callback number (confirm the number shown or get a new one)
- First name
- Pet name (confirm if known from context)
- Urgency details (what's happening with the pet)

OPTIONAL (skip if caller seems rushed):
- Last name
- Pet age
- Species/breed (if not already known)

Start by confirming the callback number.""",
            chat_ctx=chat_ctx,
        )

        # Initialize data storage
        self._data = UrgentTransferData(
            callback_number="",
            first_name="",
            pet_name="",
            urgency_reason="",
        )

        # Pre-fill from context if available
        if initial_context:
            if initial_context.get("pet_name"):
                self._data.pet_name = initial_context["pet_name"]
            if initial_context.get("species"):
                self._data.species = initial_context["species"]
            if initial_context.get("reason"):
                self._data.urgency_reason = initial_context["reason"]
            if initial_context.get("caller_phone"):
                # Store but still need to confirm
                self._pending_phone = initial_context["caller_phone"]
            else:
                self._pending_phone = ""

    async def on_enter(self) -> None:
        """Called when the task starts. Begin collecting info."""
        if self._pending_phone:
            # Format phone for speech
            formatted = self._format_phone_for_speech(self._pending_phone)
            await self.session.generate_reply(
                instructions=f"Confirm the callback number: 'I can see you're calling from {formatted}. In case we get disconnected, is that the best number to call you back on?'"
            )
        else:
            await self.session.generate_reply(
                instructions="Ask for the best callback number in case you get disconnected."
            )

    def _format_phone_for_speech(self, phone: str) -> str:
        """Format phone number for TTS with pauses."""
        digits = "".join(c for c in phone if c.isdigit())
        if len(digits) == 10:
            return f"{digits[0]} {digits[1]} {digits[2]}... {digits[3]} {digits[4]} {digits[5]}... {digits[6]} {digits[7]} {digits[8]} {digits[9]}"
        return phone

    def _check_completion(self) -> None:
        """Check if all required data is collected and complete the task."""
        if self._data.is_complete():
            logger.info(
                "urgent_info_task.complete",
                callback=self._data.callback_number[:4] + "...",
                first_name=self._data.first_name,
                pet_name=self._data.pet_name,
            )
            self.complete(self._data)

    @function_tool
    async def record_callback_number(
        self,
        context: RunContext,
        number: str,
        confirmed: bool = True,
    ) -> str:
        """Record the confirmed callback number.

        Args:
            number: The phone number (can be 'same' if confirming shown number)
            confirmed: Whether the caller confirmed this number is correct
        """
        if number.lower() == "same" and hasattr(self, "_pending_phone"):
            self._data.callback_number = self._pending_phone
        else:
            # Clean the number
            self._data.callback_number = "".join(c for c in number if c.isdigit())

        logger.info("urgent_info_task.recorded_phone", phone=self._data.callback_number[:4] + "...")

        self._check_completion()

        if not self._data.is_complete():
            return "Phone recorded. Now ask for the caller's first name."
        return "Phone recorded."

    @function_tool
    async def record_first_name(
        self,
        context: RunContext,
        first_name: str,
    ) -> str:
        """Record the caller's first name.

        Args:
            first_name: The caller's first name
        """
        self._data.first_name = first_name.strip()
        logger.info("urgent_info_task.recorded_name", first_name=first_name)

        self._check_completion()

        if not self._data.is_complete():
            # Don't say the name back immediately (per prompt rules)
            if self._data.pet_name:
                return f"Name recorded. Confirm: 'You mentioned your pet's name is {self._data.pet_name}, right?'"
            else:
                return "Name recorded. Now ask which pet they're calling about."
        return "Name recorded."

    @function_tool
    async def record_last_name(
        self,
        context: RunContext,
        last_name: str,
    ) -> str:
        """Record the caller's last name (optional).

        Args:
            last_name: The caller's last name
        """
        self._data.last_name = last_name.strip()
        logger.info("urgent_info_task.recorded_last_name", last_name=last_name)

        self._check_completion()
        return "Last name recorded. Continue collecting remaining info."

    @function_tool
    async def record_pet_info(
        self,
        context: RunContext,
        pet_name: str,
        species: str = "",
        breed: str = "",
        age: str = "",
    ) -> str:
        """Record pet information.

        Args:
            pet_name: Name of the pet
            species: Type of animal (dog, cat, etc.)
            breed: Specific breed if known
            age: Pet's age
        """
        if pet_name:
            self._data.pet_name = pet_name.strip()
        if species:
            self._data.species = species.strip()
        if breed:
            self._data.breed = breed.strip()
        if age:
            self._data.pet_age = age.strip()

        logger.info(
            "urgent_info_task.recorded_pet",
            pet_name=self._data.pet_name,
            species=self._data.species,
        )

        self._check_completion()

        if not self._data.is_complete():
            if not self._data.urgency_reason:
                return f"Pet info recorded. Now ask what's happening with {self._data.pet_name}."
        return "Pet info recorded."

    @function_tool
    async def record_urgency_details(
        self,
        context: RunContext,
        urgency_reason: str,
        additional_details: str = "",
    ) -> str:
        """Record the urgency details - what's happening with the pet.

        Args:
            urgency_reason: Main reason/symptoms
            additional_details: Any additional info the technician should know
        """
        details = urgency_reason
        if additional_details:
            details = f"{urgency_reason}. Additional: {additional_details}"
        self._data.urgency_reason = details.strip()

        logger.info("urgent_info_task.recorded_urgency", reason=urgency_reason[:50])

        self._check_completion()
        return "Urgency details recorded."

    @function_tool
    async def skip_optional_field(
        self,
        context: RunContext,
        field_name: str,
        reason: str = "caller requested to skip",
    ) -> str:
        """Skip an optional field if caller is rushed.

        Args:
            field_name: Which field to skip (last_name, pet_age, breed)
            reason: Why skipping (e.g., 'caller wants to proceed quickly')
        """
        logger.info(
            "urgent_info_task.skipped_field",
            field=field_name,
            reason=reason,
        )
        self._check_completion()
        return f"Skipped {field_name}. Continue with required fields."


class CollectMessageInfoTask(AgentTask[MessageFlowData]):
    """Task to collect information for non-urgent callback messages.

    Simpler than urgent - just needs:
    - Callback number
    - First name
    - Concern/reason for call
    """

    def __init__(
        self,
        chat_ctx=None,
        initial_context: Optional[dict] = None,
    ):
        super().__init__(
            instructions="""You are collecting information for a callback message.

RULES:
1. Ask ONE question at a time, then STOP and wait
2. Be friendly and helpful - this is not urgent
3. Use record_* tools to save each piece

REQUIRED:
- Callback number
- First name
- What they're calling about (the concern)

OPTIONAL:
- Last name
- Pet name (if relevant)

Start by confirming/asking for the callback number.""",
            chat_ctx=chat_ctx,
        )

        self._data = MessageFlowData(
            callback_number="",
            first_name="",
            concern="",
        )

        if initial_context:
            if initial_context.get("pet_name"):
                self._data.pet_name = initial_context["pet_name"]
            if initial_context.get("species"):
                self._data.species = initial_context["species"]
            if initial_context.get("reason"):
                self._data.concern = initial_context["reason"]
            self._pending_phone = initial_context.get("caller_phone", "")
        else:
            self._pending_phone = ""

    async def on_enter(self) -> None:
        if self._pending_phone:
            formatted = self._format_phone_for_speech(self._pending_phone)
            await self.session.generate_reply(
                instructions=f"Confirm: 'I can see you're calling from {formatted}. Is that the best number for us to call you back?'"
            )
        else:
            await self.session.generate_reply(
                instructions="Ask for the best callback number."
            )

    def _format_phone_for_speech(self, phone: str) -> str:
        digits = "".join(c for c in phone if c.isdigit())
        if len(digits) == 10:
            return f"{digits[0]} {digits[1]} {digits[2]}... {digits[3]} {digits[4]} {digits[5]}... {digits[6]} {digits[7]} {digits[8]} {digits[9]}"
        return phone

    def _check_completion(self) -> None:
        if self._data.is_complete():
            logger.info(
                "message_info_task.complete",
                first_name=self._data.first_name,
                concern_preview=self._data.concern[:30],
            )
            self.complete(self._data)

    @function_tool
    async def record_callback_number(
        self,
        context: RunContext,
        number: str,
    ) -> str:
        """Record the callback number."""
        if number.lower() == "same" and self._pending_phone:
            self._data.callback_number = self._pending_phone
        else:
            self._data.callback_number = "".join(c for c in number if c.isdigit())

        self._check_completion()
        if not self._data.is_complete():
            return "Number recorded. Now ask for their first name."
        return "Number recorded."

    @function_tool
    async def record_name(
        self,
        context: RunContext,
        first_name: str,
        last_name: str = "",
    ) -> str:
        """Record the caller's name."""
        self._data.first_name = first_name.strip()
        if last_name:
            self._data.last_name = last_name.strip()

        self._check_completion()
        if not self._data.is_complete():
            return "Name recorded. Now ask what they're calling about."
        return "Name recorded."

    @function_tool
    async def record_concern(
        self,
        context: RunContext,
        concern: str,
        pet_name: str = "",
    ) -> str:
        """Record what the caller is calling about."""
        self._data.concern = concern.strip()
        if pet_name:
            self._data.pet_name = pet_name.strip()

        self._check_completion()
        return "Concern recorded."


class CollectCriticalInfoTask(AgentTask[CriticalEmergencyData]):
    """Task to collect MINIMAL info for life-threatening emergencies.

    FASTEST PATH - only collects:
    - Callback number (quick confirm)
    - First name (for the technician)

    Does NOT re-ask about pet or emergency - that info comes from context.
    """

    def __init__(
        self,
        chat_ctx=None,
        initial_context: Optional[dict] = None,
    ):
        super().__init__(
            instructions="""CRITICAL EMERGENCY - Collect info FAST.

Only need:
1. Confirm callback number (yes/no question)
2. Get first name

Do NOT ask about the emergency or pet again - we already know.
Be calm but efficient.""",
            chat_ctx=chat_ctx,
        )

        self._data = CriticalEmergencyData(
            callback_number="",
            first_name="",
            emergency_type="",
        )

        if initial_context:
            self._data.pet_name = initial_context.get("pet_name", "")
            self._data.species = initial_context.get("species", "")
            self._data.emergency_type = initial_context.get("emergency_type", "")
            self._pending_phone = initial_context.get("caller_phone", "")
        else:
            self._pending_phone = ""

    async def on_enter(self) -> None:
        if self._pending_phone:
            await self.session.generate_reply(
                instructions="Quick confirm: 'Is your current number the best to reach you? Yes or no?'"
            )
        else:
            await self.session.generate_reply(
                instructions="Quickly ask: 'What's the best number to reach you?'"
            )

    def _check_completion(self) -> None:
        if self._data.is_complete():
            logger.info("critical_info_task.complete", first_name=self._data.first_name)
            self.complete(self._data)

    @function_tool
    async def record_callback_confirmed(
        self,
        context: RunContext,
        confirmed: bool,
        alternate_number: str = "",
    ) -> str:
        """Record callback number confirmation."""
        if confirmed and self._pending_phone:
            self._data.callback_number = self._pending_phone
        elif alternate_number:
            self._data.callback_number = "".join(c for c in alternate_number if c.isdigit())

        self._check_completion()
        if not self._data.is_complete():
            return "Got it. What's your first name?"
        return "Confirmed."

    @function_tool
    async def record_first_name(
        self,
        context: RunContext,
        first_name: str,
    ) -> str:
        """Record first name for the technician."""
        self._data.first_name = first_name.strip()
        self._check_completion()
        return "Thank you. Connecting you now."
