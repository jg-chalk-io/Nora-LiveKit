#!/usr/bin/env python3
"""Run Nora Voice Agent with LiveKit - Task-Based Workflow Architecture.

This script creates Nora, the veterinary virtual assistant with:
1. TASK-BASED WORKFLOWS for proper conversation flow:
   - GreeterAgent: Initial greeting and triage routing
   - UrgentTransferAgent: Uses CollectUrgentInfoTask for data collection
   - MessageFlowAgent: Uses CollectMessageInfoTask for callbacks
   - CriticalEmergencyAgent: Fastest path with CollectCriticalInfoTask
2. Latency-optimized voice pipeline (sub-300ms target)
3. Proper agent handoffs via function tool returns (no infinite loops!)
4. Langfuse observability for latency tracking

Architecture:
    GreeterAgent (triage)
        ├── returns UrgentTransferAgent (needs urgent help)
        ├── returns MessageFlowAgent (can wait for callback)
        └── returns CriticalEmergencyAgent (life-threatening)

    Each specialist agent uses AgentTask for focused data collection,
    preventing the routing tool loop bug.

Usage:
    # Start in development mode (uses LiveKit playground)
    python scripts/run_voice_agent.py dev

    # Production mode
    python scripts/run_voice_agent.py start
"""

import logging
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dotenv import load_dotenv

from livekit.agents import (
    AgentSession,
    JobContext,
    JobProcess,
    WorkerOptions,
    cli,
    metrics,
)
import livekit.plugins.deepgram as deepgram
import livekit.plugins.silero as silero
import livekit.plugins.openai as openai
import livekit.plugins.cartesia as cartesia

# Optional LLM providers - imported conditionally
try:
    import livekit.plugins.groq as groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False


try:
    from livekit.plugins.openai import realtime as openai_realtime
    OPENAI_REALTIME_AVAILABLE = True
except ImportError:
    OPENAI_REALTIME_AVAILABLE = False

try:
    from livekit.plugins import ultravox
    ULTRAVOX_AVAILABLE = True
except ImportError:
    ULTRAVOX_AVAILABLE = False

# CRITICAL: Import turn detector at MODULE LEVEL to register inference runner
# BEFORE Worker.__init__ is called. This must happen before cli.run_app().
from livekit.plugins.turn_detector.english import EnglishModel  # noqa: F401

# Turn detector - ENABLED with pre-downloaded models
USE_TURN_DETECTOR = True

# Load environment variables
load_dotenv()

# Langfuse observability
from nora_livekit.observability import init_langfuse, get_tracer

# Workflow agents and data classes (Task-based architecture)
from nora_livekit.workflows import GreeterAgent
from nora_livekit.workflows.data import SessionContext

# Sanitized TTS wrapper (removes function call syntax from LLM output)
from nora_livekit.nora.sanitized_tts import wrap_tts

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
# TTS VOICE CONFIGURATION
# Cartesia Sonic - ultra-low latency TTS (~100-300ms vs 4-9s for Deepgram)
# Browse voices: https://play.cartesia.ai/
# =============================================================================
CARTESIA_VOICE_ID = os.getenv("CARTESIA_VOICE_ID", "996a8b96-4804-46f0-8e05-3fd4ef1a87cd")
# Fallback: Deepgram Aura-2 (slower but reliable)
DEEPGRAM_TTS_VOICE = os.getenv("DEEPGRAM_TTS_VOICE", "aura-2-thalia-en")
# TTS Provider: cartesia (fast) or deepgram (fallback)
TTS_PROVIDER = os.getenv("TTS_PROVIDER", "cartesia")

# =============================================================================
# LLM PROVIDER CONFIGURATION
# Supported: openai, groq, ultravox (speech-to-speech)
# =============================================================================
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "150"))  # Short responses for voice

# Ultravox voice (only used when LLM_PROVIDER=ultravox)
# Browse voices: https://app.ultravox.ai/voices
ULTRAVOX_VOICE = os.getenv("ULTRAVOX_VOICE", "Mark")




def _get_office_config() -> dict:
    """Get office configuration dict."""
    return {
        "name": OFFICE_NAME,
        "hours": OFFICE_HOURS,
        "address": OFFICE_ADDRESS,
        "website": OFFICE_WEBSITE,
        "phone": OFFICE_PHONE,
        "is_open": IS_CLINIC_OPEN,
    }


def _is_realtime_mode() -> bool:
    """Check if using a realtime (speech-to-speech) model."""
    return LLM_PROVIDER.lower() == "ultravox"


def _get_llm():
    """Get LLM instance based on provider configuration.

    Supports:
    - openai: OpenAI GPT models (default)
    - groq: Groq's ultra-fast inference (requires GROQ_API_KEY)
    - ultravox: Speech-to-speech realtime model (requires ULTRAVOX_API_KEY)

    Returns:
        LLM instance configured for the selected provider
    """
    provider = LLM_PROVIDER.lower()
    model = LLM_MODEL
    max_tokens = LLM_MAX_TOKENS

    logger.info(f"Configuring LLM: provider={provider}, model={model}, max_tokens={max_tokens}")

    if provider == "ultravox":
        if not ULTRAVOX_AVAILABLE:
            logger.warning("Ultravox plugin not installed, falling back to OpenAI")
            return openai.LLM(model="gpt-4o-mini", temperature=0.7)
        if not os.getenv("ULTRAVOX_API_KEY"):
            logger.warning("ULTRAVOX_API_KEY not set, falling back to OpenAI")
            return openai.LLM(model="gpt-4o-mini", temperature=0.7)
        logger.info(f"Using Ultravox realtime model with voice: {ULTRAVOX_VOICE}")
        # Ultravox is a realtime model - handles STT+LLM+TTS in one connection
        return ultravox.realtime.RealtimeModel(voice=ULTRAVOX_VOICE)

    elif provider == "groq":
        if not GROQ_AVAILABLE:
            logger.warning("Groq plugin not installed, falling back to OpenAI")
            return openai.LLM(model="gpt-4o-mini", temperature=0.7)
        if not os.getenv("GROQ_API_KEY"):
            logger.warning("GROQ_API_KEY not set, falling back to OpenAI")
            return openai.LLM(model="gpt-4o-mini", temperature=0.7)
        # Groq models: llama-3.3-70b-versatile (reliable tool calling), llama-3.1-8b-instant (fast but flaky)
        # The 8B model generates invalid function calls; 70B is more reliable
        groq_model = model if model.startswith("llama") or model.startswith("mixtral") else "llama-3.3-70b-versatile"
        logger.info(f"Using Groq with model: {groq_model}")
        return groq.LLM(model=groq_model, temperature=0.7)

    else:  # Default: openai
        # Note: livekit-plugins-openai LLM doesn't support max_tokens parameter
        return openai.LLM(model=model, temperature=0.7)


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

    # Note: Workflow agents load their own prompts internally
    # No need for PromptManager prewarming with Task-based architecture
    logger.info("  Task-based workflow: Agents load prompts on demand")

    # Initialize Langfuse observability
    logger.info("  Initializing Langfuse observability...")
    tracer = init_langfuse()
    proc.userdata["langfuse_enabled"] = tracer.enabled
    if tracer.enabled:
        logger.info("  ✓ Langfuse enabled")
    else:
        logger.info("  ○ Langfuse disabled (no API keys)")

    logger.info("Models prewarmed successfully!")


async def entrypoint(ctx: JobContext):
    """Main entry point for the Nora voice agent.

    Uses the Task-based workflow architecture:
    1. GreeterAgent handles initial greeting and triage
    2. Routing tools return specialist agents (proper handoff pattern)
    3. Specialist agents use AgentTask for focused data collection
    4. No infinite loops because Tasks don't have routing tools
    """
    logger.info("Nora agent starting with TASK-BASED WORKFLOW...")

    # Connect to the room
    await ctx.connect()
    logger.info(f"Connected to room: {ctx.room.name}")

    # Get caller phone from room participant
    caller_phone = ""
    for participant in ctx.room.remote_participants.values():
        caller_phone = participant.identity or ""
        break

    # Create session context with caller info
    session_context = SessionContext(
        caller_phone=caller_phone,
        office_name=OFFICE_NAME,
        is_clinic_open=IS_CLINIC_OPEN,
    )
    logger.info(f"Session context: phone={caller_phone[:4]}..., clinic_open={IS_CLINIC_OPEN}")

    # Start Langfuse conversation trace (non-fatal if it fails)
    try:
        tracer = get_tracer()
        if tracer and tracer.enabled:
            tracer.start_conversation(
                caller_phone=caller_phone,
                office_name=OFFICE_NAME,
                metadata={
                    "room_name": ctx.room.name,
                    "is_clinic_open": IS_CLINIC_OPEN,
                    "llm_provider": LLM_PROVIDER,
                    "llm_model": LLM_MODEL,
                    "llm_max_tokens": LLM_MAX_TOKENS,
                    "voice_id": DEEPGRAM_TTS_VOICE,
                    "architecture": "task_based_workflow",
                },
            )
            logger.info("Langfuse trace started")
    except Exception as e:
        logger.warning(f"Langfuse tracing failed (non-fatal): {e}")

    # Create the GreeterAgent with session context
    # The agent's on_enter() will handle the initial greeting
    # Routing tools on the agent return new specialist agents (proper handoff)
    agent = GreeterAgent(session_context=session_context)
    logger.info("GreeterAgent created with Task-based workflow")

    # Create the agent session based on provider mode
    if _is_realtime_mode():
        # Ultravox mode: Speech-to-speech (STT+LLM+TTS in single connection)
        logger.info("Creating AgentSession in REALTIME mode (Ultravox)")
        session = AgentSession(
            # VAD - prewarmed
            vad=ctx.proc.userdata["vad"],

            # Realtime model handles STT+LLM+TTS together
            llm=_get_llm(),

            # Turn detection - English model
            turn_detection=_get_turn_detector() if USE_TURN_DETECTOR else None,

            # Interruption handling
            allow_interruptions=True,
            min_interruption_duration=0.5,
        )
    else:
        # Standard mode: Separate STT → LLM → TTS pipeline
        logger.info("Creating AgentSession in STANDARD mode (STT→LLM→TTS)")
        session = AgentSession(
            # VAD - prewarmed
            vad=ctx.proc.userdata["vad"],

            # STT - Deepgram Nova-3 (latency optimized)
            stt=deepgram.STT(
                model="nova-3",
                language="en",
                smart_format=True,
                filler_words=False,
            ),

            # LLM - Configurable provider (openai, groq)
            llm=_get_llm(),

            # TTS - Cartesia Sonic (ultra-low latency) with sanitizer
            tts=wrap_tts(cartesia.TTS(
                voice=CARTESIA_VOICE_ID,
            )),

            # Turn detection - English model
            turn_detection=_get_turn_detector() if USE_TURN_DETECTOR else None,

            # Endpointing delays (aggressive for low latency)
            min_endpointing_delay=0.25,
            max_endpointing_delay=1.2,

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
        metrics.log_metrics(ev.metrics)
        usage_collector.collect(ev.metrics)

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

    # Start the session - GreeterAgent.on_enter() handles initial greeting
    await session.start(agent=agent, room=ctx.room)

    logger.info(f"Nora is running with TASK-BASED WORKFLOW for {OFFICE_NAME}")


def main():
    """Run the Nora voice agent."""
    print("\n" + "=" * 60)
    print("  NORA VETERINARY ASSISTANT - TASK-BASED WORKFLOW")
    print("=" * 60)

    # Check required environment variables
    required_vars = {
        "LIVEKIT_URL": os.getenv("LIVEKIT_URL"),
        "LIVEKIT_API_KEY": os.getenv("LIVEKIT_API_KEY"),
        "LIVEKIT_API_SECRET": os.getenv("LIVEKIT_API_SECRET"),
        "DEEPGRAM_API_KEY": os.getenv("DEEPGRAM_API_KEY"),
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
    print(f"  Currently Open: {'YES' if IS_CLINIC_OPEN else 'NO'}")

    print("\nTASK-BASED WORKFLOW ARCHITECTURE:")
    print("  GreeterAgent → Triage and routing")
    print("    ├── UrgentTransferAgent (CollectUrgentInfoTask)")
    print("    ├── MessageFlowAgent (CollectMessageInfoTask)")
    print("    └── CriticalEmergencyAgent (CollectCriticalInfoTask)")
    print("  → No infinite loops! Tasks have focused tools only.")

    print("\nVoice Pipeline:")
    print(f"  STT: Deepgram Nova-3")
    print(f"  LLM: {LLM_PROVIDER}/{LLM_MODEL} (max_tokens={LLM_MAX_TOKENS})")
    print(f"  TTS: Cartesia Sonic (voice: {CARTESIA_VOICE_ID})")
    print(f"  TTS Sanitizer: ✓ Enabled (removes function call syntax)")
    print(f"  Turn Detection: {'Enabled' if USE_TURN_DETECTOR else 'Disabled'}")

    # Show LLM provider availability
    print(f"\nLLM Provider Status:")
    print(f"  OpenAI: ✓ Available")
    print(f"  Groq: {'✓ Available' if GROQ_AVAILABLE else '○ Not installed (pip install livekit-plugins-groq)'}")
    print(f"  Ultravox: {'✓ Available (speech-to-speech)' if ULTRAVOX_AVAILABLE else '○ Not installed (pip install livekit-plugins-ultravox)'}")

    # Check Langfuse configuration
    langfuse_enabled = bool(os.getenv("LANGFUSE_PUBLIC_KEY"))
    print("\nObservability:")
    if langfuse_enabled:
        print(f"  Langfuse: ✓ Enabled")
        print(f"    Host: {os.getenv('LANGFUSE_HOST', 'https://cloud.langfuse.com')}")
    else:
        print("  Langfuse: ○ Disabled")

    print("\nAgent Routing (GreeterAgent methods):")
    print("  ✓ route_to_urgent_transfer → Returns UrgentTransferAgent")
    print("  ✓ route_to_message_flow → Returns MessageFlowAgent")
    print("  ✓ route_to_critical_emergency → Returns CriticalEmergencyAgent")
    print("  ✓ queryCorpus → Breed/species lookup")

    print("\nData Collection Tasks (focused tools, no routing):")
    print("  ✓ CollectUrgentInfoTask → record_callback, record_name, record_pet...")
    print("  ✓ CollectMessageInfoTask → record_callback, record_name, record_concern...")
    print("  ✓ CollectCriticalInfoTask → record_callback_confirmed, record_first_name")

    print("\n" + "-" * 60)
    print("Starting Nora with TASK-BASED WORKFLOW...")
    print("Agent Name: nora-v2 (explicit dispatch)")
    print("Architecture: Proper agent handoffs prevent infinite loops!")
    print("")
    print("NOTE: Named agents require explicit dispatch!")
    print("  - Configure SIP dispatch rule with agent_name='nora-v2'")
    print("  - Or use AgentDispatch API to dispatch to rooms")
    print("-" * 60 + "\n")

    # Run the agent with explicit dispatch (named agent)
    # This prevents conflicts with the old contaminated unnamed agent
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            prewarm_fnc=prewarm,
            agent_name="nora-v2",  # Named agent for explicit dispatch
            num_idle_processes=1,
            job_memory_warn_mb=300,
        ),
    )


if __name__ == "__main__":
    main()
