"""Tests for BaseAgent."""

import pytest

from src.agents import BaseAgent
from tests.mocks import MockLLMClient


class ConcreteAgent(BaseAgent):
    """Concrete implementation of BaseAgent for testing."""

    async def process_transfer(self, context: dict) -> None:
        """Process transfer."""
        if "conversation_history" in context:
            self._conversation_history = context["conversation_history"]


class TestBaseAgent:
    """Test BaseAgent functionality."""

    def test_agent_initialization(self):
        """Test agent initialization."""
        llm = MockLLMClient()
        agent = ConcreteAgent(
            name="test_agent",
            llm_client=llm,
            system_prompt="Test prompt",
        )
        assert agent.name == "test_agent"
        assert agent.system_prompt == "Test prompt"

    def test_agent_conversation_history(self):
        """Test agent conversation history management."""
        llm = MockLLMClient()
        agent = ConcreteAgent(name="test", llm_client=llm, system_prompt="Test")

        agent.add_message_to_history("user", "Hello")
        agent.add_message_to_history("assistant", "Hi there")

        history = agent.get_conversation_history()
        assert len(history) == 2
        assert history[0]["role"] == "user"
        assert history[0]["content"] == "Hello"
        assert history[1]["role"] == "assistant"

    def test_agent_clear_history(self):
        """Test clearing conversation history."""
        llm = MockLLMClient()
        agent = ConcreteAgent(name="test", llm_client=llm, system_prompt="Test")

        agent.add_message_to_history("user", "Hello")
        assert len(agent.get_conversation_history()) == 1

        agent.clear_history()
        assert len(agent.get_conversation_history()) == 0

    @pytest.mark.asyncio
    async def test_agent_on_message(self):
        """Test agent on_message method."""
        llm = MockLLMClient(responses=["Agent response"])
        agent = ConcreteAgent(
            name="test",
            llm_client=llm,
            system_prompt="You are helpful",
        )

        response = await agent.on_message("Hello")
        assert response == "Agent response"
        assert len(agent.get_conversation_history()) == 2

    @pytest.mark.asyncio
    async def test_agent_should_transfer_default(self):
        """Test should_transfer default behavior."""
        llm = MockLLMClient()
        agent = ConcreteAgent(name="test", llm_client=llm, system_prompt="Test")

        should_transfer, target = await agent.should_transfer()
        assert should_transfer is False
        assert target is None

    @pytest.mark.asyncio
    async def test_agent_prepare_transfer_context(self):
        """Test preparing transfer context."""
        llm = MockLLMClient()
        agent = ConcreteAgent(name="test", llm_client=llm, system_prompt="Test prompt")

        agent.add_message_to_history("user", "Hello")
        agent.add_message_to_history("assistant", "Hi")

        context = await agent.prepare_transfer_context()
        assert context["agent_name"] == "test"
        assert context["system_prompt"] == "Test prompt"
        assert len(context["conversation_history"]) == 2

    @pytest.mark.asyncio
    async def test_agent_process_transfer(self):
        """Test processing transfer."""
        llm = MockLLMClient()
        agent = ConcreteAgent(name="test", llm_client=llm, system_prompt="Test")

        # Agent starts with empty history
        assert len(agent.get_conversation_history()) == 0

        # Process transfer with context
        context = {
            "agent_name": "previous_agent",
            "conversation_history": [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi"},
            ],
        }

        await agent.process_transfer(context)

        # History is inherited from previous agent
        history = agent.get_conversation_history()
        assert len(history) == 2
        assert history[0]["content"] == "Hello"
