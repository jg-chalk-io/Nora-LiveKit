#!/usr/bin/env python3
"""Run Nora Voice Agent with LiveKit - Phased Prompt Architecture.

This script creates Nora, the veterinary virtual assistant with:
1. PHASED PROMPTS for reduced latency:
   - Phase 1: Greeter (~2K tokens) - Handles greeting and triage
   - Phase 2A: Urgent Transfer (~5K tokens) - Full collection for urgent cases
   - Phase 2B: Message Flow (~4K tokens) - Non-urgent message taking
   - Phase 2C: Critical Emergency (~2K tokens) - Life-threatening, minimal data
2. Latency-optimized voice pipeline (sub-300ms target with Phase 1)
3. Seamless prompt transitions via function tools
4. Langfuse observability for latency tracking

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

# Phased prompt manager
from nora_livekit.prompts import PromptManager, PromptPhase, get_prompt_manager

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
CARTESIA_VOICE_ID = os.getenv("CARTESIA_VOICE_ID", "79a125e8-cd45-4c13-8a67-188112f4dd22")
CARTESIA_SPEED = float(os.getenv("CARTESIA_SPEED", "1.0"))


# =============================================================================
# GLOBAL STATE FOR PROMPT SWITCHING
# =============================================================================
# Store the current session and agent for prompt switching
_current_session: AgentSession | None = None
_prompt_manager: PromptManager | None = None


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

    # Initialize prompt manager with Phase 1
    logger.info("  Initializing phased prompt manager...")
    prompts_dir = Path(__file__).parent.parent / "prompts"
    manager = PromptManager(
        prompts_dir=prompts_dir,
        office_config=_get_office_config(),
    )
    proc.userdata["prompt_manager"] = manager

    # Log prompt sizes for comparison
    for phase in PromptPhase:
        tokens = manager.get_estimated_tokens(phase)
        logger.info(f"    {phase.value}: ~{tokens} tokens")

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
# ROUTING FUNCTION TOOLS - These trigger prompt phase transitions
# Uses session.update_agent() to properly switch agent instructions
# =============================================================================

def _get_all_tools():
    """Get all tools for creating new agents."""
    return [
        route_to_urgent_transfer,
        route_to_message_flow,
        route_to_critical_emergency,
        transferFromAiTriageWithMetadata,
        collectNameNumberConcernPetName,
        hangUp,
        queryCorpus,
    ]


@function_tool
async def route_to_urgent_transfer(
    context: RunContext,
    pet_name: str = "",
    species: str = "",
    reason: str = "",
    caller_phone: str = "",
) -> str:
    """Route to urgent transfer flow when pet needs immediate assistance.

    Call this when the caller confirms their pet needs immediate help.
    This will switch to the specialized urgent transfer agent.
    """
    global _prompt_manager, _current_session

    logger.info(
        "ROUTING TO URGENT TRANSFER",
        extra={
            "pet_name": pet_name,
            "species": species,
            "reason": reason,
        }
    )

    if _prompt_manager and _current_session:
        new_prompt = _prompt_manager.transition_to(
            PromptPhase.URGENT_TRANSFER,
            context_updates={
                "pet_name": pet_name,
                "species": species,
                "reason": reason,
                "caller_phone": caller_phone,
                "triage_result": "urgent",
            },
        )

        # Create new agent with urgent transfer prompt and switch to it
        new_agent = Agent(
            instructions=new_prompt,
            tools=_get_all_tools(),
        )
        _current_session.update_agent(new_agent)
        logger.info(f"AGENT SWITCHED to URGENT_TRANSFER (~{len(new_prompt)//4} tokens)")

    return "Switched to urgent transfer flow. Continue with data collection."


@function_tool
async def route_to_message_flow(
    context: RunContext,
    pet_name: str = "",
    species: str = "",
    reason: str = "",
    caller_phone: str = "",
) -> str:
    """Route to message flow when request can wait for callback.

    Call this when the caller confirms their request is not urgent
    and can wait for office staff to return their call.
    """
    global _prompt_manager, _current_session

    logger.info(
        "ROUTING TO MESSAGE FLOW",
        extra={
            "pet_name": pet_name,
            "species": species,
            "reason": reason,
        }
    )

    if _prompt_manager and _current_session:
        new_prompt = _prompt_manager.transition_to(
            PromptPhase.MESSAGE_FLOW,
            context_updates={
                "pet_name": pet_name,
                "species": species,
                "reason": reason,
                "caller_phone": caller_phone,
                "triage_result": "can_wait",
            },
        )

        # Create new agent with message flow prompt and switch to it
        new_agent = Agent(
            instructions=new_prompt,
            tools=_get_all_tools(),
        )
        _current_session.update_agent(new_agent)
        logger.info(f"AGENT SWITCHED to MESSAGE_FLOW (~{len(new_prompt)//4} tokens)")

    return "Switched to message flow. Continue with data collection."


@function_tool
async def route_to_critical_emergency(
    context: RunContext,
    pet_name: str = "",
    species: str = "",
    emergency_type: str = "",
    caller_phone: str = "",
) -> str:
    """Route to critical emergency flow for life-threatening situations.

    Call this ONLY for these specific emergencies:
    - Hit by car
    - Not breathing / can't breathe
    - Active seizure
    - Unconscious / collapsed
    - Dead / appears dead

    This is the FASTEST path - collects only phone + name then transfers.
    """
    global _prompt_manager, _current_session

    logger.info(
        "ROUTING TO CRITICAL EMERGENCY",
        extra={
            "pet_name": pet_name,
            "emergency_type": emergency_type,
        }
    )

    if _prompt_manager and _current_session:
        new_prompt = _prompt_manager.transition_to(
            PromptPhase.CRITICAL_EMERGENCY,
            context_updates={
                "pet_name": pet_name,
                "species": species,
                "emergency_type": emergency_type,
                "caller_phone": caller_phone,
                "triage_result": "critical_emergency",
            },
        )

        # Create new agent with critical emergency prompt and switch to it
        new_agent = Agent(
            instructions=new_prompt,
            tools=_get_all_tools(),
        )
        _current_session.update_agent(new_agent)
        logger.info(f"AGENT SWITCHED to CRITICAL_EMERGENCY (~{len(new_prompt)//4} tokens)")

    return "CRITICAL EMERGENCY - Switched to minimal collection flow. Get phone + name only, then transfer immediately."


# =============================================================================
# NORA TOOLS - These execute the actual business logic
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


@function_tool
async def queryCorpus(context: RunContext, query: str) -> str:
    """Look up breed/species information from veterinary corpus.

    Use this when caller mentions a breed name to confirm the species.
    """
    # Simple breed lookup - in production this would query a real corpus
    breed_map = {
        "yorkie": "Yorkshire Terrier (dog)",
        "yorkshire terrier": "Yorkshire Terrier (dog)",
        "labrador": "Labrador Retriever (dog)",
        "lab": "Labrador Retriever (dog)",
        "labradoodle": "Labradoodle - Poodle/Labrador mix (dog)",
        "goldendoodle": "Goldendoodle - Poodle/Golden Retriever mix (dog)",
        "german shepherd": "German Shepherd (dog)",
        "golden retriever": "Golden Retriever (dog)",
        "tabby": "Tabby (cat)",
        "persian": "Persian (cat)",
        "siamese": "Siamese (cat)",
        "maine coon": "Maine Coon (cat)",
    }
    result = breed_map.get(query.lower(), f"Unknown breed: {query}")
    logger.info(f"queryCorpus({query}) -> {result}")
    return result


async def entrypoint(ctx: JobContext):
    """Main entry point for the Nora voice agent."""
    global _current_session, _prompt_manager

    logger.info("Nora agent starting with PHASED PROMPTS...")

    # Connect to the room
    await ctx.connect()
    logger.info(f"Connected to room: {ctx.room.name}")

    # Get prompt manager
    _prompt_manager = ctx.proc.userdata.get("prompt_manager")
    if not _prompt_manager:
        # Fallback: create fresh manager
        prompts_dir = Path(__file__).parent.parent / "prompts"
        _prompt_manager = PromptManager(
            prompts_dir=prompts_dir,
            office_config=_get_office_config(),
        )

    # Get caller phone from room participant
    caller_phone = ""
    for participant in ctx.room.remote_participants.values():
        caller_phone = participant.identity or ""
        break

    # Update prompt context with caller info
    _prompt_manager.update_context(caller_phone=caller_phone)

    # Start with Phase 1: Greeter prompt
    greeter_prompt = _prompt_manager.get_prompt_for_phase(PromptPhase.GREETER)
    logger.info(f"Starting with GREETER prompt (~{len(greeter_prompt)//4} tokens)")

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
                    "llm_model": os.getenv("LLM_MODEL", "gpt-4o-mini"),
                    "voice_id": CARTESIA_VOICE_ID[:8],
                    "prompt_phase": "greeter",
                    "prompt_tokens": len(greeter_prompt) // 4,
                },
            )
            logger.info("Langfuse trace started")
    except Exception as e:
        logger.warning(f"Langfuse tracing failed (non-fatal): {e}")

    # Create the Nora agent with Phase 1 prompt
    agent = Agent(
        instructions=greeter_prompt,
        tools=_get_all_tools(),
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

        # LLM - OpenAI (gpt-4o-mini for speed)
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

    # Store session reference for prompt switching
    _current_session = session

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
        global _current_session, _prompt_manager
        try:
            summary = usage_collector.get_summary()
            logger.info(f"Session usage summary: {summary}")

            # Log final prompt phase
            if _prompt_manager:
                final_phase = _prompt_manager.current_phase
                logger.info(f"Final prompt phase: {final_phase.value}")

            if tracer and tracer.enabled:
                tracer.end_conversation(
                    outcome="completed",
                    metadata={
                        "usage_summary": str(summary),
                        "final_phase": _prompt_manager.current_phase.value if _prompt_manager else "unknown",
                    },
                )
        except Exception as e:
            logger.warning(f"Langfuse shutdown failed: {e}")

        # Clear global state
        _current_session = None
        _prompt_manager = None

    ctx.add_shutdown_callback(on_shutdown)

    # Start the session
    await session.start(agent=agent, room=ctx.room)

    # Generate the proper Nora greeting based on clinic status
    if IS_CLINIC_OPEN:
        greeting = (
            f"Thank you for calling {OFFICE_NAME}. "
            "We're currently open but assisting other callers. "
            "I'm Nora, the virtual assistant. How can I help you today?"
        )
    else:
        greeting = (
            f"Thank you for calling {OFFICE_NAME}. "
            "The office is currently closed, but I'm Nora, "
            "the virtual assistant here to help. How can I assist you?"
        )

    await session.generate_reply(instructions=f"Say exactly this: {greeting}")

    logger.info(f"Nora is running with PHASED PROMPTS for {OFFICE_NAME}")
    logger.info(f"  Current phase: {_prompt_manager.current_phase.value}")
    logger.info(f"  Initial tokens: ~{_prompt_manager.get_estimated_tokens()}")


def main():
    """Run the Nora voice agent."""
    print("\n" + "=" * 60)
    print("  NORA VETERINARY ASSISTANT - PHASED PROMPTS")
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
    print(f"  Currently Open: {'YES' if IS_CLINIC_OPEN else 'NO'}")

    print("\nPHASED PROMPTS (Latency Optimization):")
    print("  Phase 1 (Greeter):           ~500 tokens (vs 18K original)")
    print("  Phase 2A (Urgent Transfer):  ~1,200 tokens")
    print("  Phase 2B (Message Flow):     ~1,000 tokens")
    print("  Phase 2C (Critical Emerg):   ~400 tokens")
    print("  → 60-70% token reduction per turn!")

    print("\nVoice Pipeline:")
    print(f"  STT: Deepgram Nova-3")
    print(f"  LLM: {os.getenv('LLM_MODEL', 'gpt-4o-mini')}")
    print(f"  TTS: Cartesia Sonic (voice: {CARTESIA_VOICE_ID[:8]}..., speed: {CARTESIA_SPEED})")
    print(f"  Turn Detection: {'Enabled' if USE_TURN_DETECTOR else 'Disabled'}")

    # Check Langfuse configuration
    langfuse_enabled = bool(os.getenv("LANGFUSE_PUBLIC_KEY"))
    print("\nObservability:")
    if langfuse_enabled:
        print(f"  Langfuse: ✓ Enabled")
        print(f"    Host: {os.getenv('LANGFUSE_HOST', 'https://cloud.langfuse.com')}")
    else:
        print("  Langfuse: ○ Disabled")

    print("\nRouting Tools (trigger prompt switches):")
    print("  ✓ route_to_urgent_transfer")
    print("  ✓ route_to_message_flow")
    print("  ✓ route_to_critical_emergency")

    print("\nBusiness Tools:")
    print("  ✓ transferFromAiTriageWithMetadata")
    print("  ✓ collectNameNumberConcernPetName")
    print("  ✓ hangUp")
    print("  ✓ queryCorpus")

    print("\n" + "-" * 60)
    print("Starting Nora with PHASED PROMPTS...")
    print("Expected latency improvement: 3-5x faster initial response")
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
