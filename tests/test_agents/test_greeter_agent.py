"""Tests for GreeterAgent."""

import pytest

from src.agents import GreeterAgent
from tests.mocks import MockLLMClient


class TestGreeterAgent:
    """Test GreeterAgent functionality."""

    def test_greeter_initialization(self):
        """Test greeter agent initialization."""
        llm = MockLLMClient()
        agent = GreeterAgent(llm_client=llm)
        assert agent.name == "greeter"

    @pytest.mark.asyncio
    async def test_greeter_urgent_keyword_detection(self):
        """Test urgent keyword detection."""
        llm = MockLLMClient(responses=["Response"])
        agent = GreeterAgent(llm_client=llm)

        # Add urgent message to history
        agent.add_message_to_history("user", "I have chest pain")
        agent.add_message_to_history("assistant", "Please describe your symptoms")

        should_transfer, target = await agent.should_transfer()
        assert should_transfer is True
        assert target == "triage"

    @pytest.mark.asyncio
    async def test_greeter_no_urgent_keyword(self):
        """Test no transfer without urgent keywords."""
        llm = MockLLMClient(responses=["Response"])
        agent = GreeterAgent(llm_client=llm)

        agent.add_message_to_history("user", "I'd like to schedule an appointment")
        agent.add_message_to_history("assistant", "Of course, let me help with that")

        should_transfer, target = await agent.should_transfer()
        assert should_transfer is False

    @pytest.mark.asyncio
    async def test_greeter_emergency_keyword(self):
        """Test transfer on emergency keyword."""
        llm = MockLLMClient()
        agent = GreeterAgent(llm_client=llm)

        agent.add_message_to_history("user", "This is an emergency!")
        should_transfer, target = await agent.should_transfer()
        assert should_transfer is True
        assert target == "triage"

    @pytest.mark.asyncio
    async def test_greeter_all_urgent_keywords(self):
        """Test all urgent keywords trigger transfer."""
        urgent_keywords = [
            "emergency",
            "urgent",
            "pain",
            "bleeding",
            "difficulty breathing",
            "chest pain",
            "severe",
            "critical",
            "serious",
        ]

        for keyword in urgent_keywords:
            llm = MockLLMClient()
            agent = GreeterAgent(llm_client=llm)
            agent.add_message_to_history("user", f"I have {keyword} symptoms")

            should_transfer, target = await agent.should_transfer()
            assert should_transfer is True, f"Failed for keyword: {keyword}"
            assert target == "triage"

    @pytest.mark.asyncio
    async def test_greeter_process_transfer(self):
        """Test greeter process transfer."""
        llm = MockLLMClient()
        agent = GreeterAgent(llm_client=llm)

        context = {
            "agent_name": "previous",
            "conversation_history": [
                {"role": "user", "content": "Hello"},
            ],
        }

        await agent.process_transfer(context)
        history = agent.get_conversation_history()
        assert len(history) == 1
