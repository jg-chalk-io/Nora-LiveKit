"""Transfer handler for context preservation."""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class TransferHandler:
    """Handles agent-to-agent transfers with context preservation."""

    @staticmethod
    async def prepare_context(agent: "BaseAgent") -> dict:
        """Prepare context for agent transfer.

        Args:
            agent: Agent to transfer from

        Returns:
            Context dict with full conversation state
        """
        context = {
            "agent_name": agent.name,
            "conversation_history": agent.get_conversation_history(),
            "system_prompt": agent.system_prompt,
        }
        logger.info(f"Prepared transfer context from {agent.name}")
        return context

    @staticmethod
    async def execute_transfer(
        source_agent: "BaseAgent", target_agent: "BaseAgent"
    ) -> None:
        """Execute transfer between agents.

        Args:
            source_agent: Agent initiating transfer
            target_agent: Agent receiving transfer
        """
        context = await TransferHandler.prepare_context(source_agent)
        await target_agent.process_transfer(context)
        logger.info(f"Transfer executed: {source_agent.name} -> {target_agent.name}")

    @staticmethod
    async def verify_context(
        source_agent: "BaseAgent", target_agent: "BaseAgent"
    ) -> bool:
        """Verify context integrity after transfer.

        Args:
            source_agent: Original agent
            target_agent: Target agent

        Returns:
            True if context preserved correctly
        """
        source_history = source_agent.get_conversation_history()
        target_history = target_agent.get_conversation_history()

        # Verify that target has at least the source history
        if len(target_history) < len(source_history):
            logger.error("Context integrity check failed: target history shorter")
            return False

        # Verify that messages match
        for i, source_msg in enumerate(source_history):
            if target_history[i] != source_msg:
                logger.error(f"Context integrity check failed at message {i}")
                return False

        logger.info("Context integrity verified")
        return True
