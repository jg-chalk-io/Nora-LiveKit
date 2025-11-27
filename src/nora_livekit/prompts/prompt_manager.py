"""Prompt manager for phased conversation handling.

Enables dynamic prompt switching with modular architecture:
- Core rules loaded with EVERY phase (~3K tokens)
- Handler modules loaded on-demand
- Phase-specific prompts (~2-5K tokens each)
- Total: ~5-8K tokens per phase vs 18K single prompt
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


class HandlerType(Enum):
    """Handler modules for specific situations."""

    CONFUSION = "confusion"
    EMERGENCY = "emergency"
    SPECIAL = "special"


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
        if len(digits) == 11 and digits[0] == "1":
            # Handle 1+ country code
            return f"{digits[1]} {digits[2]} {digits[3]}... {digits[4]} {digits[5]} {digits[6]}... {digits[7]} {digits[8]} {digits[9]} {digits[10]}"
        return " ".join(digits)


@dataclass
class PromptManager:
    """Manages phased prompts with modular architecture."""

    prompts_dir: Path
    office_config: dict[str, Any] = field(default_factory=dict)
    _current_phase: PromptPhase = PromptPhase.GREETER
    _context: ConversationContext = field(default_factory=ConversationContext)
    _prompt_cache: dict[PromptPhase, str] = field(default_factory=dict)
    _core_rules: str = ""
    _handlers: dict[HandlerType, str] = field(default_factory=dict)
    _include_handlers_in_prompt: bool = True  # Toggle for including handlers

    def __post_init__(self):
        """Load all prompts into cache."""
        # Load core rules first
        self._load_core_rules()

        # Load all handlers
        self._load_handlers()

        # Load phase-specific prompts
        for phase in PromptPhase:
            self._load_prompt(phase)

        logger.info(
            "prompt_manager.initialized",
            phases_loaded=len(self._prompt_cache),
            handlers_loaded=len(self._handlers),
            has_core_rules=bool(self._core_rules),
            prompts_dir=str(self.prompts_dir),
        )

    def _load_core_rules(self) -> None:
        """Load the core rules that apply to all phases."""
        core_rules_file = self.prompts_dir / "core_rules.md"
        if core_rules_file.exists():
            self._core_rules = core_rules_file.read_text()
            logger.debug(
                "prompt_manager.core_rules_loaded",
                chars=len(self._core_rules),
            )
        else:
            logger.warning("prompt_manager.core_rules_not_found")

    def _load_handlers(self) -> None:
        """Load handler modules."""
        handlers_dir = self.prompts_dir / "handlers"
        if not handlers_dir.exists():
            logger.warning("prompt_manager.handlers_dir_not_found")
            return

        for handler_type in HandlerType:
            handler_file = handlers_dir / f"{handler_type.value}.md"
            if handler_file.exists():
                self._handlers[handler_type] = handler_file.read_text()
                logger.debug(
                    "prompt_manager.handler_loaded",
                    handler=handler_type.value,
                    chars=len(self._handlers[handler_type]),
                )
            else:
                logger.warning(
                    "prompt_manager.handler_not_found",
                    handler=handler_type.value,
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

    def _assemble_full_prompt(self, phase_prompt: str) -> str:
        """Assemble full prompt with core rules and handlers.

        Structure:
        1. Core Rules (always included)
        2. Handlers (included if _include_handlers_in_prompt is True)
        3. Phase-specific prompt

        This allows LLM to reference core rules and handlers from any phase.
        """
        parts = []

        # 1. Core rules (always first)
        if self._core_rules:
            parts.append(self._core_rules)

        # 2. Handlers (if enabled)
        if self._include_handlers_in_prompt:
            for handler_type, handler_content in self._handlers.items():
                if handler_content:
                    parts.append(f"\n---\n\n# Handler: {handler_type.value.title()}\n\n{handler_content}")

        # 3. Phase-specific prompt
        parts.append(f"\n---\n\n{phase_prompt}")

        return "\n".join(parts)

    def get_current_prompt(self, include_core: bool = True) -> str:
        """Get the current phase's prompt with template variables filled.

        Args:
            include_core: If True, prepend core rules and handlers.
                         If False, return only phase-specific prompt.
        """
        template = self._prompt_cache.get(self._current_phase, "")

        if include_core:
            template = self._assemble_full_prompt(template)

        return self._fill_template(template)

    def get_prompt_for_phase(
        self, phase: PromptPhase, include_core: bool = True
    ) -> str:
        """Get a specific phase's prompt with template variables filled."""
        template = self._prompt_cache.get(phase, "")

        if include_core:
            template = self._assemble_full_prompt(template)

        return self._fill_template(template)

    def get_handler(self, handler_type: HandlerType) -> str:
        """Get a specific handler's content with template variables filled."""
        template = self._handlers.get(handler_type, "")
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

    def get_estimated_tokens(
        self, phase: Optional[PromptPhase] = None, include_core: bool = True
    ) -> int:
        """Estimate token count for a phase's prompt.

        Args:
            phase: Phase to estimate. Defaults to current phase.
            include_core: Include core rules and handlers in estimate.
        """
        target_phase = phase or self._current_phase
        prompt = self._prompt_cache.get(target_phase, "")

        if include_core:
            prompt = self._assemble_full_prompt(prompt)

        # Rough estimate: ~4 chars per token
        return len(prompt) // 4

    def get_prompt_stats(self) -> dict[str, Any]:
        """Get statistics about loaded prompts."""
        return {
            "core_rules_chars": len(self._core_rules),
            "core_rules_tokens_est": len(self._core_rules) // 4,
            "handlers": {
                h.value: {
                    "chars": len(c),
                    "tokens_est": len(c) // 4,
                }
                for h, c in self._handlers.items()
            },
            "phases": {
                p.value: {
                    "chars": len(c),
                    "tokens_est": len(c) // 4,
                    "full_tokens_est": self.get_estimated_tokens(p, include_core=True),
                }
                for p, c in self._prompt_cache.items()
            },
        }


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
