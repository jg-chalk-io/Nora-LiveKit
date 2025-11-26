"""Main entry point for Nora LiveKit Agent.

This module provides the main entry point for running the agent as a module:
    python -m nora_livekit

Or via the installed script:
    nora-agent
"""

import asyncio
import signal
import sys
from typing import NoReturn

import structlog
from dotenv import load_dotenv

from nora_livekit.agent import NoraAgent
from nora_livekit.config import Config, setup_logging

logger = structlog.get_logger(__name__)


async def run() -> None:
    """Run the Nora LiveKit agent.

    This function:
    1. Loads configuration from environment
    2. Sets up structured logging
    3. Creates and starts the agent
    4. Waits for shutdown signal
    5. Stops the agent gracefully
    """
    # Load configuration
    logger.info("agent.initializing")
    config = Config.from_env()
    setup_logging(config)

    # Create agent
    agent = NoraAgent(config)

    # Set up signal handlers for graceful shutdown
    def signal_handler(sig: int) -> None:
        """Handle shutdown signals."""
        logger.info("agent.shutdown_signal_received", signal=sig)
        if agent._shutdown_event:
            agent._shutdown_event.set()

    signal.signal(signal.SIGINT, lambda s, f: signal_handler(s))
    signal.signal(signal.SIGTERM, lambda s, f: signal_handler(s))

    try:
        # Start agent
        await agent.start()

        # Wait for shutdown signal
        if agent._shutdown_event:
            await agent._shutdown_event.wait()
        else:
            # Fallback: wait indefinitely
            while agent.is_running:
                await asyncio.sleep(1)

    except KeyboardInterrupt:
        logger.info("agent.interrupted")
    except Exception as e:
        logger.error("agent.error", error=str(e), exc_info=True)
        raise
    finally:
        # Stop agent
        await agent.stop()
        logger.info("agent.shutdown_complete")


def main() -> NoReturn:
    """Main entry point for the agent.

    This is the entry point used by the installed script.
    """
    # Load environment variables from .env file
    load_dotenv()

    try:
        # Run the agent
        asyncio.run(run())
        sys.exit(0)
    except KeyboardInterrupt:
        logger.info("agent.interrupted_by_user")
        sys.exit(0)
    except Exception as e:
        logger.error("agent.fatal_error", error=str(e), exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
