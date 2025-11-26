#!/usr/bin/env python3
"""Run Nora Voice Agent with LiveKit.

This script creates a fully functional voice agent that:
1. Connects to a LiveKit room
2. Listens to participant audio (your microphone)
3. Transcribes speech using Deepgram STT
4. Generates responses with OpenAI LLM
5. Speaks back using Cartesia TTS

Usage:
    # Start in development mode (uses LiveKit playground)
    python scripts/run_voice_agent.py dev

    # Production mode
    python scripts/run_voice_agent.py start

Requirements:
    - LiveKit Cloud account (free tier works)
    - Deepgram API key
    - Cartesia API key
    - OpenAI API key for intelligent responses
"""

import logging
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dotenv import load_dotenv

from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    WorkerOptions,
    cli,
    function_tool,
    RunContext,
)
import livekit.plugins.deepgram as deepgram
import livekit.plugins.cartesia as cartesia
import livekit.plugins.silero as silero
import livekit.plugins.openai as openai

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("nora-agent")


# Optional: Define custom tools for the agent
@function_tool
async def get_current_time(context: RunContext) -> str:
    """Get the current time."""
    from datetime import datetime
    return f"The current time is {datetime.now().strftime('%I:%M %p')}"


@function_tool
async def get_date(context: RunContext) -> str:
    """Get today's date."""
    from datetime import datetime
    return f"Today is {datetime.now().strftime('%A, %B %d, %Y')}"


async def entrypoint(ctx: JobContext):
    """Main entry point for the voice agent.

    This function is called when the agent joins a room.

    Args:
        ctx: LiveKit job context with room connection
    """
    logger.info(f"Agent starting, waiting for room connection...")

    # Connect to the room
    await ctx.connect()

    logger.info(f"Connected to room: {ctx.room.name}")

    # Create the agent with instructions
    agent = Agent(
        instructions="""You are Nora, a friendly and helpful voice assistant.

Key behaviors:
- Keep responses brief and conversational (1-2 sentences when possible)
- Speak naturally as if having a phone conversation
- Be warm and personable
- If asked about your capabilities, mention you can help with general questions, tell the time and date
- If you don't know something, be honest about it

Remember: You're having a voice conversation, so avoid long lists or complex explanations.""",
        tools=[get_current_time, get_date],
    )

    # Create the agent session with STT, LLM, TTS, and VAD
    session = AgentSession(
        vad=silero.VAD.load(),
        stt=deepgram.STT(
            model="nova-2",
            language="en-US",
        ),
        llm=openai.LLM(
            model="gpt-4o-mini",
            temperature=0.7,
        ),
        tts=cartesia.TTS(
            voice="79a125e8-cd45-4c13-8a67-188112f4dd22",  # Default Cartesia voice
        ),
    )

    # Start the session
    await session.start(agent=agent, room=ctx.room)

    # Generate initial greeting
    await session.generate_reply(
        instructions="Greet the user warmly. Introduce yourself as Nora and ask how you can help them today."
    )

    logger.info("Voice assistant is running. Speak to interact!")


def main():
    """Run the voice agent."""
    print("\n" + "=" * 60)
    print("  NORA VOICE AGENT - LiveKit Test")
    print("=" * 60)

    # Check required environment variables
    required_vars = {
        "LIVEKIT_URL": os.getenv("LIVEKIT_URL"),
        "LIVEKIT_API_KEY": os.getenv("LIVEKIT_API_KEY"),
        "LIVEKIT_API_SECRET": os.getenv("LIVEKIT_API_SECRET"),
        "DEEPGRAM_API_KEY": os.getenv("DEEPGRAM_API_KEY"),
        "CARTESIA_API_KEY": os.getenv("CARTESIA_API_KEY"),
        "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
    }

    missing = [k for k, v in required_vars.items() if not v]

    if missing:
        print("\n[ERROR] Missing required environment variables:")
        for var in missing:
            print(f"  - {var}")
        print("\nPlease set these in your .env file.")
        print("\nExample .env file:")
        print("-" * 40)
        print("LIVEKIT_URL=wss://your-project.livekit.cloud")
        print("LIVEKIT_API_KEY=your_api_key")
        print("LIVEKIT_API_SECRET=your_api_secret")
        print("DEEPGRAM_API_KEY=your_deepgram_key")
        print("CARTESIA_API_KEY=your_cartesia_key")
        print("OPENAI_API_KEY=your_openai_key")
        print("-" * 40)
        sys.exit(1)

    # Show configuration
    print("\nConfiguration:")
    print(f"  LiveKit URL: {required_vars['LIVEKIT_URL']}")
    print(f"  Deepgram: ✓ Configured")
    print(f"  Cartesia: ✓ Configured")
    print(f"  OpenAI: ✓ Configured")

    print("\n" + "-" * 60)
    print("Starting agent...")
    print("To test: Open https://agents-playground.livekit.io")
    print("Configure your LiveKit credentials and connect!")
    print("-" * 60 + "\n")

    # Run the agent
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
        ),
    )


if __name__ == "__main__":
    main()
