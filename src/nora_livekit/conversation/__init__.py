"""Conversation engine module for Nora LiveKit agent.

SPEC: SPEC-LIVEKIT-003 - Context & Conversation Engine

Components:
- context: ConversationContext for managing conversation state
- llm: LLMIntegration for multi-provider LLM support
- turn_manager: TurnManager for turn-taking detection
- engine: ConversationEngine orchestrator
- participant_manager: ParticipantManager for multi-user support
"""
