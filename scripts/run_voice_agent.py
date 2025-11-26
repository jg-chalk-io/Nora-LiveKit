#!/usr/bin/env python3
"""Run Nora Voice Agent with LiveKit - Latency Optimized.

This script creates a fully functional voice agent optimized for sub-300ms latency:
1. Prewarmed VAD model (eliminates cold-start latency)
2. English turn detector (predicts end-of-turn ~200-500ms faster)
3. Nova-3 STT (faster than nova-2)
4. Preemptive generation (starts LLM before user finishes)
5. Tuned endpointing delays
6. Interruption handling

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
    JobProcess,
    WorkerOptions,
    cli,
    function_tool,
    RunContext,
)
import livekit.plugins.deepgram as deepgram
import livekit.plugins.cartesia as cartesia
import livekit.plugins.silero as silero
import livekit.plugins.openai as openai

# Turn detector - DISABLED due to HuggingFace download issues in Railway
# The plugin can't download model files at runtime in containerized environments
# TODO: Re-enable once LiveKit fixes the download mechanism
USE_TURN_DETECTOR = False  # Hardcoded off - doesn't work in Railway

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("nora-agent")


def prewarm(proc: JobProcess):
    """Prewarm models during worker startup to eliminate cold-start latency.

    This function is called ONCE when the worker process starts, before any
    rooms are joined. Preloading models here saves ~200-400ms on first response.

    NOTE: Only VAD can be prewarmed. Turn detector must be created in entrypoint
    (it requires job context that doesn't exist during prewarm).
    """
    logger.info("Prewarming VAD model...")

    # Preload VAD model (Silero) - saves ~100-200ms
    proc.userdata["vad"] = silero.VAD.load()

    logger.info("VAD model prewarmed successfully!")


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
    Optimized for sub-300ms latency using Deepgram best practices.

    Args:
        ctx: LiveKit job context with room connection
    """
    logger.info(f"Agent starting, waiting for room connection...")

    # Connect to the room
    await ctx.connect()

    logger.info(f"Connected to room: {ctx.room.name}")

    # Create the agent with instructions optimized for voice
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

    # Create the agent session with LATENCY OPTIMIZATIONS
    # Reference: https://deepgram.com/learn/low-latency-voice-ai-and-how-to-achieve-it
    session = AgentSession(
        # =====================================================
        # VOICE ACTIVITY DETECTION (VAD)
        # Using prewarmed model to eliminate cold-start latency
        # =====================================================
        vad=ctx.proc.userdata["vad"],

        # =====================================================
        # SPEECH-TO-TEXT (STT) - Deepgram Nova-3
        # Nova-3 is newer/faster than Nova-2
        # Streaming STT processes audio as it arrives
        # =====================================================
        stt=deepgram.STT(
            model="nova-3",  # Upgraded from nova-2 for better speed
            language="en",   # Simplified language code
        ),

        # =====================================================
        # LARGE LANGUAGE MODEL (LLM) - OpenAI
        # gpt-4o-mini is optimized for speed while maintaining quality
        # =====================================================
        llm=openai.LLM(
            model="gpt-4o-mini",
            temperature=0.7,
        ),

        # =====================================================
        # TEXT-TO-SPEECH (TTS) - Cartesia Sonic
        # Cartesia streams audio back while generating
        # First syllable in ~150ms
        # =====================================================
        tts=cartesia.TTS(
            voice="79a125e8-cd45-4c13-8a67-188112f4dd22",  # Default Cartesia voice
        ),

        # =====================================================
        # TURN DETECTION - English Model (~10ms inference)
        # Predicts when user finished speaking BEFORE silence timeout
        # This is the #1 latency optimization (saves 200-500ms)
        # NOTE: Created here (not prewarmed) - requires job context
        # =====================================================
        turn_detection=_get_turn_detector() if USE_TURN_DETECTOR else None,

        # =====================================================
        # ENDPOINTING DELAYS - Tuned for responsiveness
        # min: minimum wait after predicted end-of-turn
        # max: maximum wait before forcing response
        # =====================================================
        min_endpointing_delay=0.3,  # 300ms minimum (default is higher)
        max_endpointing_delay=1.5,  # 1.5s maximum wait

        # =====================================================
        # PREEMPTIVE GENERATION - Start LLM early
        # Begins generating response before user fully finishes
        # Overlaps STT and LLM processing (parallel pipeline)
        # =====================================================
        preemptive_generation=True,

        # =====================================================
        # INTERRUPTION HANDLING - Natural conversation flow
        # =====================================================
        allow_interruptions=True,
        min_interruption_duration=0.5,  # 500ms to trigger interruption
    )

    # Start the session
    await session.start(agent=agent, room=ctx.room)

    # Generate initial greeting
    await session.generate_reply(
        instructions="Greet the user warmly. Introduce yourself as Nora and ask how you can help them today."
    )

    logger.info("Voice assistant is running with latency optimizations. Speak to interact!")


def main():
    """Run the voice agent."""
    print("\n" + "=" * 60)
    print("  NORA VOICE AGENT - LiveKit (Latency Optimized)")
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
    print(f"  Deepgram: ✓ Nova-3 (upgraded)")
    print(f"  Cartesia: ✓ Configured")
    print(f"  OpenAI: ✓ gpt-4o-mini")

    print("\nLatency Optimizations:")
    print("  ✓ VAD prewarming (Silero)")
    if USE_TURN_DETECTOR:
        print("  ✓ Turn detection (English model, created at runtime)")
    else:
        print("  ○ Turn detector DISABLED (set USE_TURN_DETECTOR=true to enable)")
    print("  ✓ Preemptive generation (parallel pipeline)")
    print("  ✓ Tuned endpointing (0.3s min, 1.5s max)")
    print("  ✓ Interruption handling enabled")

    print("\n" + "-" * 60)
    print("Starting agent with prewarmed models...")
    print("To test: Open https://agents-playground.livekit.io")
    print("Configure your LiveKit credentials and connect!")
    print("-" * 60 + "\n")

    # Run the agent with resource-optimized settings for Railway
    # Railway has limited resources - we minimize process usage
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            prewarm_fnc=prewarm,  # Prewarm models on worker startup
            # CRITICAL: Railway resource optimization
            # Default is min(cpu_count, 4) which overwhelms Railway's Hobby plan
            num_idle_processes=1,  # Only 1 idle process (default: 4 in prod)
            job_memory_warn_mb=300,  # Lower memory warning threshold
        ),
    )


if __name__ == "__main__":
    main()
