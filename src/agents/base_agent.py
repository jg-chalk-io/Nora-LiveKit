"""Base agent class with LiveKit integration support."""

import logging
from abc import ABC, abstractmethod
from typing import Any

from src.models import BaseLLMClient

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Abstract base class for all agents."""

    def __init__(
        self,
        name: str,
        llm_client: BaseLLMClient,
        system_prompt: str,
    ):
        """Initialize base agent.

        Args:
            name: Agent identifier
            llm_client: LLM client for generation
            system_prompt: System prompt for the agent
        """
        self._name = name
        self._llm_client = llm_client
        self._system_prompt = system_prompt
        self._conversation_history: list[dict] = []

    @property
    def name(self) -> str:
        """Return agent name."""
        return self._name

    @property
    def system_prompt(self) -> str:
        """Return system prompt."""
        return self._system_prompt

    def add_message_to_history(self, role: str, content: str) -> None:
        """Add message to conversation history.

        Args:
            role: Message role ('user' or 'assistant')
            content: Message content
        """
        self._conversation_history.append({"role": role, "content": content})

    def get_conversation_history(self) -> list[dict]:
        """Get full conversation history.

        Returns:
            List of message dicts with 'role' and 'content'
        """
        return self._conversation_history.copy()

    def clear_history(self) -> None:
        """Clear conversation history."""
        self._conversation_history = []

    async def on_message(self, message: str) -> str:
        """Process incoming message.

        Args:
            message: User message

        Returns:
            Agent response
        """
        self.add_message_to_history("user", message)

        # Prepare context with system prompt
        context = [{"role": "system", "content": self._system_prompt}]
        context.extend(self._conversation_history[:-1])  # All messages except last

        try:
            response = await self._llm_client.generate(message, context)
            self.add_message_to_history("assistant", response)
            return response
        except Exception as e:
            logger.error(f"Error in {self._name} on_message: {str(e)}")
            raise

    async def should_transfer(self) -> tuple[bool, str | None]:
        """Determine if conversation should be transferred.

        Returns:
            Tuple of (should_transfer, target_agent_name)
        """
        return False, None

    @abstractmethod
    async def process_transfer(self, context: dict) -> None:
        """Handle receiving a transfer from another agent.

        Args:
            context: Transferred context from previous agent
        """
        pass

    async def prepare_transfer_context(self) -> dict:
        """Prepare context for transfer to another agent.

        Returns:
            Context dict with conversation history and metadata
        """
        return {
            "agent_name": self._name,
            "conversation_history": self.get_conversation_history(),
            "system_prompt": self._system_prompt,
        }
