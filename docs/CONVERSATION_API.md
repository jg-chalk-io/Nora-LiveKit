---
id: conversation-api-reference
title: Conversation Engine API Reference
description: Complete API documentation for ConversationEngine, ConversationContext, LLMIntegration, TurnManager, and ParticipantManager
author: GOOS
created: 2025-11-25
updated: 2025-11-25
version: 1.0.0
---

# Conversation Engine API Reference

## Table of Contents

1. [ConversationContext](#conversationcontext)
2. [LLMIntegration](#llmintegration)
3. [TurnManager](#turnmanager)
4. [ConversationEngine](#conversationengine)
5. [ParticipantManager](#participantmanager)
6. [Data Classes](#data-classes)
7. [Enums](#enums)
8. [Exceptions](#exceptions)

---

## ConversationContext

**Module**: `nora_livekit.conversation.context`

**Purpose**: Manages in-memory conversation state, message history, and participant metadata.

### Class Definition

```python
class ConversationContext:
    """Manages in-memory conversation state and history.

    Satisfies: REQ-F-CTX-001, REQ-F-CTX-002, REQ-F-CTX-003,
               REQ-F-CTX-004, REQ-F-CTX-005
    """
```

### Constructor

```python
def __init__(self, max_history: int = 20) -> None:
    """Initialize conversation context with history limit.

    Args:
        max_history: Maximum number of messages to retain (default: 20).
                    Must be > 0.

    Raises:
        ValueError: If max_history <= 0

    Example:
        context = ConversationContext(max_history=20)
    """
```

### Properties

#### `max_history`

```python
@property
def max_history(self) -> int:
    """Get the maximum history limit."""
```

**Returns**: `int` - Maximum messages retained

**Example**:
```python
context = ConversationContext(max_history=20)
assert context.max_history == 20
```

#### `phase`

```python
@property
def phase(self) -> ConversationPhase:
    """Get current conversation phase."""
```

**Returns**: `ConversationPhase` - Current phase (GREETING, ACTIVE, or CLOSING)

**Example**:
```python
if context.phase == ConversationPhase.GREETING:
    print("In greeting phase")
```

#### `session_id`

```python
@property
def session_id(self) -> str:
    """Get unique session ID (UUID)."""
```

**Returns**: `str` - Unique UUID for this conversation session

**Example**:
```python
print(f"Session: {context.session_id}")  # UUID string
```

### Methods

#### `add_message()`

```python
def add_message(
    self,
    role: str,
    content: str,
    participant_id: str | None = None,
) -> None:
    """Add message to history and auto-prune if limit exceeded.

    Args:
        role: Message role - "user", "assistant", or "system"
        content: Message text content
        participant_id: Optional ID of speaking participant

    Returns:
        None

    Raises:
        ValueError: If role not in {"user", "assistant", "system"}

    Behavior:
        - Appends message with current timestamp
        - If history exceeds max_history, removes oldest messages
        - Preserves chronological order
        - O(n) time complexity (n = max_history, typically 20)

    Example:
        context.add_message("user", "Hello there!")
        context.add_message("assistant", "Hello! How can I help?")
        context.add_message(
            "user",
            "What's the weather?",
            participant_id="user-123"
        )
    """
```

#### `get_history()`

```python
def get_history(self, limit: int | None = None) -> list[Message]:
    """Get conversation history with optional limit.

    Args:
        limit: Optional maximum number of messages to return.
               If None, returns all messages.

    Returns:
        list[Message]: List of Message objects (copy, not reference)

    Behavior:
        - Returns copy of history (modifications don't affect internal state)
        - Returns most recent 'limit' messages if limit specified
        - Returns empty list if no messages

    Example:
        # Get all messages
        history = context.get_history()

        # Get last 5 messages
        recent = context.get_history(limit=5)

        # Iterate over history
        for msg in context.get_history():
            print(f"{msg.role}: {msg.content}")
    """
```

#### `add_participant()`

```python
def add_participant(
    self,
    participant_id: str,
    name: str | None = None,
) -> None:
    """Add or update participant metadata.

    Args:
        participant_id: Unique participant identifier
        name: Human-readable participant name (optional)

    Returns:
        None

    Behavior:
        - Creates or overwrites participant metadata
        - Records join_time as current UTC time
        - Initializes empty preferences dictionary

    Example:
        context.add_participant("user-123", "Alice")
        context.add_participant("user-456", "Bob")
        context.add_participant("user-789")  # No name
    """
```

#### `get_participant()`

```python
def get_participant(
    self,
    participant_id: str,
) -> ParticipantMetadata | None:
    """Get participant metadata by ID.

    Args:
        participant_id: Unique participant identifier

    Returns:
        ParticipantMetadata or None if not found

    Example:
        participant = context.get_participant("user-123")
        if participant:
            print(f"Joined at: {participant.join_time}")
        else:
            print("Participant not found")
    """
```

#### `set_phase()`

```python
def set_phase(self, phase: ConversationPhase) -> None:
    """Update conversation phase with validation.

    Args:
        phase: Target ConversationPhase

    Returns:
        None

    Raises:
        ValueError: If transition is invalid

    Valid Transitions:
        GREETING → ACTIVE
        ACTIVE → CLOSING
        Any phase → itself (no-op, allowed)
        Invalid: GREETING → CLOSING, CLOSING → *

    Example:
        # Valid transitions
        context.set_phase(ConversationPhase.ACTIVE)
        context.set_phase(ConversationPhase.CLOSING)

        # Invalid (raises ValueError)
        context.set_phase(ConversationPhase.GREETING)  # From CLOSING
    """
```

#### `format_for_llm()`

```python
def format_for_llm(self) -> list[dict[str, str]]:
    """Format conversation history for LLM API.

    Returns OpenAI/Anthropic compatible message list with
    "role" and "content" keys only.

    Returns:
        list[dict[str, str]]: List of dicts with "role" and "content"

    Example Output:
        [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hello! How are you?"},
            {"role": "user", "content": "I'm doing well"}
        ]

    Usage:
        messages = context.format_for_llm()
        response = openai.chat.completions.create(
            model="gpt-4",
            messages=messages
        )
    """
```

#### `clear_history()`

```python
def clear_history(self) -> None:
    """Clear conversation history (for testing/reset).

    Returns:
        None

    Example:
        context.clear_history()
        assert len(context.get_history()) == 0
    """
```

---

## LLMIntegration

**Module**: `nora_livekit.conversation.llm`

**Purpose**: Integrate with LLM APIs (OpenAI, Anthropic) with retry logic and TTS formatting.

### Class Definition

```python
class LLMIntegration:
    """Handles LLM API integration for conversation generation.

    Satisfies: REQ-F-LLM-001, REQ-F-LLM-002, REQ-F-LLM-003,
               REQ-F-LLM-004, REQ-F-LLM-005, REQ-F-LLM-006, REQ-F-LLM-007
    """
```

### Constructor

```python
def __init__(
    self,
    provider: LLMProvider,
    api_key: str,
    model: str,
    temperature: float = 0.7,
    max_tokens: int = 150,
) -> None:
    """Initialize LLM integration with provider configuration.

    Args:
        provider: LLMProvider.OPENAI or LLMProvider.ANTHROPIC
        api_key: API key for the provider
        model: Model name (e.g., "gpt-4", "claude-3-sonnet-20240229")
        temperature: Sampling temperature, 0.0-1.0 (default: 0.7)
        max_tokens: Maximum tokens in response (default: 150)

    Raises:
        ValueError: If api_key is empty or provider invalid

    Example:
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
            temperature=0.5,
            max_tokens=200
        )
    """
```

### Properties

#### `provider`, `api_key`, `model`, `temperature`, `max_tokens`

```python
provider: LLMProvider
api_key: str
model: str
temperature: float
max_tokens: int
```

**Read-only properties** containing current configuration.

### Methods

#### `generate_response()`

```python
async def generate_response(
    self,
    context: ConversationContext,
    system_prompt: str | None = None,
) -> LLMResponse:
    """Generate response using LLM based on conversation context.

    Args:
        context: Current ConversationContext with message history
        system_prompt: Optional override for system prompt.
                      If None, uses phase-specific prompt.

    Returns:
        LLMResponse with text, tokens_used, latency_ms, model, finish_reason

    Raises:
        RuntimeError: On permanent API failure after retries

    Retry Behavior:
        - Retryable errors (429, 500, 503): Retry with exponential backoff
        - Backoff delays: 1s, 2s, 4s
        - Max attempts: 3
        - Falls back to fallback_response on permanent failure
        - Logs all retry attempts and errors

    Example:
        response = await llm.generate_response(context)
        print(f"Text: {response.text}")
        print(f"Tokens: {response.tokens_used}")
        print(f"Latency: {response.latency_ms}ms")
    """
```

#### `_construct_system_prompt()`

```python
def _construct_system_prompt(self, phase: ConversationPhase) -> str:
    """Construct phase-specific system prompt.

    Args:
        phase: Current ConversationPhase

    Returns:
        str: System prompt text

    Prompts:
        GREETING: "You are Nora, a friendly AI voice assistant.
                   The conversation is just starting. Greet the user..."
        ACTIVE:   "You are Nora, a helpful AI voice assistant.
                   Provide clear, concise answers..."
        CLOSING:  "The conversation is ending. Provide a brief..."

    Example:
        prompt = llm._construct_system_prompt(ConversationPhase.ACTIVE)
    """
```

#### `_format_for_tts()`

```python
def _format_for_tts(self, text: str) -> str:
    """Format LLM response for TTS compatibility.

    Removes markdown and formatting that TTS wouldn't handle well.

    Args:
        text: Raw LLM response

    Returns:
        str: Formatted text safe for TTS

    Transformations:
        - Removes **bold** → bold
        - Removes _italic_ → italic
        - Removes code blocks (```)
        - Removes inline code (`)
        - Removes markdown headers (#, ##)
        - Removes bullet points (-, *, +)
        - Removes numbered lists (1., 2.)
        - Collapses multiple line breaks
        - Removes extra whitespace

    Example:
        raw = "**Welcome!** Here's how to help:\n- Option 1\n- Option 2"
        formatted = llm._format_for_tts(raw)
        # Result: "Welcome! Here's how to help: Option 1 Option 2"
    """
```

---

## TurnManager

**Module**: `nora_livekit.conversation.turn_manager`

**Purpose**: Detect turn boundaries and interruptions using VAD.

### Class Definition

```python
class TurnManager:
    """Manages turn-taking detection and coordination.

    Satisfies: REQ-F-TURN-001, REQ-F-TURN-002, REQ-F-TURN-003,
               REQ-F-TURN-004, REQ-F-TURN-005
    """
```

### Constructor

```python
def __init__(
    self,
    vad_threshold: float = 0.5,
    min_speech_duration_ms: int = 300,
    silence_duration_ms: int = 700,
) -> None:
    """Initialize turn manager with VAD configuration.

    Args:
        vad_threshold: Voice activity confidence, 0.0-1.0 (default: 0.5)
        min_speech_duration_ms: Minimum speech duration, ms (default: 300)
        silence_duration_ms: Silence threshold for turn end, ms (default: 700)

    Example:
        tm = TurnManager(
            vad_threshold=0.5,
            min_speech_duration_ms=300,
            silence_duration_ms=700
        )
    """
```

### Properties

#### `agent_speaking`

```python
agent_speaking: bool
```

**Current state**: True if agent is currently speaking, False otherwise.

### Methods

#### `start()`

```python
async def start(self, audio_stream: AsyncIterator[bytes]) -> None:
    """Start monitoring audio stream for turn events.

    Args:
        audio_stream: Async iterator of audio bytes

    Returns:
        None

    Behavior:
        - Begins monitoring audio stream
        - Emits turn events based on VAD detection
        - Runs until explicitly stopped

    Example:
        async for audio_chunk in audio_source:
            await turn_manager.start(audio_chunk)
    """
```

#### `stop()`

```python
async def stop(self) -> None:
    """Stop turn detection and cleanup.

    Returns:
        None

    Example:
        await turn_manager.stop()
    """
```

#### `wait_for_turn()`

```python
async def wait_for_turn(self) -> TurnData:
    """Wait for next turn event (blocking).

    Returns:
        TurnData: Event details with timestamp and metadata

    Raises:
        NotImplementedError: In base class (implemented in subclasses)

    Behavior:
        - Blocks until next turn event detected
        - Returns event type, participant_id, timestamp
        - Can be cancelled via asyncio.CancelledError

    Example:
        turn = await turn_manager.wait_for_turn()
        if turn.event == TurnEvent.USER_TURN_END:
            print(f"User {turn.participant_id} finished speaking")
    """
```

#### `set_agent_speaking()`

```python
def set_agent_speaking(self, speaking: bool) -> None:
    """Notify turn manager when agent is speaking.

    Args:
        speaking: True if agent is speaking, False otherwise

    Returns:
        None

    Behavior:
        - When True, suppresses user turn detection
        - Enables interruption detection if enabled
        - Non-blocking, synchronous

    Example:
        # Before starting TTS
        turn_manager.set_agent_speaking(True)

        # After TTS finishes
        turn_manager.set_agent_speaking(False)
    """
```

---

## ConversationEngine

**Module**: `nora_livekit.conversation.engine`

**Purpose**: Orchestrate conversation flow, manage lifecycle.

### Class Definition

```python
class ConversationEngine:
    """Orchestrates conversation flow with context, LLM, and turn management.

    Satisfies: REQ-F-ENG-001, REQ-F-ENG-002, REQ-F-ENG-003,
               REQ-F-ENG-004, REQ-F-ENG-005, REQ-F-ENG-006, REQ-F-ENG-007
    """
```

### Constructor

```python
def __init__(
    self,
    config: ConversationEngineConfig,
    context: ConversationContext,
    llm: LLMIntegration,
    turn_manager: TurnManager,
) -> None:
    """Initialize conversation engine with dependencies.

    Args:
        config: ConversationEngineConfig with settings
        context: ConversationContext instance
        llm: LLMIntegration instance
        turn_manager: TurnManager instance

    Example:
        engine = ConversationEngine(
            config=ConversationEngineConfig(max_history=20),
            context=ConversationContext(),
            llm=LLMIntegration(...),
            turn_manager=TurnManager()
        )
    """
```

### Properties

#### `context`, `llm`, `turn_manager`, `participant_manager`, `config`

```python
context: ConversationContext
llm: LLMIntegration
turn_manager: TurnManager
participant_manager: ParticipantManager
config: ConversationEngineConfig
```

**Read-only access** to engine components.

### Methods

#### `start()`

```python
async def start(self) -> None:
    """Start conversation engine and generate initial greeting.

    Returns:
        None

    Behavior:
        - Initializes engine in GREETING phase
        - Generates greeting message via LLM
        - Starts idle timeout monitoring
        - Logs conversation start

    Example:
        await engine.start()
    """
```

#### `stop()`

```python
async def stop(self) -> None:
    """Stop conversation engine and cleanup.

    Returns:
        None

    Behavior:
        - Sets running flag to False
        - Cancels idle timeout task
        - Logs shutdown

    Example:
        await engine.stop()
    """
```

#### `process_transcription()`

```python
async def process_transcription(
    self,
    text: str,
    participant_id: str = "default",
) -> str:
    """Process transcribed text and generate response.

    This is the main entry point for conversation processing.
    Called by VoicePipeline._handle_transcription().

    Args:
        text: Transcribed user text
        participant_id: ID of speaking participant (default: "default")

    Returns:
        str: Response text for TTS synthesis

    Behavior:
        - Adds user message to context
        - Updates participant activity timestamp
        - Checks for phase transition (GREETING → ACTIVE)
        - Calls LLM to generate response
        - Adds response to context
        - Returns text for TTS
        - Falls back to fallback_response on error
        - Logs all operations

    Exceptions:
        - Caught and logged; returns fallback_response
        - Does not raise (graceful degradation)

    Example:
        response = await engine.process_transcription(
            text="What time is it?",
            participant_id="user-123"
        )
        # response: "It's 3:45 PM."
    """
```

#### `handle_turn_event()`

```python
async def handle_turn_event(self, turn_data: TurnData) -> None:
    """Handle turn-taking events from TurnManager.

    Args:
        turn_data: TurnData with event details

    Returns:
        None

    Behavior:
        - Processes USER_TURN_END, AGENT_TURN_START, etc.
        - Handles INTERRUPTION events
        - Stops current TTS if interrupted (via VoicePipeline)

    Example:
        await engine.handle_turn_event(turn_data)
    """
```

---

## ParticipantManager

**Module**: `nora_livekit.conversation.participant_manager`

**Purpose**: Track multiple participants in conversation room.

### Class Definition

```python
class ParticipantManager:
    """Manages multiple participants in conversation room.

    Satisfies: REQ-F-PART-001, REQ-F-PART-002, REQ-F-PART-003,
               REQ-F-PART-004, REQ-F-PART-005
    """
```

### Constructor

```python
def __init__(self, context: ConversationContext) -> None:
    """Initialize participant manager with conversation context.

    Args:
        context: ConversationContext instance for metadata storage

    Example:
        pm = ParticipantManager(context)
    """
```

### Methods

#### `add_participant()`

```python
def add_participant(
    self,
    participant_id: str,
    name: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Add new participant to conversation.

    Args:
        participant_id: Unique participant identifier
        name: Human-readable participant name (optional)
        metadata: Additional participant metadata (optional)

    Returns:
        None

    Behavior:
        - Records join_time as current UTC time
        - Initializes message_count to 0
        - Sets is_active to True
        - Also adds to ConversationContext
        - Logs participant join

    Example:
        pm.add_participant("user-123", "Alice")
        pm.add_participant("user-456", "Bob")
    """
```

#### `remove_participant()`

```python
def remove_participant(self, participant_id: str) -> None:
    """Mark participant as inactive (left conversation).

    Args:
        participant_id: Unique participant identifier

    Returns:
        None

    Behavior:
        - Sets is_active to False
        - Records leave_time as current UTC time
        - Logs participant leave
        - Does not delete participant record

    Example:
        pm.remove_participant("user-123")
    """
```

#### `update_activity()`

```python
def update_activity(self, participant_id: str) -> None:
    """Update participant's last activity timestamp.

    Args:
        participant_id: Unique participant identifier

    Returns:
        None

    Behavior:
        - Updates last_activity to current UTC time
        - Increments message_count
        - Called when participant speaks (message added)

    Example:
        pm.update_activity("user-123")
    """
```

#### `get_active_participants()`

```python
def get_active_participants(self) -> list[ParticipantActivity]:
    """Get list of currently active participants.

    Returns:
        list[ParticipantActivity]: Active participants sorted by join_time

    Example:
        active = pm.get_active_participants()
        for participant in active:
            print(f"{participant.participant_id}: {participant.message_count} messages")
    """
```

#### `get_participant_stats()`

```python
def get_participant_stats(
    self,
    participant_id: str,
) -> ParticipantActivity | None:
    """Get activity statistics for specific participant.

    Args:
        participant_id: Unique participant identifier

    Returns:
        ParticipantActivity or None if not found

    Example:
        stats = pm.get_participant_stats("user-123")
        if stats:
            print(f"Messages: {stats.message_count}")
            print(f"Joined: {stats.join_time}")
    """
```

---

## Data Classes

### Message

```python
@dataclass
class Message:
    """Represents a single conversation message."""

    role: Literal["user", "assistant", "system"]
    content: str
    timestamp: datetime
    participant_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
```

**Fields**:
- `role`: "user" (participant), "assistant" (AI), or "system" (control)
- `content`: Message text
- `timestamp`: UTC datetime when message was created
- `participant_id`: Optional participant ID for multi-user tracking
- `metadata`: Optional additional data

### ParticipantMetadata

```python
@dataclass
class ParticipantMetadata:
    """Metadata for a conversation participant."""

    participant_id: str
    name: str | None
    join_time: datetime
    preferences: dict[str, Any] = field(default_factory=dict)
```

**Fields**:
- `participant_id`: Unique identifier
- `name`: Optional human-readable name
- `join_time`: UTC datetime when participant joined
- `preferences`: Optional user preferences dictionary

### ParticipantActivity

```python
@dataclass
class ParticipantActivity:
    """Tracks participant activity in conversation."""

    participant_id: str
    join_time: datetime
    leave_time: datetime | None
    last_activity: datetime
    message_count: int
    is_active: bool
```

**Fields**:
- `participant_id`: Unique identifier
- `join_time`: When participant joined
- `leave_time`: When participant left (None if still active)
- `last_activity`: Last time participant spoke
- `message_count`: Total messages sent by participant
- `is_active`: Whether participant is currently active

### LLMResponse

```python
@dataclass
class LLMResponse:
    """Response from LLM API."""

    text: str
    tokens_used: int
    latency_ms: float
    model: str
    finish_reason: str
```

**Fields**:
- `text`: Generated response text (already formatted for TTS)
- `tokens_used`: Total tokens used (input + output)
- `latency_ms`: API latency in milliseconds
- `model`: Model name that generated response
- `finish_reason`: Reason for completion ("stop", "length", etc.)

### ConversationEngineConfig

```python
@dataclass
class ConversationEngineConfig:
    """Configuration for ConversationEngine."""

    max_history: int = 20
    idle_timeout_seconds: int = 120
    enable_interruptions: bool = True
    fallback_response: str = "I'm having trouble right now. Please try again."
```

**Fields**:
- `max_history`: Maximum messages in context
- `idle_timeout_seconds`: Seconds before auto-closing conversation
- `enable_interruptions`: Whether to allow user interruptions
- `fallback_response`: Response on LLM failure

### TurnData

```python
@dataclass
class TurnData:
    """Data associated with a turn event."""

    event: TurnEvent
    participant_id: str | None
    timestamp: datetime
    metadata: dict[str, Any] = field(default_factory=dict)
```

**Fields**:
- `event`: Type of turn event
- `participant_id`: Participant ID (if applicable)
- `timestamp`: When event occurred
- `metadata`: Additional event data

---

## Enums

### ConversationPhase

```python
class ConversationPhase(Enum):
    """Conversation lifecycle phases."""

    GREETING = "greeting"  # Initial greeting phase
    ACTIVE = "active"      # Main conversation phase
    CLOSING = "closing"    # Conversation ending phase
```

**Valid Transitions**:
- GREETING → ACTIVE
- ACTIVE → CLOSING
- Any phase → itself (no-op)

### LLMProvider

```python
class LLMProvider(Enum):
    """Supported LLM providers."""

    OPENAI = "openai"           # OpenAI API
    ANTHROPIC = "anthropic"     # Anthropic API
```

### TurnEvent

```python
class TurnEvent(Enum):
    """Turn-taking events."""

    USER_TURN_START = "user_turn_start"      # User started speaking
    USER_TURN_END = "user_turn_end"          # User stopped speaking
    AGENT_TURN_START = "agent_turn_start"    # Agent started speaking
    AGENT_TURN_END = "agent_turn_end"        # Agent stopped speaking
    INTERRUPTION = "interruption"             # User interrupted agent
```

---

## Exceptions

### LLMError (Custom)

```python
class LLMError(Exception):
    """Raised on permanent LLM API failure."""

    def __init__(self, message: str, status_code: int | None = None):
        self.status_code = status_code
        super().__init__(message)
```

**When Raised**:
- Permanent API errors (4xx non-429, connection failures)
- After all retry attempts exhausted
- Never raised in practice; caught and logged in `generate_response()`

### Standard Python Exceptions

- `ValueError`: Invalid arguments, invalid phase transitions
- `RuntimeError`: Engine not running, API failures
- `asyncio.TimeoutError`: Operation timeout
- `asyncio.CancelledError`: Operation cancelled

---

## Complete Usage Example

```python
import asyncio
from nora_livekit.conversation import (
    ConversationEngine, ConversationContext, LLMIntegration,
    TurnManager, ConversationEngineConfig, LLMProvider
)

async def main():
    # 1. Create components
    config = ConversationEngineConfig(
        max_history=20,
        idle_timeout_seconds=120,
        enable_interruptions=True
    )

    context = ConversationContext(max_history=20)

    llm = LLMIntegration(
        provider=LLMProvider.OPENAI,
        api_key="sk-...",
        model="gpt-4",
        temperature=0.7,
        max_tokens=150
    )

    turn_manager = TurnManager(
        vad_threshold=0.5,
        min_speech_duration_ms=300,
        silence_duration_ms=700
    )

    # 2. Create engine
    engine = ConversationEngine(
        config=config,
        context=context,
        llm=llm,
        turn_manager=turn_manager
    )

    # 3. Start conversation
    await engine.start()

    # 4. Add participants
    engine.participant_manager.add_participant("alice", "Alice")

    # 5. Process conversation
    response1 = await engine.process_transcription(
        "Hello, how are you?",
        participant_id="alice"
    )
    print(f"AI: {response1}")

    response2 = await engine.process_transcription(
        "What's the weather?",
        participant_id="alice"
    )
    print(f"AI: {response2}")

    # 6. Check stats
    stats = engine.participant_manager.get_participant_stats("alice")
    print(f"Messages: {stats.message_count}")

    # 7. Stop
    await engine.stop()

asyncio.run(main())
```

---

**Version**: 1.0.0
**Last Updated**: 2025-11-25
