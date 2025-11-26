"""Integration tests for conversation system.

Tests complete conversation flows and edge cases.
"""

import pytest
from nora_livekit.conversation.context import ConversationContext, ConversationPhase
from nora_livekit.conversation.engine import ConversationEngine, ConversationEngineConfig
from nora_livekit.conversation.llm import LLMIntegration, LLMProvider
from nora_livekit.conversation.turn_manager import TurnManager
from nora_livekit.conversation.participant_manager import ParticipantManager


class TestBasicConversationFlow:
    """Test AC-001: Basic greeting flow."""

    def test_conversation_initialization(self) -> None:
        """Test conversation starts in GREETING phase."""
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
        assert engine.context.session_id is not None


class TestMultiTurnConversation:
    """Test AC-002: Multi-turn Q&A with context."""

    def test_message_history_preservation(self) -> None:
        """Test that message history is preserved across turns."""
        ctx = ConversationContext(max_history=20)

        # Add conversation messages
        messages = [
            ("user", "What is the capital of France?"),
            ("assistant", "The capital of France is Paris."),
            ("user", "What is its population?"),
            ("assistant", "Paris has a population of about 2 million people."),
            ("user", "What was my first question?"),
        ]

        for role, content in messages:
            ctx.add_message(role, content)

        # Verify all messages are preserved
        history = ctx.get_history()
        assert len(history) == 5
        assert history[0].content == "What is the capital of France?"
        assert history[-1].content == "What was my first question?"


class TestParticipantTracking:
    """Test AC-004: Participant join/leave handling."""

    def test_multi_participant_conversation(self) -> None:
        """Test tracking multiple participants."""
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

        # Add multiple participants
        engine.participant_manager.add_participant("alice", "Alice")
        engine.participant_manager.add_participant("bob", "Bob")
        engine.participant_manager.add_participant("charlie", "Charlie")

        # Verify all are active
        active = engine.participant_manager.get_active_participants()
        assert len(active) == 3

        # Remove one participant
        engine.participant_manager.remove_participant("bob")

        # Verify only 2 are still active
        active = engine.participant_manager.get_active_participants()
        assert len(active) == 2
        assert active[0].participant_id == "alice"
        assert active[1].participant_id == "charlie"


class TestContextFormatting:
    """Test AC-008: Context retention and formatting."""

    def test_context_limit_enforcement(self) -> None:
        """Test that context limit is enforced."""
        ctx = ConversationContext(max_history=5)

        # Add 10 messages
        for i in range(10):
            ctx.add_message("user" if i % 2 == 0 else "assistant", f"Message {i}")

        # Verify only 5 messages retained
        history = ctx.get_history()
        assert len(history) == 5

        # Verify oldest messages removed, newest retained
        assert history[0].content == "Message 5"
        assert history[-1].content == "Message 9"

    def test_format_for_llm_consistency(self) -> None:
        """Test format_for_llm produces consistent output."""
        ctx = ConversationContext()

        # Add messages
        ctx.add_message("user", "Hello")
        ctx.add_message("assistant", "Hi there")

        # Format for LLM
        formatted = ctx.format_for_llm()

        # Verify format
        assert len(formatted) == 2
        assert all("role" in msg for msg in formatted)
        assert all("content" in msg for msg in formatted)
        assert all(len(msg) == 2 for msg in formatted)  # Only role and content


class TestPhaseTransitions:
    """Test AC-007: Conversation state transitions."""

    def test_greeting_to_active_transition(self) -> None:
        """Test automatic transition from GREETING to ACTIVE."""
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

        # Initially in GREETING
        assert ctx.phase == ConversationPhase.GREETING

        # Add a user message
        ctx.add_message("user", "Hello")

        # Should be ready to transition to ACTIVE
        assert engine._should_transition_to_active() is True

        # Perform transition
        ctx.set_phase(ConversationPhase.ACTIVE)
        assert ctx.phase == ConversationPhase.ACTIVE


class TestErrorHandling:
    """Test error handling and fallback responses."""

    def test_fallback_response_on_error(self) -> None:
        """Test fallback response when conversation engine fails."""
        config = ConversationEngineConfig(
            fallback_response="I'm having trouble right now."
        )
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

        # Verify fallback response is configured
        assert engine.config.fallback_response == "I'm having trouble right now."


class TestPerformanceMetrics:
    """Test AC-009: Performance characteristics."""

    def test_context_operation_performance(self) -> None:
        """Test that context operations complete quickly."""
        import time

        ctx = ConversationContext(max_history=100)

        # Add messages and measure time
        start = time.time()
        for i in range(100):
            ctx.add_message("user" if i % 2 == 0 else "assistant", f"Message {i}")
        add_time = (time.time() - start) * 1000  # ms

        # Measure get_history
        start = time.time()
        for _ in range(100):
            ctx.get_history()
        get_time = (time.time() - start) / 100 * 1000  # ms per operation

        # Measure format_for_llm
        start = time.time()
        for _ in range(100):
            ctx.format_for_llm()
        format_time = (time.time() - start) / 100 * 1000  # ms per operation

        # All operations should be fast
        assert add_time < 50  # 50ms for 100 adds
        assert get_time < 10  # <10ms per get
        assert format_time < 10  # <10ms per format


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_history_handling(self) -> None:
        """Test handling of empty conversation history."""
        ctx = ConversationContext()

        history = ctx.get_history()
        assert history == []

        formatted = ctx.format_for_llm()
        assert formatted == []

    def test_single_message_history(self) -> None:
        """Test handling of single message."""
        ctx = ConversationContext()
        ctx.add_message("user", "Hello")

        history = ctx.get_history()
        assert len(history) == 1

        formatted = ctx.format_for_llm()
        assert len(formatted) == 1

    def test_very_long_message(self) -> None:
        """Test handling of very long messages."""
        ctx = ConversationContext()
        long_text = "x" * 10000  # 10KB message

        ctx.add_message("user", long_text)
        history = ctx.get_history()

        assert history[0].content == long_text

    def test_special_characters_in_messages(self) -> None:
        """Test handling of special characters."""
        ctx = ConversationContext()
        special_text = "Hello! How are you? 👋 #awesome @mention $100"

        ctx.add_message("user", special_text)
        history = ctx.get_history()

        assert history[0].content == special_text

    def test_maximum_participant_count(self) -> None:
        """Test handling of many participants."""
        ctx = ConversationContext()
        manager = ParticipantManager(ctx)

        # Add 100 participants
        for i in range(100):
            manager.add_participant(f"user-{i}", f"User {i}")

        # Verify all are active
        active = manager.get_active_participants()
        assert len(active) == 100
