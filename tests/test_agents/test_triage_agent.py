"""Tests for TriageAgent."""

import pytest

from src.agents import TriageAgent
from tests.mocks import MockLLMClient


class TestTriageAgent:
    """Test TriageAgent functionality."""

    def test_triage_initialization(self):
        """Test triage agent initialization."""
        llm = MockLLMClient()
        agent = TriageAgent(llm_client=llm)
        assert agent.name == "triage"

    @pytest.mark.asyncio
    async def test_triage_support_keyword_detection(self):
        """Test support keyword detection."""
        llm = MockLLMClient(responses=["Response"])
        agent = TriageAgent(llm_client=llm)

        # Add message with support keyword
        agent.add_message_to_history("user", "I need to schedule an appointment")
        agent.add_message_to_history("assistant", "Let me help with that")

        should_transfer, target = await agent.should_transfer()
        assert should_transfer is True
        assert target == "support"

    @pytest.mark.asyncio
    async def test_triage_no_transfer_without_keyword(self):
        """Test no transfer without support keywords."""
        llm = MockLLMClient(responses=["Response"])
        agent = TriageAgent(llm_client=llm)

        agent.add_message_to_history("user", "How long does it take to recover?")
        agent.add_message_to_history("assistant", "Recovery takes about 2 weeks")

        should_transfer, target = await agent.should_transfer()
        assert should_transfer is False

    @pytest.mark.asyncio
    async def test_triage_all_support_keywords(self):
        """Test all support keywords trigger transfer."""
        support_keywords = ["schedule", "appointment", "billing", "prescription", "refill"]

        for keyword in support_keywords:
            llm = MockLLMClient()
            agent = TriageAgent(llm_client=llm)
            agent.add_message_to_history("user", f"I need to {keyword}")

            should_transfer, target = await agent.should_transfer()
            assert should_transfer is True, f"Failed for keyword: {keyword}"
            assert target == "support"

    @pytest.mark.asyncio
    async def test_triage_process_transfer(self):
        """Test triage process transfer."""
        llm = MockLLMClient()
        agent = TriageAgent(llm_client=llm)

        context = {
            "agent_name": "greeter",
            "conversation_history": [
                {"role": "user", "content": "I have chest pain"},
                {"role": "assistant", "content": "Let me assess"},
            ],
        }

        await agent.process_transfer(context)
        history = agent.get_conversation_history()
        assert len(history) == 2
        assert history[0]["content"] == "I have chest pain"
