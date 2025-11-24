"""Tests for TransferHandler."""

import pytest

from src.agents import BaseAgent, TransferHandler
from tests.mocks import MockLLMClient


class TestAgent(BaseAgent):
    """Test implementation of BaseAgent."""

    async def process_transfer(self, context: dict) -> None:
        """Process transfer."""
        if "conversation_history" in context:
            self._conversation_history = context["conversation_history"]


class TestTransferHandler:
    """Test TransferHandler context preservation."""

    @pytest.mark.asyncio
    async def test_prepare_context(self):
        """Test preparing transfer context."""
        llm = MockLLMClient()
        agent = TestAgent(
            name="agent1",
            llm_client=llm,
            system_prompt="System prompt",
        )

        agent.add_message_to_history("user", "Hello")
        agent.add_message_to_history("assistant", "Hi")

        context = await TransferHandler.prepare_context(agent)

        assert context["agent_name"] == "agent1"
        assert context["system_prompt"] == "System prompt"
        assert len(context["conversation_history"]) == 2

    @pytest.mark.asyncio
    async def test_execute_transfer(self):
        """Test executing transfer between agents."""
        llm1 = MockLLMClient()
        llm2 = MockLLMClient()

        agent1 = TestAgent(name="agent1", llm_client=llm1, system_prompt="Prompt 1")
        agent2 = TestAgent(name="agent2", llm_client=llm2, system_prompt="Prompt 2")

        # Add conversation to source agent
        agent1.add_message_to_history("user", "Hello")
        agent1.add_message_to_history("assistant", "Hi there")

        # Execute transfer
        await TransferHandler.execute_transfer(agent1, agent2)

        # Verify target agent has the conversation
        history = agent2.get_conversation_history()
        assert len(history) == 2
        assert history[0]["content"] == "Hello"
        assert history[1]["content"] == "Hi there"

    @pytest.mark.asyncio
    async def test_verify_context_integrity(self):
        """Test context integrity verification."""
        llm1 = MockLLMClient()
        llm2 = MockLLMClient()

        agent1 = TestAgent(name="agent1", llm_client=llm1, system_prompt="P1")
        agent2 = TestAgent(name="agent2", llm_client=llm2, system_prompt="P2")

        # Setup conversation
        agent1.add_message_to_history("user", "Test")
        agent1.add_message_to_history("assistant", "Response")

        # Transfer
        await TransferHandler.execute_transfer(agent1, agent2)

        # Verify integrity
        is_valid = await TransferHandler.verify_context(agent1, agent2)
        assert is_valid is True

    @pytest.mark.asyncio
    async def test_verify_context_failure_missing_messages(self):
        """Test context verification fails with missing messages."""
        llm1 = MockLLMClient()
        llm2 = MockLLMClient()

        agent1 = TestAgent(name="agent1", llm_client=llm1, system_prompt="P1")
        agent2 = TestAgent(name="agent2", llm_client=llm2, system_prompt="P2")

        # Setup conversation in source
        agent1.add_message_to_history("user", "Message 1")
        agent1.add_message_to_history("assistant", "Response 1")

        # Setup incomplete conversation in target
        agent2.add_message_to_history("user", "Message 1")

        # Verify should fail
        is_valid = await TransferHandler.verify_context(agent1, agent2)
        assert is_valid is False

    @pytest.mark.asyncio
    async def test_full_transfer_workflow(self):
        """Test complete transfer workflow."""
        llm1 = MockLLMClient(responses=["Greeter response"])
        llm2 = MockLLMClient(responses=["Triage response"])

        agent1 = TestAgent(name="greeter", llm_client=llm1, system_prompt="Greet")
        agent2 = TestAgent(name="triage", llm_client=llm2, system_prompt="Assess")

        # Simulate conversation
        response1 = await agent1.on_message("Hello")
        assert response1 == "Greeter response"

        # Transfer to agent 2
        await TransferHandler.execute_transfer(agent1, agent2)

        # Agent 2 continues conversation
        response2 = await agent2.on_message("What's wrong?")
        assert response2 == "Triage response"

        # Verify full history
        history = agent2.get_conversation_history()
        assert len(history) == 4  # 2 from transfer + 2 from agent2
        assert history[0]["content"] == "Hello"
        assert history[1]["content"] == "Greeter response"
