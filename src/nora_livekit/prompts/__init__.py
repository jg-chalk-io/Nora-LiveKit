"""Phased prompt management for Nora voice agent.

This module handles loading and switching between different conversation phases
with a modular architecture:

- Core Rules (~3K tokens): Shared rules loaded with EVERY phase
- Handlers (~2K tokens each): Confusion, Emergency, Special handlers
- Phase 1: Greeter/Triage (~2K tokens) - Handles greeting and initial routing
- Phase 2A: Urgent Transfer (~4K tokens) - Full collection for urgent cases
- Phase 2B: Message Flow (~4K tokens) - Non-urgent message taking
- Phase 2C: Critical Emergency (~2K tokens) - Life-threatening, minimal collection

Total per phase: ~8-11K tokens (down from 18K single prompt)
"""

from .prompt_manager import (
    HandlerType,
    PromptPhase,
    PromptManager,
    ConversationContext,
    get_prompt_manager,
    reset_prompt_manager,
)

__all__ = [
    "HandlerType",
    "PromptPhase",
    "PromptManager",
    "ConversationContext",
    "get_prompt_manager",
    "reset_prompt_manager",
]
