"""Tests for Nora LLM tools."""

import pytest
from unittest.mock import MagicMock

from nora_livekit.nora.tools import NoraTools, get_tool_definitions


class TestNoraTools:
    """Tests for NoraTools class."""

    @pytest.fixture
    def tools(self):
        """Create a NoraTools instance."""
        return NoraTools()

    @pytest.fixture
    def tools_with_callbacks(self):
        """Create NoraTools with mock callbacks."""
        on_transfer = MagicMock()
        on_message = MagicMock()
        return NoraTools(on_transfer=on_transfer, on_message_saved=on_message), on_transfer, on_message

    @pytest.mark.asyncio
    async def test_transfer_with_minimum_data(self, tools):
        """Test transfer with minimum required data."""
        result = await tools.transfer_from_ai_triage_with_metadata(
            callback_number="4165550198",
            first_name="John",
        )

        assert result == "Transferred to Vet Wise"

    @pytest.mark.asyncio
    async def test_transfer_with_full_data(self, tools):
        """Test transfer with all data fields."""
        result = await tools.transfer_from_ai_triage_with_metadata(
            callback_number="4165550198",
            first_name="John",
            last_name="Smith",
            pet_name="Max",
            age="3 years",
            species="dog",
            breed="Golden Retriever",
            urgency_reason="Hit by car",
        )

        assert result == "Transferred to Vet Wise"

    @pytest.mark.asyncio
    async def test_transfer_calls_callback(self, tools_with_callbacks):
        """Test that transfer calls the callback."""
        tools, on_transfer, _ = tools_with_callbacks

        await tools.transfer_from_ai_triage_with_metadata(
            callback_number="4165550198",
            first_name="John",
            urgency_reason="Emergency",
        )

        on_transfer.assert_called_once()
        call_args = on_transfer.call_args[0]
        assert call_args[0] == "transferFromAiTriageWithMetadata"
        assert call_args[1]["callback_number"] == "4165550198"
        assert call_args[1]["first_name"] == "John"

    @pytest.mark.asyncio
    async def test_collect_message_with_minimum_data(self, tools):
        """Test message collection with minimum data."""
        result = await tools.collect_name_number_concern_pet_name(
            callback_number="4165550198",
            first_name="John",
        )

        assert result == "Message saved"

    @pytest.mark.asyncio
    async def test_collect_message_with_full_data(self, tools):
        """Test message collection with all data."""
        result = await tools.collect_name_number_concern_pet_name(
            callback_number="4165550198",
            first_name="John",
            last_name="Smith",
            pet_name="Max",
            concern_description="Prescription refill for Heartgard medication",
        )

        assert result == "Message saved"

    @pytest.mark.asyncio
    async def test_collect_message_calls_callback(self, tools_with_callbacks):
        """Test that message collection calls the callback."""
        tools, _, on_message = tools_with_callbacks

        await tools.collect_name_number_concern_pet_name(
            callback_number="4165550198",
            first_name="John",
            concern_description="Routine checkup",
        )

        on_message.assert_called_once()
        call_args = on_message.call_args[0]
        assert call_args[0] == "collectNameNumberConcernPetName"
        assert call_args[1]["callback_number"] == "4165550198"


class TestToolDefinitions:
    """Tests for tool definition schema."""

    def test_get_tool_definitions_returns_list(self):
        """Test that get_tool_definitions returns a list."""
        definitions = get_tool_definitions()
        assert isinstance(definitions, list)
        assert len(definitions) == 2

    def test_transfer_tool_definition(self):
        """Test transfer tool definition schema."""
        definitions = get_tool_definitions()
        transfer_def = next(
            d for d in definitions
            if d["function"]["name"] == "transferFromAiTriageWithMetadata"
        )

        assert transfer_def["type"] == "function"
        params = transfer_def["function"]["parameters"]
        assert "callback_number" in params["properties"]
        assert "first_name" in params["properties"]
        assert "urgency_reason" in params["properties"]
        assert params["required"] == ["callback_number", "first_name"]

    def test_collect_message_tool_definition(self):
        """Test message collection tool definition schema."""
        definitions = get_tool_definitions()
        collect_def = next(
            d for d in definitions
            if d["function"]["name"] == "collectNameNumberConcernPetName"
        )

        assert collect_def["type"] == "function"
        params = collect_def["function"]["parameters"]
        assert "callback_number" in params["properties"]
        assert "first_name" in params["properties"]
        assert "concern_description" in params["properties"]
        assert params["required"] == ["callback_number", "first_name"]
