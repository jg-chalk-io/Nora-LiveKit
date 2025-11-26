"""Nora-specific state management using Pydantic.

Extends ConversationContext with Nora-specific fields for veterinary
triage, data collection, and workflow tracking.

Satisfies REQ-F-NORA-STATE-001 through REQ-F-NORA-STATE-005.
"""

from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field


class NoraFlow(str, Enum):
    """Nora conversation workflow states."""

    GREETING = "greeting"
    TRIAGE = "triage"
    URGENT = "urgent"
    MESSAGE = "message"
    CRITICAL = "critical"
    CLOSING = "closing"


class NoraState(BaseModel):
    """Strongly-typed state for Nora veterinary assistant.

    Prevents hallucinations by providing structured data to LLM.

    Satisfies: REQ-F-NORA-STATE-001, REQ-F-NORA-STATE-002,
               REQ-F-NORA-STATE-003, REQ-F-NORA-STATE-004, REQ-F-NORA-STATE-005
    """

    # Office context
    is_the_clinic_open: bool = Field(
        default=False,
        description="Whether the veterinary clinic is currently open",
    )
    caller_phone: str = Field(
        default="",
        description="Caller's phone number (from SIP or identity)",
    )

    # Collected caller data
    callback_number: Optional[str] = Field(
        default=None,
        description="Confirmed callback number",
    )
    first_name: Optional[str] = Field(
        default=None,
        description="Caller's first name",
    )
    last_name: Optional[str] = Field(
        default=None,
        description="Caller's last name (spelled and confirmed)",
    )

    # Pet information
    pet_name: Optional[str] = Field(
        default=None,
        description="Pet's name (NOT breed)",
    )
    age: Optional[str] = Field(
        default=None,
        description="Pet's age",
    )
    species: Optional[str] = Field(
        default=None,
        description="Pet species (dog, cat, etc.)",
    )
    breed: Optional[str] = Field(
        default=None,
        description="Pet breed (keep separate from pet_name)",
    )

    # Call details
    urgency_reason: Optional[str] = Field(
        default=None,
        description="Reason for urgent transfer",
    )
    concern_description: Optional[str] = Field(
        default=None,
        description="Detailed message/concern for non-urgent calls",
    )

    # Flow control
    flow: NoraFlow = Field(
        default=NoraFlow.GREETING,
        description="Current workflow state",
    )
    last_question: Optional[str] = Field(
        default=None,
        description="Last question asked (for silence handling)",
    )
    silence_checks: int = Field(
        default=0,
        description="Number of silence checks performed",
    )
    data_collection_step: Optional[str] = Field(
        default=None,
        description="Current step in data collection workflow",
    )

    # Debug and configuration
    debug_mode: bool = Field(
        default=False,
        description="Whether DEBUG mode is activated",
    )

    def reset_silence_tracking(self) -> None:
        """Reset silence tracking after receiving a response."""
        self.last_question = None
        self.silence_checks = 0

    def set_question(self, question: str) -> None:
        """Set the last question asked and reset silence counter."""
        self.last_question = question
        self.silence_checks = 0

    def increment_silence_check(self) -> int:
        """Increment silence check counter and return new count."""
        self.silence_checks += 1
        return self.silence_checks

    def has_minimum_transfer_data(self) -> bool:
        """Check if minimum data for transfer is collected.

        For CRITICAL emergencies: callback_number + first_name only.
        """
        return bool(self.callback_number and self.first_name)

    def has_full_transfer_data(self) -> bool:
        """Check if full data for urgent transfer is collected."""
        return bool(
            self.callback_number
            and self.first_name
            and self.pet_name
            and self.urgency_reason
        )

    def has_message_data(self) -> bool:
        """Check if all data for message flow is collected."""
        return bool(
            self.callback_number
            and self.first_name
            and self.concern_description
        )

    def to_prompt_context(self) -> str:
        """Format state as context string for LLM injection.

        Returns JSON representation for structured context.
        """
        return self.model_dump_json(indent=2, exclude_none=True)

    model_config = {"use_enum_values": True}
