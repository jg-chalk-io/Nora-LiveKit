"""Integration tests for medical triage workflow."""

import pytest

from src.agents import GreeterAgent, TriageAgent, SupportAgent, TransferHandler
from src.models import LLMClientFactory
from tests.mocks import MockLLMClient


class TestMedicalTriageWorkflow:
    """Test complete medical triage workflow."""

    @pytest.mark.asyncio
    async def test_simple_greeting_workflow(self):
        """Test simple greeting without transfer."""
        llm = MockLLMClient(responses=["Welcome to the medical office"])
        greeter = GreeterAgent(llm_client=llm)

        response = await greeter.on_message("Hello")
        assert response == "Welcome to the medical office"

    @pytest.mark.asyncio
    async def test_urgent_case_transfer_workflow(self):
        """Test urgent case that transfers to triage."""
        llm_greeter = MockLLMClient(responses=["I'll connect you with our triage nurse"])
        llm_triage = MockLLMClient(responses=["Let me assess your condition"])

        greeter = GreeterAgent(llm_client=llm_greeter)
        triage = TriageAgent(llm_client=llm_triage)

        # Greeter interaction
        response1 = await greeter.on_message("I have chest pain")
        assert response1 == "I'll connect you with our triage nurse"

        # Detect need for transfer
        should_transfer, target = await greeter.should_transfer()
        assert should_transfer is True
        assert target == "triage"

        # Execute transfer
        await TransferHandler.execute_transfer(greeter, triage)

        # Triage continues conversation
        response2 = await triage.on_message("How long have you had the pain?")
        assert response2 == "Let me assess your condition"

        # Verify context preserved
        history = triage.get_conversation_history()
        assert len(history) == 4  # 2 from greeter + 2 from triage

    @pytest.mark.asyncio
    async def test_full_triage_to_support_workflow(self):
        """Test full workflow from greeter to triage to support."""
        llm_greeter = MockLLMClient(responses=["Connecting to triage"])
        llm_triage = MockLLMClient(responses=["I'll schedule that appointment"])
        llm_support = MockLLMClient(responses=["Your appointment is confirmed"])

        greeter = GreeterAgent(llm_client=llm_greeter)
        triage = TriageAgent(llm_client=llm_triage)
        support = SupportAgent(llm_client=llm_support)

        # Phase 1: Greeter
        r1 = await greeter.on_message("I have back pain")
        assert r1 == "Connecting to triage"

        should_transfer, target = await greeter.should_transfer()
        assert should_transfer is True

        # Phase 2: Transfer to Triage
        await TransferHandler.execute_transfer(greeter, triage)
        r2 = await triage.on_message("Can you schedule an appointment?")
        assert r2 == "I'll schedule that appointment"

        should_transfer, target = await triage.should_transfer()
        assert should_transfer is True
        assert target == "support"

        # Phase 3: Transfer to Support
        await TransferHandler.execute_transfer(triage, support)
        r3 = await support.on_message("Next available is Wednesday at 2pm")
        assert r3 == "Your appointment is confirmed"

        # Verify full history
        history = support.get_conversation_history()
        assert len(history) == 6  # 2 + 2 + 2

    @pytest.mark.asyncio
    async def test_factory_with_multiple_agents(self):
        """Test LLM factory with multiple agents."""
        # Factory with fallback
        primary_llm = MockLLMClient(name="primary", failure_mode="api_error")
        secondary_llm = MockLLMClient(name="secondary", responses=["Fallback response"])

        factory = LLMClientFactory([primary_llm, secondary_llm])

        greeter = GreeterAgent(llm_client=factory)

        # Response should come from fallback
        response = await greeter.on_message("Hello")
        assert response == "Fallback response"

    @pytest.mark.asyncio
    async def test_context_integrity_across_transfers(self):
        """Test that context is completely preserved across transfers."""
        llm_g = MockLLMClient(responses=["Greeter"])
        llm_t = MockLLMClient(responses=["Triage"])
        llm_s = MockLLMClient(responses=["Support"])

        greeter = GreeterAgent(llm_client=llm_g)
        triage = TriageAgent(llm_client=llm_t)
        support = SupportAgent(llm_client=llm_s)

        # Build conversation
        await greeter.on_message("User message 1")
        await TransferHandler.execute_transfer(greeter, triage)

        await triage.on_message("User message 2")
        await TransferHandler.execute_transfer(triage, support)

        await support.on_message("User message 3")

        # Verify all messages are preserved
        history = support.get_conversation_history()
        messages = [msg["content"] for msg in history if msg["role"] == "user"]
        assert "User message 1" in messages
        assert "User message 2" in messages
        assert "User message 3" in messages

    @pytest.mark.asyncio
    async def test_health_check_workflow(self):
        """Test health check across all providers."""
        client1 = MockLLMClient(name="openai")
        client2 = MockLLMClient(name="anthropic")
        client3 = MockLLMClient(name="google")

        factory = LLMClientFactory([client1, client2, client3])

        health = await factory.health_check()
        assert all(health.values())  # All should be healthy
        assert "openai" in health
        assert "anthropic" in health
        assert "google" in health
