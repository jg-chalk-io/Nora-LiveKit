"""Triage agent for urgency assessment and routing."""

import logging

from .base_agent import BaseAgent

logger = logging.getLogger(__name__)

DEFAULT_TRIAGE_PROMPT = """You are a medical triage specialist at a healthcare facility.
Your role is to:
1. Assess the urgency and nature of the patient's condition
2. Determine if they need immediate emergency care or can be scheduled
3. Identify the appropriate department or specialist needed
4. Route to support agent for appointment scheduling, billing, or prescriptions
5. Ask clarifying questions to better understand the situation

Assess urgency level: Critical (immediate ER), High (same day), Medium (this week), Low (next week+)

Route to support agent if: caller needs appointment scheduling, billing information, or prescription refills."""


class TriageAgent(BaseAgent):
    """Agent for medical triage and routing."""

    def __init__(self, llm_client, system_prompt: str | None = None):
        """Initialize triage agent.

        Args:
            llm_client: LLM client for generation
            system_prompt: Optional custom system prompt
        """
        super().__init__(
            name="triage",
            llm_client=llm_client,
            system_prompt=system_prompt or DEFAULT_TRIAGE_PROMPT,
        )
        self._transfer_keywords = ["schedule", "appointment", "billing", "prescription", "refill"]

    async def should_transfer(self) -> tuple[bool, str | None]:
        """Determine if transfer to support agent is needed.

        Returns:
            Tuple of (should_transfer, target_agent_name)
        """
        if not self._conversation_history:
            return False, None

        # Check all user messages for support keywords
        for message in self._conversation_history:
            if message.get("role") == "user":
                message_text = message.get("content", "").lower()
                for keyword in self._transfer_keywords:
                    if keyword in message_text:
                        logger.info(f"Support keyword detected: {keyword}")
                        return True, "support"

        return False, None

    async def process_transfer(self, context: dict) -> None:
        """Handle receiving a transfer from another agent.

        Args:
            context: Transferred context from previous agent
        """
        # Inherit conversation history from previous agent
        if "conversation_history" in context:
            self._conversation_history = context["conversation_history"]
        logger.info(f"Triage received transfer from {context.get('agent_name')}")
