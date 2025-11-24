"""Support agent for task execution."""

import logging

from .base_agent import BaseAgent

logger = logging.getLogger(__name__)

DEFAULT_SUPPORT_PROMPT = """You are a medical office support specialist.
Your role is to:
1. Schedule appointments for patients
2. Answer billing and insurance questions
3. Process prescription refill requests
4. Provide general office information
5. Redirect back to triage if medical questions arise

Be helpful, professional, and efficient.
For complex medical questions, recommend re-connecting with the triage agent."""


class SupportAgent(BaseAgent):
    """Agent for handling specific tasks (scheduling, billing, etc.)."""

    def __init__(self, llm_client, system_prompt: str | None = None):
        """Initialize support agent.

        Args:
            llm_client: LLM client for generation
            system_prompt: Optional custom system prompt
        """
        super().__init__(
            name="support",
            llm_client=llm_client,
            system_prompt=system_prompt or DEFAULT_SUPPORT_PROMPT,
        )
        self._available_services = [
            "appointment_scheduling",
            "billing_inquiry",
            "prescription_refill",
            "office_information",
        ]

    async def should_transfer(self) -> tuple[bool, str | None]:
        """Determine if transfer back to triage is needed.

        Returns:
            Tuple of (should_transfer, target_agent_name)
        """
        if not self._conversation_history:
            return False, None

        # Support doesn't typically transfer, but could escalate medical questions
        last_message = self._conversation_history[-1]
        if last_message.get("role") == "user":
            message_text = last_message.get("content", "").lower()
            # Medical keywords that should go back to triage
            medical_keywords = ["symptom", "diagnosis", "treatment", "medication", "pain"]
            for keyword in medical_keywords:
                if keyword in message_text:
                    logger.info(f"Medical keyword detected: {keyword}")
                    return True, "triage"

        return False, None

    async def process_transfer(self, context: dict) -> None:
        """Handle receiving a transfer from another agent.

        Args:
            context: Transferred context from previous agent
        """
        # Inherit conversation history from triage agent
        if "conversation_history" in context:
            self._conversation_history = context["conversation_history"]
        logger.info(f"Support received transfer from {context.get('agent_name')}")
