"""Phased prompt management for Nora voice agent.

This module handles loading and switching between different conversation phases:
- Phase 1: Greeter/Triage (~2K tokens) - Handles greeting and initial routing
- Phase 2A: Urgent Transfer (~5K tokens) - Full collection for urgent cases
- Phase 2B: Message Flow (~4K tokens) - Non-urgent message taking
- Phase 2C: Critical Emergency (~2K tokens) - Life-threatening, minimal collection
"""

from .prompt_manager import (
    PromptPhase,
    PromptManager,
    get_prompt_manager,
)

__all__ = [
    "PromptPhase",
    "PromptManager",
    "get_prompt_manager",
]
