"""Data classes for Nora workflow results.

These dataclasses define the structured data collected by each task.
They are used as the result type for AgentTask generics.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class UrgentTransferData:
    """Data collected for urgent (but not life-threatening) transfers.

    Required fields:
    - callback_number: Confirmed phone number for callbacks
    - first_name: Caller's first name
    - pet_name: Name of the pet (or "no pet" if not applicable)
    - urgency_reason: Description of the urgent issue

    Optional fields:
    - last_name: Caller's last name (skip if caller is rushed)
    - pet_age: Age of the pet
    - species: Type of animal (dog, cat, etc.)
    - breed: Specific breed if known
    """
    callback_number: str
    first_name: str
    pet_name: str
    urgency_reason: str
    last_name: str = ""
    pet_age: str = ""
    species: str = ""
    breed: str = ""

    def is_complete(self) -> bool:
        """Check if all required fields are populated."""
        return bool(
            self.callback_number
            and self.first_name
            and self.pet_name
            and self.urgency_reason
        )

    def missing_fields(self) -> list[str]:
        """Return list of missing required fields."""
        missing = []
        if not self.callback_number:
            missing.append("callback_number")
        if not self.first_name:
            missing.append("first_name")
        if not self.pet_name:
            missing.append("pet_name")
        if not self.urgency_reason:
            missing.append("urgency_reason")
        return missing


@dataclass
class MessageFlowData:
    """Data collected for non-urgent callback messages.

    Required fields:
    - callback_number: Phone number for callback
    - first_name: Caller's first name
    - concern: Description of concern/reason for call

    Optional fields:
    - last_name: Caller's last name
    - pet_name: Name of the pet
    - species: Type of animal
    """
    callback_number: str
    first_name: str
    concern: str
    last_name: str = ""
    pet_name: str = ""
    species: str = ""

    def is_complete(self) -> bool:
        """Check if all required fields are populated."""
        return bool(
            self.callback_number
            and self.first_name
            and self.concern
        )

    def missing_fields(self) -> list[str]:
        """Return list of missing required fields."""
        missing = []
        if not self.callback_number:
            missing.append("callback_number")
        if not self.first_name:
            missing.append("first_name")
        if not self.concern:
            missing.append("concern")
        return missing


@dataclass
class CriticalEmergencyData:
    """Data collected for life-threatening emergencies.

    This is the FASTEST path - only collects essential info:
    - callback_number: Phone for disconnection
    - first_name: Caller identification
    - emergency_type: What's happening (hit by car, not breathing, etc.)

    Pet info is captured from context if available, not re-asked.
    """
    callback_number: str
    first_name: str
    emergency_type: str
    pet_name: str = ""  # From context, not re-asked
    species: str = ""   # From context, not re-asked

    def is_complete(self) -> bool:
        """Check if all required fields are populated."""
        return bool(
            self.callback_number
            and self.first_name
            and self.emergency_type
        )

    def missing_fields(self) -> list[str]:
        """Return list of missing required fields."""
        missing = []
        if not self.callback_number:
            missing.append("callback_number")
        if not self.first_name:
            missing.append("first_name")
        if not self.emergency_type:
            missing.append("emergency_type")
        return missing


@dataclass
class SessionContext:
    """Shared context passed between agents during handoffs.

    This replaces the global state approach with proper state passing.
    """
    # From caller ID
    caller_phone: str = ""

    # Triage result from greeter
    triage_result: str = ""  # "urgent", "can_wait", "critical_emergency"

    # Pet info from initial conversation
    pet_name: str = ""
    species: str = ""
    breed: str = ""
    reason: str = ""

    # Clinic info
    office_name: str = "Humber Veterinary Clinic"
    is_clinic_open: bool = False
