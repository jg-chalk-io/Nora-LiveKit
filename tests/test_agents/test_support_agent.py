"""Tests for SupportAgent."""

import pytest

from src.agents import SupportAgent
from tests.mocks import MockLLMClient


class TestSupportAgent:
    """Test SupportAgent functionality."""

    def test_support_initialization(self):
        """Test support agent initialization."""
        llm = MockLLMClient()
        agent = SupportAgent(llm_client=llm)
        assert agent.name == "support"

    @pytest.mark.asyncio
    async def test_support_medical_keyword_detection(self):
        """Test medical keyword detection triggers transfer."""
        llm = MockLLMClient(responses=["Response"])
        agent = SupportAgent(llm_client=llm)

        # Add user message with medical keyword
        agent.add_message_to_history("user", "What is this pain about?")

        should_transfer, target = await agent.should_transfer()
        assert should_transfer is True
        assert target == "triage"

    @pytest.mark.asyncio
    async def test_support_no_transfer_without_medical_keyword(self):
        """Test no transfer without medical keywords."""
        llm = MockLLMClient(responses=["Response"])
        agent = SupportAgent(llm_client=llm)

        agent.add_message_to_history("user", "What times are you open?")
        agent.add_message_to_history("assistant", "We're open 9-5")

        should_transfer, target = await agent.should_transfer()
        assert should_transfer is False

    @pytest.mark.asyncio
    async def test_support_all_medical_keywords(self):
        """Test all medical keywords trigger transfer."""
        medical_keywords = ["symptom", "diagnosis", "treatment", "medication", "pain"]

        for keyword in medical_keywords:
            llm = MockLLMClient()
            agent = SupportAgent(llm_client=llm)
            agent.add_message_to_history("user", f"I have a {keyword} question")

            should_transfer, target = await agent.should_transfer()
            assert should_transfer is True, f"Failed for keyword: {keyword}"
            assert target == "triage"

    @pytest.mark.asyncio
    async def test_support_process_transfer(self):
        """Test support process transfer."""
        llm = MockLLMClient()
        agent = SupportAgent(llm_client=llm)

        context = {
            "agent_name": "triage",
            "conversation_history": [
                {"role": "user", "content": "I need an appointment"},
                {"role": "assistant", "content": "Let me schedule that"},
            ],
        }

        await agent.process_transfer(context)
        history = agent.get_conversation_history()
        assert len(history) == 2

    @pytest.mark.asyncio
    async def test_support_available_services(self):
        """Test support agent has available services."""
        llm = MockLLMClient()
        agent = SupportAgent(llm_client=llm)

        assert "appointment_scheduling" in agent._available_services
        assert "billing_inquiry" in agent._available_services
        assert "prescription_refill" in agent._available_services
        assert "office_information" in agent._available_services
