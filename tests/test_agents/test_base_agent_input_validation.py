"""Tests for input validation in BaseAgent."""

import pytest
from unittest.mock import AsyncMock
from src.agents.base_agent import BaseAgent
from tests.mocks import MockLLMClient


class ConcreteAgent(BaseAgent):
    """Concrete implementation of BaseAgent for testing."""

    async def process_transfer(self, context: dict) -> None:
        """Handle receiving a transfer from another agent."""
        pass


class TestBaseAgentInputValidation:
    """Test input validation in BaseAgent.on_message()."""

    @pytest.mark.asyncio
    async def test_on_message_with_valid_input(self):
        """Test on_message with valid input."""
        client = MockLLMClient(responses=["Test response"])
        agent = ConcreteAgent("test_agent", client, "You are a test agent")

        response = await agent.on_message("Hello, agent!")
        assert response == "Test response"
        assert len(agent.get_conversation_history()) == 2  # user message + assistant response

    @pytest.mark.asyncio
    async def test_on_message_with_empty_string(self):
        """Test on_message with empty string."""
        client = MockLLMClient(responses=["Response to empty"])
        agent = ConcreteAgent("test_agent", client, "You are a test agent")

        response = await agent.on_message("")
        assert response == "Response to empty"
        assert len(agent.get_conversation_history()) == 2

    @pytest.mark.asyncio
    async def test_on_message_with_special_characters(self):
        """Test on_message with special characters."""
        client = MockLLMClient(responses=["Response to special chars"])
        agent = ConcreteAgent("test_agent", client, "You are a test agent")

        special_input = "Hello!@#$%^&*()_+-=[]{}|;:,.<>?"
        response = await agent.on_message(special_input)
        assert response == "Response to special chars"
        history = agent.get_conversation_history()
        assert history[-2]["content"] == special_input

    @pytest.mark.asyncio
    async def test_on_message_with_unicode(self):
        """Test on_message with Unicode characters."""
        client = MockLLMClient(responses=["Response to unicode"])
        agent = ConcreteAgent("test_agent", client, "You are a test agent")

        unicode_input = "Hello 世界 مرحبا Привет 🌍"
        response = await agent.on_message(unicode_input)
        assert response == "Response to unicode"
        history = agent.get_conversation_history()
        assert history[-2]["content"] == unicode_input

    @pytest.mark.asyncio
    async def test_on_message_with_very_long_input(self):
        """Test on_message with very long input."""
        client = MockLLMClient(responses=["Long response"])
        agent = ConcreteAgent("test_agent", client, "You are a test agent")

        long_input = "a" * 10000
        response = await agent.on_message(long_input)
        assert response == "Long response"
        history = agent.get_conversation_history()
        assert len(history[-2]["content"]) == 10000

    @pytest.mark.asyncio
    async def test_on_message_with_whitespace(self):
        """Test on_message with whitespace variations."""
        client = MockLLMClient(responses=["Response"])
        agent = ConcreteAgent("test_agent", client, "You are a test agent")

        # Test with only spaces
        response = await agent.on_message("   ")
        assert response == "Response"
        history = agent.get_conversation_history()
        assert history[-2]["content"] == "   "

    @pytest.mark.asyncio
    async def test_on_message_with_newlines(self):
        """Test on_message with newlines."""
        client = MockLLMClient(responses=["Response"])
        agent = ConcreteAgent("test_agent", client, "You are a test agent")

        multiline_input = "Hello\nWorld\nHow are you?"
        response = await agent.on_message(multiline_input)
        assert response == "Response"
        history = agent.get_conversation_history()
        assert history[-2]["content"] == multiline_input

    @pytest.mark.asyncio
    async def test_on_message_adds_to_history(self):
        """Test that on_message properly adds messages to history."""
        client = MockLLMClient(responses=["Response 1", "Response 2"])
        agent = ConcreteAgent("test_agent", client, "You are a test agent")

        await agent.on_message("First message")
        assert len(agent.get_conversation_history()) == 2
        assert agent.get_conversation_history()[-2]["role"] == "user"
        assert agent.get_conversation_history()[-1]["role"] == "assistant"

        await agent.on_message("Second message")
        assert len(agent.get_conversation_history()) == 4

    @pytest.mark.asyncio
    async def test_on_message_context_includes_system_prompt(self):
        """Test that context includes system prompt."""
        async_mock_client = AsyncMock()
        async_mock_client.generate = AsyncMock(return_value="Response")
        async_mock_client.name = "mock"
        async_mock_client.model = "mock-model"

        system_prompt = "You are a helpful assistant"
        agent = ConcreteAgent("test_agent", async_mock_client, system_prompt)

        await agent.on_message("Test message")

        # Verify that generate was called with context containing system prompt
        call_args = async_mock_client.generate.call_args
        context = call_args[0][1]  # Second argument is context
        assert len(context) > 0
        assert context[0]["role"] == "system"
        assert context[0]["content"] == system_prompt

    @pytest.mark.asyncio
    async def test_on_message_sequential_calls(self):
        """Test sequential on_message calls maintain history."""
        client = MockLLMClient(responses=["R1", "R2", "R3"])
        agent = ConcreteAgent("test_agent", client, "System prompt")

        await agent.on_message("Q1")
        await agent.on_message("Q2")
        await agent.on_message("Q3")

        history = agent.get_conversation_history()
        assert len(history) == 6  # 3 user messages + 3 assistant responses
        assert history[0]["content"] == "Q1"
        assert history[1]["content"] == "R1"
        assert history[2]["content"] == "Q2"
        assert history[3]["content"] == "R2"
        assert history[4]["content"] == "Q3"
        assert history[5]["content"] == "R3"

    @pytest.mark.asyncio
    async def test_on_message_with_json_like_string(self):
        """Test on_message with JSON-like string."""
        client = MockLLMClient(responses=["JSON response"])
        agent = ConcreteAgent("test_agent", client, "You are a test agent")

        json_input = '{"key": "value", "nested": {"data": 123}}'
        response = await agent.on_message(json_input)
        assert response == "JSON response"
        history = agent.get_conversation_history()
        assert history[-2]["content"] == json_input

    @pytest.mark.asyncio
    async def test_on_message_with_code_snippet(self):
        """Test on_message with code snippet."""
        client = MockLLMClient(responses=["Code response"])
        agent = ConcreteAgent("test_agent", client, "You are a test agent")

        code_input = """def hello():
    print("Hello, World!")
    return True
"""
        response = await agent.on_message(code_input)
        assert response == "Code response"
        history = agent.get_conversation_history()
        assert history[-2]["content"] == code_input

    @pytest.mark.asyncio
    async def test_on_message_adds_correct_role(self):
        """Test that on_message adds message with correct role."""
        client = MockLLMClient(responses=["Response"])
        agent = ConcreteAgent("test_agent", client, "System prompt")

        await agent.on_message("User input")

        history = agent.get_conversation_history()
        assert history[-2]["role"] == "user"
        assert history[-1]["role"] == "assistant"

    @pytest.mark.asyncio
    async def test_on_message_does_not_modify_input(self):
        """Test that on_message does not modify the input string."""
        client = MockLLMClient(responses=["Response"])
        agent = ConcreteAgent("test_agent", client, "System prompt")

        original_input = "  Test Message  \n"
        await agent.on_message(original_input)

        history = agent.get_conversation_history()
        stored_input = history[-2]["content"]
        assert stored_input == original_input

    @pytest.mark.asyncio
    async def test_on_message_multiple_consecutive_calls(self):
        """Test multiple consecutive on_message calls."""
        client = MockLLMClient(responses=["R1", "R2", "R3", "R4", "R5"])
        agent = ConcreteAgent("test_agent", client, "System prompt")

        for i in range(5):
            response = await agent.on_message(f"Message {i+1}")
            assert response == f"R{i+1}"

        history = agent.get_conversation_history()
        assert len(history) == 10  # 5 user + 5 assistant messages

    @pytest.mark.asyncio
    async def test_on_message_with_numeric_string(self):
        """Test on_message with numeric strings."""
        client = MockLLMClient(responses=["Numeric response"])
        agent = ConcreteAgent("test_agent", client, "System prompt")

        numeric_input = "12345.67890"
        response = await agent.on_message(numeric_input)
        assert response == "Numeric response"
        history = agent.get_conversation_history()
        assert history[-2]["content"] == numeric_input

    @pytest.mark.asyncio
    async def test_on_message_handles_api_error(self):
        """Test that on_message properly handles API errors."""
        client = MockLLMClient(failure_mode="api_error")
        agent = ConcreteAgent("test_agent", client, "System prompt")

        with pytest.raises(RuntimeError):
            await agent.on_message("This should fail")

    @pytest.mark.asyncio
    async def test_on_message_with_html_content(self):
        """Test on_message with HTML content."""
        client = MockLLMClient(responses=["HTML response"])
        agent = ConcreteAgent("test_agent", client, "System prompt")

        html_input = "<html><body><p>Hello World</p></body></html>"
        response = await agent.on_message(html_input)
        assert response == "HTML response"
        history = agent.get_conversation_history()
        assert history[-2]["content"] == html_input

    @pytest.mark.asyncio
    async def test_on_message_with_sql_like_string(self):
        """Test on_message with SQL-like string."""
        client = MockLLMClient(responses=["SQL response"])
        agent = ConcreteAgent("test_agent", client, "System prompt")

        sql_input = "SELECT * FROM users WHERE id = 1;"
        response = await agent.on_message(sql_input)
        assert response == "SQL response"
        history = agent.get_conversation_history()
        assert history[-2]["content"] == sql_input

    @pytest.mark.asyncio
    async def test_on_message_message_immutability(self):
        """Test that conversation history is not affected by external changes."""
        client = MockLLMClient(responses=["Response"])
        agent = ConcreteAgent("test_agent", client, "System prompt")

        test_input = "Original message"
        await agent.on_message(test_input)

        # Get history and verify content
        history1 = agent.get_conversation_history()
        original_message = history1[-2]["content"]

        # Verify the message is preserved
        assert original_message == test_input
