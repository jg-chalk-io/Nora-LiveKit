"""Greeter agent for initial contact."""

import logging

from .base_agent import BaseAgent

logger = logging.getLogger(__name__)

DEFAULT_GREETER_PROMPT = """You are a friendly and professional medical office greeter.
Your role is to:
1. Welcome the caller warmly
2. Identify their initial needs (appointment, urgent issue, general inquiry, etc.)
3. Determine if they need to be transferred to the triage agent for urgent matters
4. Keep responses brief and professional

Transfer to triage agent if the caller mentions: emergency, urgent, pain, bleeding, difficulty breathing, chest pain, or other critical health issues.
Otherwise, gather their basic information and needs."""


class GreeterAgent(BaseAgent):
    """Agent for greeting and initial needs assessment."""

    def __init__(self, llm_client, system_prompt: str | None = None):
        """Initialize greeter agent.

        Args:
            llm_client: LLM client for generation
            system_prompt: Optional custom system prompt
        """
        super().__init__(
            name="greeter",
            llm_client=llm_client,
            system_prompt=system_prompt or DEFAULT_GREETER_PROMPT,
        )
        self._urgent_keywords = [
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

    async def should_transfer(self) -> tuple[bool, str | None]:
        """Determine if transfer to triage is needed.

        Returns:
            Tuple of (should_transfer, target_agent_name)
        """
        if not self._conversation_history:
            return False, None

        # Check all user messages for urgent keywords
        for message in self._conversation_history:
            if message.get("role") == "user":
                message_text = message.get("content", "").lower()
                for keyword in self._urgent_keywords:
                    if keyword in message_text:
                        logger.info(f"Urgent keyword detected: {keyword}")
                        return True, "triage"

        return False, None

    async def process_transfer(self, context: dict) -> None:
        """Handle receiving a transfer from another agent.

        Args:
            context: Transferred context from previous agent
        """
        # Greeter typically doesn't receive transfers, but handle gracefully
        logger.info(f"Greeter received transfer context: {context.get('agent_name')}")
        # Inherit conversation history if provided
        if "conversation_history" in context:
            self._conversation_history = context["conversation_history"]
