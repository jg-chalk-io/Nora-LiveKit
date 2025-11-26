#!/usr/bin/env python3
"""Run Nora Voice Agent with LiveKit - Full Nora Veterinary Assistant.

This script creates Nora, the veterinary virtual assistant with:
1. Full nora.md system prompt (1180 lines of behavior rules)
2. Latency-optimized voice pipeline (sub-300ms target)
3. Proper tools (transferFromAiTriageWithMetadata, collectNameNumberConcernPetName)
4. Office configuration (name, hours, address, etc.)

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
    metrics,
    RunContext,
)
import livekit.plugins.deepgram as deepgram
import livekit.plugins.cartesia as cartesia
import livekit.plugins.silero as silero
import livekit.plugins.openai as openai

# CRITICAL: Import turn detector at MODULE LEVEL to register inference runner
# BEFORE Worker.__init__ is called. This must happen before cli.run_app().
from livekit.plugins.turn_detector.english import EnglishModel  # noqa: F401

# Turn detector - ENABLED with pre-downloaded models
USE_TURN_DETECTOR = True

# Load environment variables
load_dotenv()

# Langfuse observability
from nora_livekit.observability import init_langfuse, get_tracer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("nora-agent")


# =============================================================================
# NORA CONFIGURATION - Customize these for your veterinary clinic
# =============================================================================
OFFICE_NAME = os.getenv("OFFICE_NAME", "Humber Veterinary Clinic")
OFFICE_HOURS = os.getenv("OFFICE_HOURS", "Monday–Friday 8 AM–6 PM, Saturday 9 AM–2 PM")
OFFICE_ADDRESS = os.getenv("OFFICE_ADDRESS", "123 Humber Valley Blvd, Toronto, ON")
OFFICE_WEBSITE = os.getenv("OFFICE_WEBSITE", "https://humberveterinary.com")
OFFICE_PHONE = os.getenv("OFFICE_PHONE", "4165550198")

# Clinic open status - could be dynamic based on time, or set via env
IS_CLINIC_OPEN = os.getenv("IS_CLINIC_OPEN", "false").lower() == "true"

# =============================================================================
# CARTESIA VOICE CONFIGURATION
# Browse voices at: https://play.cartesia.ai/
# =============================================================================
# Popular Cartesia voice IDs:
#   - 79a125e8-cd45-4c13-8a67-188112f4dd22  (Default - warm female)
#   - a0e99841-07ec-4d8a-9de8-21bb41899c04  (British Female - professional)
#   - 5345cf08-6f37-424d-a5d9-8ae1f1e5d5a4  (American Female - friendly)
#   - 87748186-23bb-4158-a1eb-332911b0b708  (American Male - calm)
#   - 41534e16-2966-4c6b-9670-111411def906  (British Male - authoritative)
CARTESIA_VOICE_ID = os.getenv("CARTESIA_VOICE_ID", "79a125e8-cd45-4c13-8a67-188112f4dd22")
CARTESIA_SPEED = float(os.getenv("CARTESIA_SPEED", "1.0"))  # 0.5 to 2.0


def _load_nora_prompt() -> str:
    """Load and render the Nora system prompt from nora_system.md."""
    prompt_path = Path(__file__).parent.parent / "src" / "nora_livekit" / "prompts" / "nora_system.md"

    try:
        template = prompt_path.read_text()
    except FileNotFoundError:
        logger.warning(f"Nora prompt not found at {prompt_path}, using fallback")
        return _get_fallback_prompt()

    # Replace template variables
    prompt = template.replace("{{office_name}}", OFFICE_NAME)
    prompt = prompt.replace("{{is_the_clinic_open}}", "yes" if IS_CLINIC_OPEN else "no")
    prompt = prompt.replace("{{office_hours}}", OFFICE_HOURS)
    prompt = prompt.replace("{{hospital_address}}", OFFICE_ADDRESS)
    prompt = prompt.replace("{{office_website}}", OFFICE_WEBSITE)
    prompt = prompt.replace("{{office_phone}}", OFFICE_PHONE)

    # Caller phone will be dynamic per call, use placeholder
    prompt = prompt.replace("{{caller_phone_digits}}", "unknown")
    prompt = prompt.replace("{{caller_phone_number}}", "unknown")

    logger.info(f"Loaded Nora prompt ({len(template)} chars) for {OFFICE_NAME}")
    return prompt


def _get_fallback_prompt() -> str:
    """Minimal fallback prompt if main prompt fails to load."""
    return f"""You are Nora, the virtual assistant for {OFFICE_NAME}.

CRITICAL RULES:
1. Ask ONE question at a time and STOP after the question mark
2. Never ask for multiple pieces of information in a single question
3. If silence for 5 seconds, say "Are you still there?"
4. Never provide medical advice - transfer to Vet Wise instead

The clinic is currently {'open' if IS_CLINIC_OPEN else 'closed'}.
Hours: {OFFICE_HOURS}
Address: {OFFICE_ADDRESS}
"""


def _get_nora_greeting() -> str:
    """Get the proper Nora greeting based on clinic status."""
    if IS_CLINIC_OPEN:
        return (
            f"Thank you for calling {OFFICE_NAME}. "
            "We're currently open but assisting other callers. "
            "I'm Nora, the virtual assistant. How can I help you today?"
        )
    else:
        return (
            f"Thank you for calling {OFFICE_NAME}. "
            "The office is currently closed, but I'm Nora, "
            "the virtual assistant here to help. How can I assist you?"
        )


def _get_turn_detector():
    """Create turn detector instance at runtime."""
    from livekit.plugins.turn_detector.english import EnglishModel
    return EnglishModel()


def prewarm(proc: JobProcess):
    """Prewarm models during worker startup."""
    logger.info("Prewarming models...")

    # Preload VAD model (Silero)
    logger.info("  Loading Silero VAD...")
    proc.userdata["vad"] = silero.VAD.load()

    # Preload Nora system prompt
    logger.info("  Loading Nora system prompt...")
    proc.userdata["nora_prompt"] = _load_nora_prompt()

    # Initialize Langfuse observability
    logger.info("  Initializing Langfuse observability...")
    tracer = init_langfuse()
    proc.userdata["langfuse_enabled"] = tracer.enabled
    if tracer.enabled:
        logger.info("  ✓ Langfuse enabled")
    else:
        logger.info("  ○ Langfuse disabled (no API keys)")

    logger.info("Models prewarmed successfully!")


# =============================================================================
# NORA TOOLS - These match the exact signatures from nora.md
# =============================================================================
@function_tool
async def transferFromAiTriageWithMetadata(
    context: RunContext,
    callback_number: str,
    first_name: str,
    last_name: str = "",
    pet_name: str = "",
    age: str = "",
    species: str = "",
    breed: str = "",
    urgency_reason: str = "",
) -> str:
    """Transfer to Vet Wise with full metadata.

    Use this when the caller needs immediate live assistance from a
    registered veterinary technician.
    """
    logger.info(
        "TRANSFER TRIGGERED",
        extra={
            "callback_number": callback_number,
            "first_name": first_name,
            "last_name": last_name,
            "pet_name": pet_name,
            "urgency_reason": urgency_reason,
        }
    )
    # In production: trigger SIP transfer, webhook, etc.
    return "Transferred to Vet Wise"


@function_tool
async def collectNameNumberConcernPetName(
    context: RunContext,
    callback_number: str,
    first_name: str,
    last_name: str = "",
    pet_name: str = "",
    concern_description: str = "",
) -> str:
    """Save non-urgent message for office callback.

    Use this when the caller's request can wait for office staff
    to return the call.
    """
    logger.info(
        "MESSAGE SAVED",
        extra={
            "callback_number": callback_number,
            "first_name": first_name,
            "last_name": last_name,
            "pet_name": pet_name,
            "concern_description": concern_description,
        }
    )
    # In production: save to CRM, trigger notification, etc.
    return "Message saved"


@function_tool
async def hangUp(context: RunContext) -> str:
    """End the call."""
    logger.info("HANGUP TRIGGERED")
    # In production: trigger call termination
    return "Call ended"


async def entrypoint(ctx: JobContext):
    """Main entry point for the Nora voice agent."""
    logger.info("Nora agent starting...")

    # Connect to the room
    await ctx.connect()
    logger.info(f"Connected to room: {ctx.room.name}")

    # Start Langfuse conversation trace (non-fatal if it fails)
    try:
        tracer = get_tracer()
        if tracer and tracer.enabled:
            # Get caller identity from room participant if available
            caller_phone = ""
            for participant in ctx.room.remote_participants.values():
                caller_phone = participant.identity or ""
                break

            tracer.start_conversation(
                caller_phone=caller_phone,
                office_name=OFFICE_NAME,
                metadata={
                    "room_name": ctx.room.name,
                    "is_clinic_open": IS_CLINIC_OPEN,
                    "llm_model": os.getenv("LLM_MODEL", "gpt-4o-mini"),
                    "voice_id": CARTESIA_VOICE_ID[:8],
                },
            )
            logger.info("Langfuse trace started")
    except Exception as e:
        logger.warning(f"Langfuse tracing failed (non-fatal): {e}")

    # Get prewarmed Nora prompt
    nora_prompt = ctx.proc.userdata.get("nora_prompt", _get_fallback_prompt())

    # Create the Nora agent with full system prompt
    agent = Agent(
        instructions=nora_prompt,
        tools=[
            transferFromAiTriageWithMetadata,
            collectNameNumberConcernPetName,
            hangUp,
        ],
    )

    # Create the agent session with latency optimizations
    session = AgentSession(
        # VAD - prewarmed
        vad=ctx.proc.userdata["vad"],

        # STT - Deepgram Nova-3
        stt=deepgram.STT(
            model="nova-3",
            language="en",
        ),

        # LLM - OpenAI (gpt-4o-mini for speed, gpt-4o for quality)
        llm=openai.LLM(
            model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
            temperature=0.7,
        ),

        # TTS - Cartesia Sonic (configurable voice)
        tts=cartesia.TTS(
            voice=CARTESIA_VOICE_ID,
            speed=CARTESIA_SPEED,
        ),

        # Turn detection - English model
        turn_detection=_get_turn_detector() if USE_TURN_DETECTOR else None,

        # Endpointing delays
        min_endpointing_delay=0.3,
        max_endpointing_delay=1.5,

        # Enable preemptive generation
        preemptive_generation=True,

        # Interruption handling
        allow_interruptions=True,
        min_interruption_duration=0.5,
    )

    # Set up Langfuse metrics collection
    tracer = get_tracer()
    usage_collector = metrics.UsageCollector()

    @session.on("metrics_collected")
    def on_metrics_collected(ev):
        """Handle LiveKit metrics and send to Langfuse."""
        # Log metrics locally
        metrics.log_metrics(ev.metrics)

        # Accumulate for session summary
        usage_collector.collect(ev.metrics)

        # Send to Langfuse (non-fatal)
        try:
            if tracer and tracer.enabled:
                tracer.trace_metrics(ev.metrics)
        except Exception as e:
            logger.warning(f"Langfuse metrics failed: {e}")

    # Register shutdown callback to end Langfuse trace
    async def on_shutdown():
        """Clean up when session ends."""
        try:
            summary = usage_collector.get_summary()
            logger.info(f"Session usage summary: {summary}")

            if tracer and tracer.enabled:
                tracer.end_conversation(
                    outcome="completed",
                    metadata={"usage_summary": str(summary)},
                )
        except Exception as e:
            logger.warning(f"Langfuse shutdown failed: {e}")

    ctx.add_shutdown_callback(on_shutdown)

    # Start the session
    await session.start(agent=agent, room=ctx.room)

    # Generate the proper Nora greeting
    greeting = _get_nora_greeting()
    await session.generate_reply(instructions=f"Say exactly this: {greeting}")

    logger.info(f"Nora is running for {OFFICE_NAME}. Clinic open: {IS_CLINIC_OPEN}")


def main():
    """Run the Nora voice agent."""
    print("\n" + "=" * 60)
    print("  NORA VETERINARY ASSISTANT - LiveKit")
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
        sys.exit(1)

    # Show Nora configuration
    print(f"\nOffice Configuration:")
    print(f"  Name: {OFFICE_NAME}")
    print(f"  Hours: {OFFICE_HOURS}")
    print(f"  Address: {OFFICE_ADDRESS}")
    print(f"  Phone: {OFFICE_PHONE}")
    print(f"  Currently Open: {'YES' if IS_CLINIC_OPEN else 'NO'}")

    print("\nVoice Pipeline:")
    print(f"  STT: Deepgram Nova-3")
    print(f"  LLM: {os.getenv('LLM_MODEL', 'gpt-4o-mini')}")
    print(f"  TTS: Cartesia Sonic (voice: {CARTESIA_VOICE_ID[:8]}..., speed: {CARTESIA_SPEED})")
    print(f"  VAD: Silero (prewarmed)")
    print(f"  Turn Detection: {'Enabled' if USE_TURN_DETECTOR else 'Disabled'}")

    # Check Langfuse configuration
    langfuse_enabled = bool(os.getenv("LANGFUSE_PUBLIC_KEY"))
    print("\nObservability:")
    if langfuse_enabled:
        print(f"  Langfuse: ✓ Enabled")
        print(f"    Host: {os.getenv('LANGFUSE_HOST', 'https://cloud.langfuse.com')}")
    else:
        print("  Langfuse: ○ Disabled (set LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY)")

    print("\nNora Tools:")
    print("  ✓ transferFromAiTriageWithMetadata")
    print("  ✓ collectNameNumberConcernPetName")
    print("  ✓ hangUp")

    print("\n" + "-" * 60)
    print("Starting Nora with full veterinary assistant prompt...")
    print("To test: Open https://agents-playground.livekit.io")
    print("-" * 60 + "\n")

    # Run the agent
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            prewarm_fnc=prewarm,
            num_idle_processes=1,
            job_memory_warn_mb=300,
        ),
    )


if __name__ == "__main__":
    main()
