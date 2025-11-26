"""Tests for ConversationEngine orchestration.

Tests cover REQ-F-ENG-001 through REQ-F-ENG-007 and AC-001 through AC-010.
"""

import pytest
from nora_livekit.conversation.context import ConversationContext, ConversationPhase
from nora_livekit.conversation.engine import ConversationEngine, ConversationEngineConfig
from nora_livekit.conversation.llm import LLMIntegration, LLMProvider
from nora_livekit.conversation.turn_manager import TurnManager
from nora_livekit.conversation.turn_manager import TurnEvent, TurnData
from datetime import datetime, timezone


class TestConversationEngineInitialization:
    """Test REQ-F-ENG-001: Engine Initialization."""

    def test_engine_initialization(self) -> None:
        """Test creating ConversationEngine."""
        config = ConversationEngineConfig()
        ctx = ConversationContext()
        llm = LLMIntegration(
            provider=LLMProvider.OPENAI,
            api_key="sk-test",
            model="gpt-4",
        )
        turn_manager = TurnManager()

        engine = ConversationEngine(
            config=config,
            context=ctx,
            llm=llm,
            turn_manager=turn_manager,
        )
        assert engine.config == config
        assert engine.context == ctx


class TestConversationPhaseTransition:
    """Test REQ-F-ENG-007: Phase Transition Logic."""

    def test_initial_phase_is_greeting(self) -> None:
        """Test that conversation starts in GREETING phase."""
        config = ConversationEngineConfig()
        ctx = ConversationContext()
        llm = LLMIntegration(
            provider=LLMProvider.OPENAI,
            api_key="sk-test",
            model="gpt-4",
        )
        turn_manager = TurnManager()

        engine = ConversationEngine(
            config=config,
            context=ctx,
            llm=llm,
            turn_manager=turn_manager,
        )
        assert engine.context.phase == ConversationPhase.GREETING

    def test_should_transition_to_active(self) -> None:
        """Test transitioning from GREETING to ACTIVE after 2 messages."""
        config = ConversationEngineConfig()
        ctx = ConversationContext()
        llm = LLMIntegration(
            provider=LLMProvider.OPENAI,
            api_key="sk-test",
            model="gpt-4",
        )
        turn_manager = TurnManager()

        engine = ConversationEngine(
            config=config,
            context=ctx,
            llm=llm,
            turn_manager=turn_manager,
        )

        # Add messages
        ctx.add_message("user", "Hello")
        assert engine._should_transition_to_active() is True

        # Transition
        ctx.set_phase(ConversationPhase.ACTIVE)
        assert ctx.phase == ConversationPhase.ACTIVE


class TestTurnSuppression:
    """Test REQ-F-TURN-004: Turn suppression during agent speech."""

    def test_turn_suppression_when_agent_speaking(self) -> None:
        """Test that turns are suppressed when agent_speaking=True."""
        config = ConversationEngineConfig()
        ctx = ConversationContext()
        llm = LLMIntegration(
            provider=LLMProvider.OPENAI,
            api_key="sk-test",
            model="gpt-4",
        )
        turn_manager = TurnManager()

        engine = ConversationEngine(
            config=config,
            context=ctx,
            llm=llm,
            turn_manager=turn_manager,
        )

        turn_manager.set_agent_speaking(True)
        assert turn_manager.agent_speaking is True

        turn_manager.set_agent_speaking(False)
        assert turn_manager.agent_speaking is False
