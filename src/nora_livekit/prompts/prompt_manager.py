"""Prompt manager for phased conversation handling.

Enables dynamic prompt switching for reduced latency:
- Phase 1 loads minimal prompt for greeting (~2K tokens)
- Phase 2 loads specialized prompt based on triage result (~4-5K tokens)
- Total savings: 60-70% vs single 18K token prompt
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional

import structlog

logger = structlog.get_logger(__name__)

# Global prompt manager instance
_manager: Optional["PromptManager"] = None


class PromptPhase(Enum):
    """Conversation phases with specialized prompts."""

    GREETER = "phase1_greeter"
    URGENT_TRANSFER = "phase2a_urgent_transfer"
    MESSAGE_FLOW = "phase2b_message_flow"
    CRITICAL_EMERGENCY = "phase2c_critical_emergency"


@dataclass
class ConversationContext:
    """Context passed between conversation phases."""

    # Caller info
    caller_phone: str = ""
    callback_number: str = ""

    # Collected info
    first_name: str = ""
    last_name: str = ""
    pet_name: str = ""
    species: str = ""
    breed: str = ""
    age: str = ""
    reason: str = ""
    urgency_reason: str = ""
    concern_description: str = ""

    # State
    triage_result: str = ""  # "urgent", "can_wait", "critical_emergency"
    emergency_type: str = ""  # For critical emergencies

    def to_template_vars(self) -> dict[str, str]:
        """Convert context to template variables."""
        return {
            "caller_phone": self.caller_phone,
            "caller_phone_formatted": self._format_phone(self.caller_phone),
            "callback_number": self.callback_number,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "pet_name": self.pet_name or "your pet",
            "species": self.species,
            "breed": self.breed,
            "age": self.age,
            "reason": self.reason,
            "urgency_reason": self.urgency_reason,
            "concern_description": self.concern_description,
            "emergency_type": self.emergency_type,
        }

    def _format_phone(self, phone: str) -> str:
        """Format phone number for speech (digit by digit with pauses)."""
        digits = "".join(c for c in phone if c.isdigit())
        if len(digits) == 10:
            return f"{digits[0]} {digits[1]} {digits[2]}... {digits[3]} {digits[4]} {digits[5]}... {digits[6]} {digits[7]} {digits[8]} {digits[9]}"
        return " ".join(digits)


@dataclass
class PromptManager:
    """Manages phased prompts for conversation handling."""

    prompts_dir: Path
    office_config: dict[str, Any] = field(default_factory=dict)
    _current_phase: PromptPhase = PromptPhase.GREETER
    _context: ConversationContext = field(default_factory=ConversationContext)
    _prompt_cache: dict[PromptPhase, str] = field(default_factory=dict)

    def __post_init__(self):
        """Load all prompts into cache."""
        for phase in PromptPhase:
            self._load_prompt(phase)
        logger.info(
            "prompt_manager.initialized",
            phases_loaded=len(self._prompt_cache),
            prompts_dir=str(self.prompts_dir),
        )

    def _load_prompt(self, phase: PromptPhase) -> str:
        """Load a prompt file and cache it."""
        prompt_file = self.prompts_dir / f"{phase.value}.md"
        if not prompt_file.exists():
            logger.warning("prompt_manager.file_not_found", phase=phase.value)
            return ""

        content = prompt_file.read_text()
        self._prompt_cache[phase] = content
        logger.debug(
            "prompt_manager.prompt_loaded",
            phase=phase.value,
            chars=len(content),
        )
        return content

    def get_current_prompt(self) -> str:
        """Get the current phase's prompt with template variables filled."""
        template = self._prompt_cache.get(self._current_phase, "")
        return self._fill_template(template)

    def get_prompt_for_phase(self, phase: PromptPhase) -> str:
        """Get a specific phase's prompt with template variables filled."""
        template = self._prompt_cache.get(phase, "")
        return self._fill_template(template)

    def _fill_template(self, template: str) -> str:
        """Fill template variables in prompt."""
        # Office config variables
        variables = {
            "office_name": self.office_config.get("name", "the clinic"),
            "office_hours": self.office_config.get("hours", "Monday-Friday 8 AM-6 PM"),
            "office_address": self.office_config.get("address", ""),
            "office_website": self.office_config.get("website", ""),
            "office_phone": self.office_config.get("phone", ""),
            "is_clinic_open": str(self.office_config.get("is_open", False)).lower(),
        }

        # Add context variables
        variables.update(self._context.to_template_vars())

        # Fill template
        result = template
        for key, value in variables.items():
            result = result.replace("{{" + key + "}}", str(value))

        return result

    def transition_to(
        self,
        phase: PromptPhase,
        context_updates: Optional[dict[str, Any]] = None,
    ) -> str:
        """Transition to a new phase with context.

        Args:
            phase: The phase to transition to
            context_updates: Updates to apply to conversation context

        Returns:
            The new phase's prompt with context filled in
        """
        # Update context
        if context_updates:
            for key, value in context_updates.items():
                if hasattr(self._context, key):
                    setattr(self._context, key, value)

        old_phase = self._current_phase
        self._current_phase = phase

        logger.info(
            "prompt_manager.phase_transition",
            from_phase=old_phase.value,
            to_phase=phase.value,
            context={
                "pet_name": self._context.pet_name,
                "reason": self._context.reason,
                "triage_result": self._context.triage_result,
            },
        )

        return self.get_current_prompt()

    def update_context(self, **kwargs) -> None:
        """Update conversation context."""
        for key, value in kwargs.items():
            if hasattr(self._context, key):
                setattr(self._context, key, value)

    @property
    def current_phase(self) -> PromptPhase:
        """Get current conversation phase."""
        return self._current_phase

    @property
    def context(self) -> ConversationContext:
        """Get current conversation context."""
        return self._context

    def get_estimated_tokens(self, phase: Optional[PromptPhase] = None) -> int:
        """Estimate token count for a phase's prompt."""
        target_phase = phase or self._current_phase
        prompt = self._prompt_cache.get(target_phase, "")
        # Rough estimate: ~4 chars per token
        return len(prompt) // 4


def get_prompt_manager(
    prompts_dir: Optional[Path] = None,
    office_config: Optional[dict[str, Any]] = None,
) -> PromptManager:
    """Get or create the global prompt manager.

    Args:
        prompts_dir: Directory containing prompt files
        office_config: Office configuration dict

    Returns:
        PromptManager instance
    """
    global _manager

    if _manager is None:
        if prompts_dir is None:
            # Default to prompts/ directory relative to project root
            prompts_dir = Path(__file__).parent.parent.parent.parent / "prompts"

        _manager = PromptManager(
            prompts_dir=prompts_dir,
            office_config=office_config or {},
        )

    return _manager


def reset_prompt_manager() -> None:
    """Reset the global prompt manager (for testing)."""
    global _manager
    _manager = None
