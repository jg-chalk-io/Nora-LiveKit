"""Main entry point for Nora LiveKit Agent."""

import asyncio
import threading

import uvicorn
from dotenv import load_dotenv

from .agent import NoraAgent
from .config import Config, setup_logging
from .server import app

# Load environment variables from .env file
load_dotenv()


def run_health_server(port: int) -> None:
    """Run FastAPI health check server in background thread.

    Args:
        port: Port to listen on for health checks
    """
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="warning",
    )


async def main() -> None:
    """Main agent entry point."""
    # Load configuration from environment
    config = Config.from_env()
    setup_logging(config)

    # Start health check server in background thread
    health_thread = threading.Thread(
        target=run_health_server,
        args=(config.health_check_port,),
        daemon=True,
    )
    health_thread.start()

    # Create and start agent
    agent = NoraAgent(config)
    await agent.start()

    # Wait for shutdown signal
    await agent._shutdown_event.wait()

    # Clean shutdown
    await agent.stop()


if __name__ == "__main__":
    asyncio.run(main())
