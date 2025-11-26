"""Nora-specific components for veterinary voice assistant.

This module contains Nora-specific behaviors that extend the base
LiveKit conversation engine with veterinary triage workflows.

Components:
- NoraState: Pydantic state model for Nora-specific data
- NoraTools: LLM tools for transfer and message workflows
- NoraTextProcessor: Phone SSML, single-question enforcement
- SilenceWatchdog: Proactive silence detection
- NoraConversationEngine: Full Nora-enhanced engine
"""

from nora_livekit.nora.engine import NoraConversationEngine, NoraEngineConfig
from nora_livekit.nora.silence_watchdog import (
    SilenceWatchdog,
    SilenceEvent,
    SilenceAction,
)
from nora_livekit.nora.state import NoraFlow, NoraState
from nora_livekit.nora.text_processor import NoraTextProcessor
from nora_livekit.nora.tools import NoraTools, get_tool_definitions

__all__ = [
    # Engine
    "NoraConversationEngine",
    "NoraEngineConfig",
    # State
    "NoraFlow",
    "NoraState",
    # Tools
    "NoraTools",
    "get_tool_definitions",
    # Text Processing
    "NoraTextProcessor",
    # Silence Detection
    "SilenceWatchdog",
    "SilenceEvent",
    "SilenceAction",
]
