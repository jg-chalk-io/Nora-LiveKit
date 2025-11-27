"""Nora-specific LLM tools for LiveKit Agents.

Implements the core tools that Nora's workflow requires:
- transferFromAiTriageWithMetadata: Transfer to Vet Wise with full metadata
- collectNameNumberConcernPetName: Save non-urgent message
- queryCorpus: Look up pet breed/species information

Satisfies REQ-F-NORA-TOOLS-001 through REQ-F-NORA-TOOLS-004.
"""

from typing import Callable, Optional

import structlog

from ..data.pets_corpus_loader import get_pets_corpus

logger = structlog.get_logger(__name__)

# Type alias for tool result handlers
ToolResultHandler = Callable[[str, dict], None]


class NoraTools:
    """Nora-specific tools for conversation workflows.

    These tools are designed to be registered with LiveKit Agents
    and called by the LLM during conversation flow.

    Satisfies: REQ-F-NORA-TOOLS-001, REQ-F-NORA-TOOLS-002,
               REQ-F-NORA-TOOLS-003, REQ-F-NORA-TOOLS-004
    """

    def __init__(
        self,
        on_transfer: Optional[ToolResultHandler] = None,
        on_message_saved: Optional[ToolResultHandler] = None,
    ) -> None:
        """Initialize Nora tools with optional callbacks.

        Args:
            on_transfer: Callback when transfer is triggered
            on_message_saved: Callback when message is saved
        """
        self._on_transfer = on_transfer
        self._on_message_saved = on_message_saved

    async def transfer_from_ai_triage_with_metadata(
        self,
        callback_number: str,
        first_name: str,
        last_name: Optional[str] = None,
        pet_name: Optional[str] = None,
        age: Optional[str] = None,
        species: Optional[str] = None,
        breed: Optional[str] = None,
        urgency_reason: Optional[str] = None,
    ) -> str:
        """Transfer to Vet Wise with full metadata.

        This tool is called when the caller needs to be transferred
        to the 24/7 veterinary partner service.

        Satisfies: REQ-F-NORA-TOOLS-001, REQ-F-NORA-TOOLS-002

        Args:
            callback_number: Confirmed callback number
            first_name: Caller's first name
            last_name: Caller's last name (optional)
            pet_name: Pet's name (optional)
            age: Pet's age (optional)
            species: Pet species (optional)
            breed: Pet breed (optional)
            urgency_reason: Reason for urgent transfer (optional)

        Returns:
            Status message for the LLM
        """
        metadata = {
            "callback_number": callback_number,
            "first_name": first_name,
            "last_name": last_name,
            "pet_name": pet_name,
            "age": age,
            "species": species,
            "breed": breed,
            "urgency_reason": urgency_reason,
        }

        # Filter out None values for logging
        clean_metadata = {k: v for k, v in metadata.items() if v is not None}

        logger.info(
            "nora.tools.transfer_initiated",
            **clean_metadata,
        )

        # Call the transfer handler if provided
        if self._on_transfer:
            self._on_transfer("transferFromAiTriageWithMetadata", metadata)

        # In production, this would:
        # 1. Send metadata to webhook endpoint
        # 2. Initiate SIP transfer to Vet Wise
        # 3. Return status

        return "Transferred to Vet Wise"

    async def collect_name_number_concern_pet_name(
        self,
        callback_number: str,
        first_name: str,
        last_name: Optional[str] = None,
        pet_name: Optional[str] = None,
        concern_description: Optional[str] = None,
    ) -> str:
        """Save non-urgent message for office callback.

        This tool is called when the caller's request can wait
        for office staff to return the call.

        Satisfies: REQ-F-NORA-TOOLS-003, REQ-F-NORA-TOOLS-004

        Args:
            callback_number: Confirmed callback number
            first_name: Caller's first name
            last_name: Caller's last name (optional)
            pet_name: Pet's name (optional)
            concern_description: Detailed message/concern (optional)

        Returns:
            Status message for the LLM
        """
        message_data = {
            "callback_number": callback_number,
            "first_name": first_name,
            "last_name": last_name,
            "pet_name": pet_name,
            "concern_description": concern_description,
        }

        # Filter out None values for logging
        clean_data = {k: v for k, v in message_data.items() if v is not None}

        logger.info(
            "nora.tools.message_saved",
            **clean_data,
        )

        # Call the message handler if provided
        if self._on_message_saved:
            self._on_message_saved("collectNameNumberConcernPetName", message_data)

        # In production, this would:
        # 1. Save message to database/CRM
        # 2. Trigger notification to office staff
        # 3. Return status

        return "Message saved"

    async def query_corpus(self, breed_query: str) -> str:
        """Look up pet breed/species information from corpus.

        Searches the pets corpus for breed information based on the
        caller's description. Supports exact matches, common names
        (e.g., "Yorkie" → "Yorkshire Terrier"), and partial matches.

        Args:
            breed_query: Breed term from user (e.g., "Yorkie", "Lab", "Goldendoodle")

        Returns:
            JSON-formatted string with breed info:
            - If found: {"found": true, "species": "Dog", "breed": "Yorkshire Terrier", ...}
            - If not found: {"found": false}
        """
        import json

        corpus = get_pets_corpus()
        result = corpus.search(breed_query)

        logger.info(
            "nora.tools.query_corpus",
            query=breed_query,
            found=result.found,
            species=result.species,
            breed=result.breed,
            match_type=result.match_type,
        )

        return json.dumps(result.to_dict())


def get_tool_definitions() -> list[dict]:
    """Get OpenAI-compatible tool definitions for Nora tools.

    Returns tool schemas that can be passed to the LLM for function calling.

    Returns:
        List of tool definition dicts
    """
    return [
        {
            "type": "function",
            "function": {
                "name": "transferFromAiTriageWithMetadata",
                "description": "Transfer caller to Vet Wise (24/7 veterinary partner) with full metadata. Use for urgent situations requiring immediate live assistance.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "callback_number": {
                            "type": "string",
                            "description": "Confirmed callback phone number",
                        },
                        "first_name": {
                            "type": "string",
                            "description": "Caller's first name",
                        },
                        "last_name": {
                            "type": "string",
                            "description": "Caller's last name (optional)",
                        },
                        "pet_name": {
                            "type": "string",
                            "description": "Pet's name (optional)",
                        },
                        "age": {
                            "type": "string",
                            "description": "Pet's age (optional)",
                        },
                        "species": {
                            "type": "string",
                            "description": "Pet species like dog, cat (optional)",
                        },
                        "breed": {
                            "type": "string",
                            "description": "Pet breed (optional)",
                        },
                        "urgency_reason": {
                            "type": "string",
                            "description": "Reason for urgent transfer",
                        },
                    },
                    "required": ["callback_number", "first_name"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "collectNameNumberConcernPetName",
                "description": "Save non-urgent message for office staff callback. Use when caller's request can wait.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "callback_number": {
                            "type": "string",
                            "description": "Confirmed callback phone number",
                        },
                        "first_name": {
                            "type": "string",
                            "description": "Caller's first name",
                        },
                        "last_name": {
                            "type": "string",
                            "description": "Caller's last name (optional)",
                        },
                        "pet_name": {
                            "type": "string",
                            "description": "Pet's name (optional)",
                        },
                        "concern_description": {
                            "type": "string",
                            "description": "Detailed message/concern description",
                        },
                    },
                    "required": ["callback_number", "first_name"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "queryCorpus",
                "description": "Look up pet breed and species information. Use when caller mentions a breed name or nickname to determine the species (dog, cat, etc.). Supports common names like 'Yorkie' for Yorkshire Terrier, 'Lab' for Labrador Retriever.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "breed_query": {
                            "type": "string",
                            "description": "The breed name or nickname mentioned by caller (e.g., 'Yorkie', 'Lab', 'Goldendoodle', 'Maine Coon')",
                        },
                    },
                    "required": ["breed_query"],
                },
            },
        },
    ]
