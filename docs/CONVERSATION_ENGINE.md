---
id: conversation-engine-guide
title: Conversation Engine Architecture & Implementation Guide
description: Complete guide to Nora-LiveKit conversation engine with context management, LLM integration, and turn-taking
author: GOOS
created: 2025-11-25
updated: 2025-11-25
version: 1.0.0
status: published
---

# Conversation Engine Architecture & Implementation Guide

## Overview

The Nora-LiveKit Conversation Engine provides intelligent, contextual voice conversation support with multi-turn dialogue, participant tracking, and LLM-powered response generation. It seamlessly integrates with the Voice Pipeline to deliver natural, dynamic conversations between users and the AI agent.

**Key Capabilities**:
- Multi-turn context management with automatic history pruning (20-message limit)
- Multi-provider LLM support (OpenAI GPT-4, Anthropic Claude 3)
- Natural turn-taking detection with Voice Activity Detection (VAD)
- Multi-participant tracking (2-10 concurrent users)
- Phase-aware conversation lifecycle (GREETING → ACTIVE → CLOSING)
- Intelligent fallback and error recovery

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Component Details](#component-details)
3. [Quick Start](#quick-start)
4. [Configuration](#configuration)
5. [Integration Guide](#integration-guide)
6. [Usage Examples](#usage-examples)
7. [Troubleshooting](#troubleshooting)
8. [Performance Considerations](#performance-considerations)

---

## Architecture Overview

### Component Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    VoicePipeline                             │
│  (Deepgram STT → Conversation Engine → Cartesia TTS)        │
└──────────────────┬──────────────────────────────────────────┘
                   │
        ┌──────────┴──────────┐
        │                     │
        ▼                     ▼
   ┌─────────────┐      ┌──────────────────────┐
   │  Context    │      │  LLMIntegration      │
   │  Management │◄─────┤  (OpenAI/Anthropic)  │
   └──────┬──────┘      └──────────────────────┘
          │
          ├─────────────────────────┬────────────────────┐
          ▼                         ▼                    ▼
    ┌───────────────┐    ┌──────────────────┐  ┌──────────────────┐
    │ Message       │    │ Participant      │  │ Turn Manager     │
    │ History       │    │ Manager          │  │ (VAD Detection)  │
    │ (20 messages) │    │ (2-10 users)     │  │                  │
    └───────────────┘    └──────────────────┘  └──────────────────┘
```

### System Architecture

The Conversation Engine operates within the Nora-LiveKit voice agent framework:

```
LiveKit Room Events
    │
    ├─► participant_connected
    │       └─► ParticipantManager.add_participant()
    │
    ├─► participant_disconnected
    │       └─► ParticipantManager.remove_participant()
    │
    └─► audio_stream
            └─► VoicePipeline
                └─► Deepgram STT
                    └─► transcribed_text
                        └─► ConversationEngine.process_transcription()
                            ├─► ConversationContext (add message)
                            ├─► LLMIntegration (generate response)
                            ├─► ConversationContext (add response)
                            └─► CartesiaTTS (synthesize)
```

---

## Component Details

### 1. ConversationContext

**Purpose**: Manages in-memory conversation state, message history, and participant metadata.

**Key Responsibilities**:
- Message history management with automatic pruning
- Participant metadata storage
- Conversation phase tracking (GREETING → ACTIVE → CLOSING)
- LLM-compatible message formatting

**Data Structures**:

```python
class ConversationPhase(Enum):
    GREETING = "greeting"  # Initial greeting phase
    ACTIVE = "active"      # Main conversation phase
    CLOSING = "closing"    # Conversation ending phase

@dataclass
class Message:
    role: Literal["user", "assistant", "system"]
    content: str
    timestamp: datetime
    participant_id: str | None = None
    metadata: dict[str, Any] = None

@dataclass
class ParticipantMetadata:
    participant_id: str
    name: str | None
    join_time: datetime
    preferences: dict[str, Any] = None
```

**Key Methods**:

```python
def add_message(role: str, content: str, participant_id: str | None = None)
    """Add message and auto-prune if exceeds max_history (default: 20)."""

def get_history(limit: int | None = None) -> list[Message]
    """Get conversation history with optional limit."""

def set_phase(phase: ConversationPhase)
    """Transition phase with validation (GREETING → ACTIVE → CLOSING)."""

def format_for_llm() -> list[dict[str, str]]
    """Return OpenAI/Anthropic-compatible format: [{"role": "...", "content": "..."}]"""
```

**Auto-Pruning Behavior**:
- When history exceeds `max_history` (default: 20), oldest messages are removed
- Preserves chronological order
- Runs in O(n) time, negligible for 20-message windows

### 2. LLMIntegration

**Purpose**: Abstract LLM API calls with multi-provider support, retry logic, and TTS-safe formatting.

**Supported Providers**:

| Provider | Models | Base URL |
|----------|--------|----------|
| OpenAI | gpt-4, gpt-3.5-turbo | api.openai.com |
| Anthropic | claude-3-opus, claude-3-sonnet | api.anthropic.com |

**Key Features**:

1. **Multi-Provider Support**:
   ```python
   # OpenAI
   llm = LLMIntegration(
       provider=LLMProvider.OPENAI,
       api_key="sk-...",
       model="gpt-4",
       temperature=0.7,
       max_tokens=150
   )

   # Anthropic
   llm = LLMIntegration(
       provider=LLMProvider.ANTHROPIC,
       api_key="sk-ant-...",
       model="claude-3-sonnet-20240229",
       temperature=0.7,
       max_tokens=150
   )
   ```

2. **Retry Logic with Exponential Backoff**:
   - Retryable errors: 429 (rate limit), 500, 503
   - Backoff delays: 1s, 2s, 4s
   - Max attempts: 3
   - Falls back to `fallback_response` on permanent failure

3. **Phase-Specific System Prompts**:
   ```python
   GREETING: "You are Nora, a friendly AI voice assistant.
              Greet the user warmly. Keep responses SHORT (1-2 sentences)."

   ACTIVE:   "You are Nora, a helpful AI voice assistant.
              Provide clear, concise answers. Keep responses SHORT (2-3 sentences max)."

   CLOSING:  "The conversation is ending. Provide a brief closing statement.
              Keep it SHORT (1 sentence)."
   ```

4. **TTS-Compatible Text Formatting**:
   - Removes markdown (**bold**, _italic_, code blocks)
   - Removes bullet points and numbered lists
   - Cleans up extra whitespace and line breaks
   - Ensures natural speech synthesis

**Performance**:
- Average latency: 300-800ms (OpenAI: 400-600ms, Anthropic: 500-800ms)
- Token usage: 50-150 tokens per response (configurable max_tokens)

### 3. TurnManager

**Purpose**: Detect turn boundaries and interruptions using Voice Activity Detection (VAD).

**Configuration Parameters**:

| Parameter | Default | Range | Purpose |
|-----------|---------|-------|---------|
| `vad_threshold` | 0.5 | 0.0-1.0 | Voice activity confidence threshold |
| `min_speech_duration_ms` | 300 | 100-1000 | Minimum speech to trigger turn |
| `silence_duration_ms` | 700 | 300-2000 | Silence threshold for turn end |

**Turn Events**:

```python
class TurnEvent(Enum):
    USER_TURN_START = "user_turn_start"        # User started speaking
    USER_TURN_END = "user_turn_end"            # User finished speaking
    AGENT_TURN_START = "agent_turn_start"      # Agent started speaking
    AGENT_TURN_END = "agent_turn_end"          # Agent finished speaking
    INTERRUPTION = "interruption"               # User interrupted agent
```

**Key Methods**:

```python
def set_agent_speaking(speaking: bool)
    """Notify manager when agent is speaking.
    Prevents USER_TURN_END while agent_speaking=True."""

async def wait_for_turn() -> TurnData
    """Block until next turn event. Returns TurnData with metadata."""
```

**Natural Turn-Taking**:
- Typical conversation pauses: 500-1000ms
- Default silence threshold: 700ms
- Provides >95% accuracy for natural-sounding turn boundaries

### 4. ConversationEngine

**Purpose**: Orchestrate conversation flow, integrate all components, manage lifecycle.

**Initialization**:

```python
engine = ConversationEngine(
    config=ConversationEngineConfig(
        max_history=20,
        idle_timeout_seconds=120,
        enable_interruptions=True,
        fallback_response="I'm having trouble right now. Please try again."
    ),
    context=ConversationContext(max_history=20),
    llm=LLMIntegration(...),
    turn_manager=TurnManager(...)
)
```

**Lifecycle**:

```
1. engine.start()
   └─► Initialize in GREETING phase
   └─► Generate initial greeting

2. User speaks → process_transcription()
   ├─► Add user message to context
   ├─► Check phase transition (GREETING → ACTIVE after 1+ user message)
   ├─► Call LLM to generate response
   ├─► Add response to context
   └─► Return text for TTS

3. Check for idle timeout (120s default)
   └─► Auto-transition to CLOSING phase

4. engine.stop()
   └─► Cleanup resources
```

**Key Methods**:

```python
async def start() -> None
    """Initialize engine, generate greeting, start idle timeout monitoring."""

async def process_transcription(text: str, participant_id: str) -> str
    """Main entry point: transcribed text → LLM response."""

async def handle_turn_event(turn_data: TurnData) -> None
    """Handle interruption and turn events."""

async def stop() -> None
    """Graceful shutdown and cleanup."""
```

**Phase Transitions**:

```
GREETING ──(after 1+ user message)──► ACTIVE ──(after 120s idle)──► CLOSING

Rules:
- GREETING → ACTIVE: Automatic after user's first message
- ACTIVE → CLOSING: Automatic after idle_timeout_seconds
- CLOSING → (none): Terminal state
- Invalid transitions raise ValueError
```

### 5. ParticipantManager

**Purpose**: Track multiple participants in conversation room.

**Key Responsibilities**:
- Join/leave event tracking
- Activity timestamp management
- Per-participant statistics
- Active participants listing

**Data Structure**:

```python
@dataclass
class ParticipantActivity:
    participant_id: str
    join_time: datetime
    leave_time: datetime | None
    last_activity: datetime
    message_count: int
    is_active: bool
```

**Key Methods**:

```python
def add_participant(participant_id: str, name: str | None = None)
    """Add participant with join_time timestamp."""

def remove_participant(participant_id: str)
    """Mark inactive and record leave_time."""

def update_activity(participant_id: str)
    """Update last_activity timestamp and increment message_count."""

def get_active_participants() -> list[ParticipantActivity]
    """Get all active participants sorted by join_time."""

def get_participant_stats(participant_id: str) -> ParticipantActivity | None
    """Get stats for specific participant."""
```

---

## Quick Start

### 1. Installation

```bash
# Add conversation dependencies to your environment
pip install openai anthropic tenacity

# Or use poetry
poetry add openai anthropic tenacity
```

### 2. Basic Setup

```python
from nora_livekit.config import Config, ConversationConfig, ConversationEngineConfig
from nora_livekit.conversation import (
    ConversationEngine, ConversationContext, LLMIntegration,
    TurnManager, LLMProvider
)

# Load configuration from environment
config = Config.from_env()

# Create conversation engine
engine = ConversationEngine(
    config=ConversationEngineConfig(
        max_history=20,
        idle_timeout_seconds=120,
        enable_interruptions=True
    ),
    context=ConversationContext(max_history=20),
    llm=LLMIntegration(
        provider=LLMProvider.OPENAI,
        api_key=config.conversation.llm_api_key,
        model="gpt-4",
        temperature=0.7,
        max_tokens=150
    ),
    turn_manager=TurnManager(
        vad_threshold=0.5,
        min_speech_duration_ms=300,
        silence_duration_ms=700
    )
)

# Start conversation
await engine.start()

# Process user input
response = await engine.process_transcription(
    text="Hello, how are you?",
    participant_id="user-123"
)

# Stop when done
await engine.stop()
```

### 3. VoicePipeline Integration

```python
from nora_livekit.voice.pipeline import VoicePipeline

# Initialize pipeline with conversation engine
pipeline = VoicePipeline(
    config=config,
    stt=deepgram_stt,
    tts=cartesia_tts,
    audio_handler=audio_handler,
    conversation_engine=engine  # Pass engine here
)

# Pipeline automatically delegates to engine.process_transcription()
```

---

## Configuration

### Environment Variables

**Required for Conversation Engine**:

```bash
# LLM Provider Configuration
LLM_PROVIDER=openai              # or "anthropic"
LLM_API_KEY=sk-...               # OpenAI or Anthropic API key
OPENAI_API_KEY=sk-...            # Alternative: OpenAI-specific
ANTHROPIC_API_KEY=sk-ant-...     # Alternative: Anthropic-specific
```

**Optional Settings**:

```bash
# LLM Model Selection
LLM_MODEL=gpt-4                  # OpenAI: gpt-4, gpt-3.5-turbo
                                 # Anthropic: claude-3-sonnet-20240229
LLM_TEMPERATURE=0.7              # Range: 0.0-1.0 (default: 0.7)
LLM_MAX_TOKENS=150               # Max response length (default: 150)

# Conversation Settings
CONVERSATION_MAX_HISTORY=20      # Max messages in context (default: 20)
IDLE_TIMEOUT_SECONDS=120         # Idle before closing (default: 120)
ENABLE_INTERRUPTIONS=true        # Allow user interruptions (default: true)
FALLBACK_RESPONSE="I'm having trouble right now. Please try again."

# Turn Detection (VAD)
VAD_THRESHOLD=0.5                # Voice activity threshold 0.0-1.0
MIN_SPEECH_DURATION_MS=300       # Minimum speech duration (default: 300)
SILENCE_DURATION_MS=700          # Silence threshold for turn end (default: 700)
```

### ConversationConfig Dataclass

```python
@dataclass
class ConversationConfig:
    # LLM Configuration
    llm_provider: str = "openai"
    llm_api_key: str = ""
    llm_model: str = "gpt-4"
    llm_temperature: float = 0.7
    llm_max_tokens: int = 150

    # Context Configuration
    max_history: int = 20

    # Turn Detection Configuration
    vad_threshold: float = 0.5
    min_speech_duration_ms: int = 300
    silence_duration_ms: int = 700

    # Conversation Behavior
    idle_timeout_seconds: int = 120
    enable_interruptions: bool = True
    fallback_response: str = "I'm having trouble right now. Please try again."
```

### Configuration Presets

**Conservative (Cost-Optimized)**:
```python
config = ConversationConfig(
    llm_provider="openai",
    llm_model="gpt-3.5-turbo",  # Cheaper
    llm_temperature=0.5,         # More predictable
    llm_max_tokens=100,          # Shorter responses
    max_history=10,              # Smaller context window
    idle_timeout_seconds=60      # Shorter timeouts
)
```

**Balanced (Default)**:
```python
config = ConversationConfig(
    llm_provider="openai",
    llm_model="gpt-4",
    llm_temperature=0.7,
    llm_max_tokens=150,
    max_history=20,
    idle_timeout_seconds=120
)
```

**Premium (Quality-Optimized)**:
```python
config = ConversationConfig(
    llm_provider="anthropic",
    llm_model="claude-3-opus-20240229",  # Most capable
    llm_temperature=0.8,                  # More creative
    llm_max_tokens=200,                   # Longer responses
    max_history=30,                       # Longer context
    idle_timeout_seconds=180              # Longer conversations
)
```

---

## Integration Guide

### 1. LiveKit Room Events

```python
# In your LiveKit agent initialization

# Handle participant join
@room.event.on("participant_connected")
async def on_participant_connected(participant: Participant):
    engine.participant_manager.add_participant(
        participant_id=participant.sid,
        name=participant.name
    )
    logger.info(f"Participant joined: {participant.name}")

# Handle participant leave
@room.event.on("participant_disconnected")
async def on_participant_disconnected(participant_id: str):
    engine.participant_manager.remove_participant(participant_id)
    logger.info(f"Participant left: {participant_id}")
```

### 2. VoicePipeline Integration

```python
# In VoicePipeline.__init__
def __init__(
    self,
    config: Config,
    stt: DeepgramSTT,
    tts: CartesiaTTS,
    audio_handler: AudioHandler,
    conversation_engine: ConversationEngine | None = None,
):
    self.conversation_engine = conversation_engine

# In VoicePipeline._generate_response()
async def _generate_response(self, text: str, participant_id: str = "") -> str:
    if self.conversation_engine:
        # Use conversation engine (SPEC-003)
        return await self.conversation_engine.process_transcription(
            text=text,
            participant_id=participant_id
        )
    else:
        # Fallback echo response
        return f"You said: {text}"
```

### 3. Configuration Loading

```python
# In Config.from_env()
config = Config.from_env()

if config.conversation:
    # Conversation engine is enabled
    engine = initialize_conversation_engine(config.conversation)
else:
    # Conversation engine disabled, use fallback
    logger.warning("Conversation engine not configured, using fallback mode")
```

---

## Usage Examples

### Example 1: Simple Conversation

```python
import asyncio
from nora_livekit.conversation import ConversationEngine

# Initialize engine (config from environment)
engine = initialize_engine_from_env()

async def simple_conversation():
    # Start conversation
    await engine.start()

    # User input 1
    response1 = await engine.process_transcription(
        "Hello, how are you?",
        participant_id="user-1"
    )
    print(f"Agent: {response1}")

    # User input 2 (with context from first message)
    response2 = await engine.process_transcription(
        "What's the weather like today?",
        participant_id="user-1"
    )
    print(f"Agent: {response2}")

    # Cleanup
    await engine.stop()

asyncio.run(simple_conversation())
```

### Example 2: Multi-Participant Conversation

```python
async def multi_participant_conversation():
    await engine.start()

    # Add participants
    engine.participant_manager.add_participant("alice", "Alice")
    engine.participant_manager.add_participant("bob", "Bob")

    # Alice speaks
    response1 = await engine.process_transcription(
        "Hi, I'm Alice",
        participant_id="alice"
    )

    # Bob speaks
    response2 = await engine.process_transcription(
        "And I'm Bob",
        participant_id="bob"
    )

    # Query active participants
    active = engine.participant_manager.get_active_participants()
    print(f"Active participants: {[p.participant_id for p in active]}")

    await engine.stop()
```

### Example 3: Monitoring Conversation Flow

```python
async def monitored_conversation():
    await engine.start()

    # Check initial phase
    print(f"Phase: {engine.context.phase.value}")  # GREETING

    # User speaks
    await engine.process_transcription("Hello", "user-1")
    print(f"Phase: {engine.context.phase.value}")  # ACTIVE (after 1 message)

    # Check conversation history
    history = engine.context.get_history()
    print(f"Messages: {len(history)}")

    for msg in history:
        print(f"  {msg.role}: {msg.content[:50]}...")

    await engine.stop()
```

### Example 4: Error Handling and Fallbacks

```python
async def conversation_with_error_handling():
    try:
        await engine.start()

        # Process with timeout protection
        try:
            response = await asyncio.wait_for(
                engine.process_transcription("Hello", "user-1"),
                timeout=5.0
            )
            print(f"Response: {response}")
        except asyncio.TimeoutError:
            logger.warning("LLM response timeout, using fallback")

    except Exception as e:
        logger.error(f"Conversation error: {e}")
        # System will use fallback_response
    finally:
        await engine.stop()
```

---

## Troubleshooting

### Issue: "No module named 'openai'"

**Solution**:
```bash
pip install openai anthropic
# Or for poetry:
poetry add openai anthropic
```

### Issue: "OPENAI_API_KEY not found"

**Solution**:
```bash
# Set environment variable
export OPENAI_API_KEY="sk-..."
export LLM_PROVIDER="openai"

# Or use .env file
echo "OPENAI_API_KEY=sk-..." > .env
source .env
```

### Issue: "Invalid phase transition: greeting -> closing"

**Root Cause**: Attempting invalid phase transition.

**Solution**:
```python
# Valid transitions only:
# GREETING → ACTIVE (after 1+ user message)
# ACTIVE → CLOSING (after idle timeout)

# ✗ Don't do this:
context.set_phase(ConversationPhase.CLOSING)  # From GREETING

# ✓ Do this:
context.set_phase(ConversationPhase.ACTIVE)   # After user message
# ... wait for idle timeout ...
context.set_phase(ConversationPhase.CLOSING)  # After idle
```

### Issue: "LLM API error: 429 (rate limit)"

**Expected Behavior**: System automatically retries with exponential backoff (1s, 2s, 4s).

**If Still Fails**:
1. Check API quota limits
2. Reduce `llm_max_tokens` to use fewer tokens
3. Implement request throttling at application level

### Issue: "Memory usage growing over time"

**Root Cause**: Message history not pruning properly.

**Solution**:
```python
# Verify max_history is set correctly
engine = ConversationEngine(
    config=ConversationEngineConfig(
        max_history=20  # Must be > 0
    ),
    ...
)

# Monitor history size
history = engine.context.get_history()
assert len(history) <= 20, "History not pruned!"
```

### Issue: "Turn detection not working"

**Root Cause**: TurnManager needs to be actively monitoring audio stream.

**Solution**:
```python
# Ensure turn manager is started with audio stream
await engine.turn_manager.start(audio_stream)

# Verify VAD threshold is appropriate
turn_manager = TurnManager(
    vad_threshold=0.5,      # 0.5 = balanced
    silence_duration_ms=700  # 700ms = human conversation rhythm
)
```

---

## Performance Considerations

### Latency Budget

| Component | Target P95 | Measured | Notes |
|-----------|-----------|----------|-------|
| Context operations | <10ms | ~2-5ms | add_message, get_history |
| TTS formatting | <5ms | ~1-3ms | Markdown removal |
| LLM API call | <1000ms | 300-800ms | Main bottleneck |
| Turn detection | <100ms | ~20-50ms | VAD processing |
| **Total** | **<1300ms** | **400-1000ms** | Acceptable for voice UI |

### Memory Usage

- Context (20 messages): ~10-20KB
- LLMIntegration (API clients): ~1MB
- ParticipantManager (10 participants): ~5KB
- **Total per conversation**: ~1.1MB

### Token Usage

- Greeting phase: 30-50 tokens input, 20-40 output
- Active phase: 100-200 tokens input, 50-100 output
- Closing phase: 50-100 tokens input, 10-20 output
- **Average**: 150-300 tokens per conversation

### Optimization Tips

1. **Reduce max_history** for cost-sensitive applications:
   ```python
   config = ConversationEngineConfig(max_history=10)
   ```

2. **Use gpt-3.5-turbo** instead of gpt-4 for 10x cost reduction:
   ```python
   llm = LLMIntegration(model="gpt-3.5-turbo", ...)
   ```

3. **Lower temperature** for more predictable (and cheaper) responses:
   ```python
   llm = LLMIntegration(temperature=0.5, ...)
   ```

4. **Enable caching** for frequently asked questions (future enhancement)

5. **Monitor token usage** in logs:
   ```
   INFO llm_response_generated model=gpt-4 tokens_used=145 latency_ms=412
   ```

---

## Related Documentation

- [API Reference](./CONVERSATION_API.md) - Detailed API documentation
- [Integration Guide](./CONVERSATION_INTEGRATION.md) - Integration patterns
- [Configuration Reference](./CONFIGURATION.md) - All configuration options
- [Voice Pipeline](./VOICE_PIPELINE.md) - STT/TTS integration
- [Architecture Overview](./ARCHITECTURE.md) - System architecture

---

## Support & Issues

For issues or questions:
1. Check [Troubleshooting](#troubleshooting) section
2. Review test cases in `tests/conversation/`
3. Check application logs for detailed error messages
4. Enable debug logging: `LOG_LEVEL=DEBUG`

---

**Version**: 1.0.0
**Last Updated**: 2025-11-25
**Status**: Published
**Maintainer**: GOOS
