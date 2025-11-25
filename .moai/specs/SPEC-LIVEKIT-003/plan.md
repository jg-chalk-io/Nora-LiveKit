# SPEC-LIVEKIT-003 Implementation Plan: Context & Conversation Engine

## Executive Summary

This implementation plan details the development of the Context & Conversation Engine for Nora LiveKit agent, building upon the completed foundation (SPEC-LIVEKIT-001) and voice pipeline (SPEC-LIVEKIT-002). This SPEC introduces intelligent conversation capabilities through LLM-powered response generation, in-memory context management, turn-taking detection, and multi-participant support.

**Strategic Importance**: Third critical SPEC in the 8-SPEC migration roadmap. Transforms the basic voice pipeline into an intelligent conversational agent capable of contextual, multi-turn interactions with natural turn-taking.

**User Decisions Implemented**:
- Conversation Logic: LLM-powered (leveraging SPEC-AGENT-001 patterns)
- Context Persistence: In-memory (simple session state)
- Turn-Taking: LiveKit turn detector plugin
- Scope: Moderate (greeting, Q&A, context-aware responses, conversation phases)

---

## Implementation Phases

### Phase 1: ConversationContext & State Management (Foundation)

**Priority**: P0 (Critical - Core data structures)
**Estimated LOC**: 120-150 (source) + 150-180 (tests)
**Dependencies**: None (foundation layer)

#### Components to Build

**1.1 ConversationContext Class** (`src/nora_livekit/conversation/context.py`)

**EARS Requirements**:
- **REQ-F-CTX-001**: WHEN ConversationContext is initialized, THEN it SHALL create an empty conversation history list and initialize participant metadata dictionary
- **REQ-F-CTX-002**: WHEN a message is added to context, THEN it SHALL append the message with role (user/assistant) and timestamp to conversation history
- **REQ-F-CTX-003**: WHEN conversation history exceeds max_history limit, THEN it SHALL remove oldest messages to maintain the limit
- **REQ-F-CTX-004**: WHEN participant metadata is requested, THEN it SHALL return participant info (name, join_time, preferences) or None if not found
- **REQ-F-CTX-005**: WHEN conversation phase is updated, THEN it SHALL transition through valid states (greeting → active → closing) and log the transition

**Class Structure**:
```python
@dataclass
class Message:
    """Represents a single conversation message."""
    role: Literal["user", "assistant", "system"]
    content: str
    timestamp: datetime
    participant_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass
class ParticipantMetadata:
    """Metadata for a conversation participant."""
    participant_id: str
    name: str | None
    join_time: datetime
    preferences: dict[str, Any] = field(default_factory=dict)

class ConversationPhase(Enum):
    """Conversation lifecycle phases."""
    GREETING = "greeting"
    ACTIVE = "active"
    CLOSING = "closing"

class ConversationContext:
    """Manages in-memory conversation state and history."""

    def __init__(self, max_history: int = 20) -> None:
        """Initialize conversation context with history limit."""
        self._history: list[Message] = []
        self._participants: dict[str, ParticipantMetadata] = {}
        self._phase: ConversationPhase = ConversationPhase.GREETING
        self._max_history = max_history
        self._session_id: str = str(uuid.uuid4())
        self._created_at: datetime = datetime.now(timezone.utc)

    def add_message(self, role: str, content: str, participant_id: str | None = None) -> None:
        """Add a message to conversation history."""

    def get_history(self, limit: int | None = None) -> list[Message]:
        """Get conversation history with optional limit."""

    def add_participant(self, participant_id: str, name: str | None = None) -> None:
        """Add or update participant metadata."""

    def get_participant(self, participant_id: str) -> ParticipantMetadata | None:
        """Get participant metadata by ID."""

    def set_phase(self, phase: ConversationPhase) -> None:
        """Update conversation phase."""

    def format_for_llm(self) -> list[dict[str, str]]:
        """Format conversation history for LLM API (OpenAI/Anthropic format)."""

    def clear_history(self) -> None:
        """Clear conversation history (useful for testing)."""
```

**Acceptance Criteria**:
- **AC-CTX-001**: Given ConversationContext is initialized, When max_history=20, Then history list is empty and max_history is set to 20
- **AC-CTX-002**: Given context with 25 messages and max_history=20, When new message added, Then oldest 5 messages are removed automatically
- **AC-CTX-003**: Given context with 10 messages, When format_for_llm() is called, Then returns list of dicts with "role" and "content" keys in OpenAI format
- **AC-CTX-004**: Given participant "user-123" with name "Alice" is added, When get_participant("user-123") is called, Then returns ParticipantMetadata with name="Alice"
- **AC-CTX-005**: Given context in GREETING phase, When set_phase(ACTIVE) is called, Then phase transitions to ACTIVE and log event is emitted

**Test Strategy**:
- Unit tests for message addition and history management
- Unit tests for participant metadata CRUD operations
- Unit tests for phase transitions and validation
- Unit tests for LLM format conversion
- Test coverage target: 95%+ (foundation code requires high coverage)

---

### Phase 2: LLM Integration (Response Generation)

**Priority**: P0 (Critical - Core intelligence)
**Estimated LOC**: 150-180 (source) + 200-250 (tests)
**Dependencies**: Phase 1 (ConversationContext), SPEC-AGENT-001 (reference patterns)

#### Components to Build

**2.1 LLMIntegration Class** (`src/nora_livekit/conversation/llm.py`)

**EARS Requirements**:
- **REQ-F-LLM-001**: WHEN LLMIntegration is initialized with provider="openai", THEN it SHALL create OpenAI client with API key from config
- **REQ-F-LLM-002**: WHEN LLMIntegration is initialized with provider="anthropic", THEN it SHALL create Anthropic client with API key from config
- **REQ-F-LLM-003**: WHEN generate_response() is called with conversation context, THEN it SHALL format history for LLM and call appropriate API
- **REQ-F-LLM-004**: WHEN LLM API call succeeds, THEN it SHALL return response text and log generation metrics (tokens, latency)
- **REQ-F-LLM-005**: WHEN LLM API call fails with retryable error, THEN it SHALL retry with exponential backoff (max 3 attempts)
- **REQ-F-LLM-006**: WHEN LLM API call fails permanently, THEN it SHALL return fallback response and log error
- **REQ-F-LLM-007**: WHEN prompt is constructed, THEN it SHALL include system prompt optimized for voice conversations
- **REQ-F-LLM-008**: WHEN response is generated, THEN it SHALL filter out markdown and format text for TTS compatibility

**Class Structure**:
```python
class LLMProvider(Enum):
    """Supported LLM providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"

@dataclass
class LLMResponse:
    """Response from LLM API."""
    text: str
    tokens_used: int
    latency_ms: float
    model: str
    finish_reason: str

class LLMIntegration:
    """Handles LLM API integration for conversation generation."""

    def __init__(
        self,
        provider: LLMProvider,
        api_key: str,
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 150,
    ) -> None:
        """Initialize LLM integration with provider and configuration."""

    async def generate_response(
        self,
        context: ConversationContext,
        system_prompt: str | None = None,
    ) -> LLMResponse:
        """Generate response using LLM based on conversation context."""

    def _construct_system_prompt(self, phase: ConversationPhase) -> str:
        """Construct system prompt based on conversation phase."""

    def _format_for_tts(self, text: str) -> str:
        """Format LLM response for TTS compatibility (remove markdown, etc)."""

    async def _call_openai(self, messages: list[dict]) -> LLMResponse:
        """Call OpenAI API with retry logic."""

    async def _call_anthropic(self, messages: list[dict]) -> LLMResponse:
        """Call Anthropic API with retry logic."""
```

**System Prompt Strategy**:
```python
VOICE_SYSTEM_PROMPTS = {
    ConversationPhase.GREETING: """You are Nora, a friendly AI voice assistant.
    The conversation is just starting. Greet the user warmly and ask how you can help.
    Keep responses SHORT (1-2 sentences) since this is a voice conversation.
    Avoid markdown, bullet points, or complex formatting.""",

    ConversationPhase.ACTIVE: """You are Nora, a helpful AI voice assistant.
    Provide clear, concise answers to user questions.
    Keep responses SHORT (2-3 sentences max) for voice conversations.
    Avoid markdown, lists, or complex formatting.
    Ask clarifying questions if needed.""",

    ConversationPhase.CLOSING: """You are Nora, a friendly AI voice assistant.
    The conversation is ending. Provide a brief closing statement.
    Keep it SHORT (1 sentence) and friendly.
    Avoid markdown or complex formatting.""",
}
```

**Acceptance Criteria**:
- **AC-LLM-001**: Given provider="openai" and valid API key, When LLMIntegration is initialized, Then OpenAI client is created successfully
- **AC-LLM-002**: Given provider="anthropic" and valid API key, When LLMIntegration is initialized, Then Anthropic client is created successfully
- **AC-LLM-003**: Given context with 5 messages in GREETING phase, When generate_response() is called, Then system prompt includes greeting instructions
- **AC-LLM-004**: Given LLM returns "Hello! **How** can I help?", When _format_for_tts() is applied, Then result is "Hello! How can I help?"
- **AC-LLM-005**: Given OpenAI API call fails with 429 error, When generate_response() is called, Then retries with backoff (1s, 2s, 4s delays)
- **AC-LLM-006**: Given all retry attempts fail, When generate_response() is called, Then returns fallback response "I'm having trouble right now. Please try again."
- **AC-LLM-007**: Given successful LLM call taking 450ms, When generate_response() completes, Then logs metrics with latency_ms=450

**Test Strategy**:
- Unit tests with mocked OpenAI/Anthropic clients
- Test system prompt construction for each phase
- Test TTS formatting (markdown removal, text normalization)
- Test retry logic with simulated API failures
- Test fallback behavior for permanent failures
- Integration tests with real API calls (optional, gated by env var)
- Test coverage target: 90%+

**Configuration Extension**:
```python
@dataclass
class ConversationConfig:
    """Conversation engine configuration."""
    llm_provider: str = "openai"  # or "anthropic"
    llm_api_key: str = ""
    llm_model: str = "gpt-4"  # or "claude-3-sonnet-20240229"
    llm_temperature: float = 0.7
    llm_max_tokens: int = 150
    max_history: int = 20
    fallback_response: str = "I'm having trouble right now. Please try again."
```

---

### Phase 3: TurnManager (Turn Detection & Management)

**Priority**: P1 (High - Natural conversation flow)
**Estimated LOC**: 100-120 (source) + 130-150 (tests)
**Dependencies**: Phase 1 (ConversationContext)

#### Components to Build

**3.1 TurnManager Class** (`src/nora_livekit/conversation/turn_manager.py`)

**EARS Requirements**:
- **REQ-F-TURN-001**: WHEN TurnManager is initialized, THEN it SHALL configure livekit-plugins-turn-detector with VAD settings
- **REQ-F-TURN-002**: WHEN user speech ends (turn detected), THEN it SHALL emit turn_complete event with transcribed text
- **REQ-F-TURN-003**: WHEN user interrupts agent speech, THEN it SHALL emit interruption event and stop current TTS playback
- **REQ-F-TURN-004**: WHEN agent is speaking, THEN it SHALL prevent new turn detection until speech completes
- **REQ-F-TURN-005**: WHEN turn detection fails, THEN it SHALL log error and continue monitoring without crashing

**Class Structure**:
```python
class TurnEvent(Enum):
    """Turn-taking events."""
    USER_TURN_START = "user_turn_start"
    USER_TURN_END = "user_turn_end"
    AGENT_TURN_START = "agent_turn_start"
    AGENT_TURN_END = "agent_turn_end"
    INTERRUPTION = "interruption"

@dataclass
class TurnData:
    """Data associated with a turn event."""
    event: TurnEvent
    participant_id: str | None
    timestamp: datetime
    metadata: dict[str, Any] = field(default_factory=dict)

class TurnManager:
    """Manages turn-taking detection and coordination."""

    def __init__(
        self,
        vad_threshold: float = 0.5,
        min_speech_duration_ms: int = 300,
        silence_duration_ms: int = 700,
    ) -> None:
        """Initialize turn manager with VAD configuration."""

    async def start(self, audio_stream: AsyncIterator[bytes]) -> None:
        """Start monitoring audio stream for turn-taking events."""

    async def stop(self) -> None:
        """Stop turn detection and cleanup."""

    async def wait_for_turn(self) -> TurnData:
        """Wait for next turn event (blocking)."""

    def set_agent_speaking(self, speaking: bool) -> None:
        """Notify turn manager when agent is speaking."""

    async def _detect_turns(self, audio_stream: AsyncIterator[bytes]) -> None:
        """Internal turn detection loop using livekit-plugins-turn-detector."""

    async def _handle_vad_event(self, event: Any) -> None:
        """Handle VAD events from turn detector plugin."""
```

**Turn Detector Integration** (using livekit-plugins-turn-detector):
```python
from livekit.plugins import turn_detector

# In TurnManager._detect_turns():
detector = turn_detector.TurnDetector(
    vad_threshold=self._vad_threshold,
    min_speech_duration=self._min_speech_duration_ms,
    silence_duration=self._silence_duration_ms,
)

async for vad_event in detector.detect(audio_stream):
    if vad_event.type == "speech_start":
        # User started speaking
        await self._emit_event(TurnEvent.USER_TURN_START)
    elif vad_event.type == "speech_end":
        # User stopped speaking (end of turn)
        await self._emit_event(TurnEvent.USER_TURN_END)
    elif vad_event.type == "interruption":
        # User interrupted agent
        await self._emit_event(TurnEvent.INTERRUPTION)
```

**Acceptance Criteria**:
- **AC-TURN-001**: Given TurnManager with vad_threshold=0.5, When user speaks for 400ms then 800ms silence, Then USER_TURN_END event is emitted
- **AC-TURN-002**: Given agent is speaking (set_agent_speaking=True), When user starts speaking, Then INTERRUPTION event is emitted
- **AC-TURN-003**: Given agent is speaking, When INTERRUPTION event occurs, Then agent speech stops immediately
- **AC-TURN-004**: Given turn detector encounters audio processing error, When error is caught, Then logs error and continues monitoring
- **AC-TURN-005**: Given multiple rapid speech bursts within 500ms, When detected, Then treats as single turn (not multiple turns)

**Test Strategy**:
- Unit tests with synthetic audio streams
- Test turn detection with various speech patterns
- Test interruption handling
- Test error recovery
- Mock livekit-plugins-turn-detector for deterministic testing
- Test coverage target: 90%+

---

### Phase 4: ConversationEngine (Orchestration)

**Priority**: P0 (Critical - Integration layer)
**Estimated LOC**: 180-220 (source) + 250-300 (tests)
**Dependencies**: Phases 1-3 (ConversationContext, LLMIntegration, TurnManager)

#### Components to Build

**4.1 ConversationEngine Class** (`src/nora_livekit/conversation/engine.py`)

**EARS Requirements**:
- **REQ-F-ENG-001**: WHEN ConversationEngine is initialized, THEN it SHALL create ConversationContext, LLMIntegration, and TurnManager instances
- **REQ-F-ENG-002**: WHEN engine.start() is called, THEN it SHALL initialize conversation with greeting phase
- **REQ-F-ENG-003**: WHEN USER_TURN_END event occurs, THEN it SHALL add user message to context and call LLM to generate response
- **REQ-F-ENG-004**: WHEN LLM response is received, THEN it SHALL add assistant message to context and return response text
- **REQ-F-ENG-005**: WHEN INTERRUPTION event occurs, THEN it SHALL stop current TTS playback and handle user input
- **REQ-F-ENG-006**: WHEN conversation has been idle for configured timeout, THEN it SHALL transition to closing phase
- **REQ-F-ENG-007**: WHEN conversation phase transitions occur, THEN it SHALL update context phase and adjust LLM system prompt

**Class Structure**:
```python
class ConversationEngine:
    """Orchestrates conversation flow with context, LLM, and turn management."""

    def __init__(
        self,
        config: ConversationConfig,
        context: ConversationContext,
        llm: LLMIntegration,
        turn_manager: TurnManager,
    ) -> None:
        """Initialize conversation engine with dependencies."""

    async def start(self) -> None:
        """Start conversation engine and generate initial greeting."""

    async def stop(self) -> None:
        """Stop conversation engine and cleanup."""

    async def process_transcription(self, text: str, participant_id: str) -> str:
        """Process transcribed text and generate response.

        This is the main entry point for conversation processing.
        Called by VoicePipeline._handle_transcription().
        """

    async def handle_turn_event(self, turn_data: TurnData) -> None:
        """Handle turn-taking events from TurnManager."""

    async def _generate_greeting(self) -> str:
        """Generate initial greeting message."""

    async def _handle_idle_timeout(self) -> None:
        """Handle conversation idle timeout and transition to closing."""

    def _should_transition_to_active(self) -> bool:
        """Check if conversation should transition from greeting to active."""

    def _should_transition_to_closing(self) -> bool:
        """Check if conversation should transition to closing phase."""
```

**Integration with VoicePipeline**:
```python
# Modification to VoicePipeline._generate_response() in pipeline.py
async def _generate_response(self, text: str, participant_id: str = "") -> str:
    """Generate response using ConversationEngine.

    Previously: Simple echo response
    Now: Full conversation logic with context and LLM
    """
    if self.conversation_engine:
        # Use conversation engine (SPEC-003)
        response = await self.conversation_engine.process_transcription(
            text=text,
            participant_id=participant_id,
        )
        return response
    else:
        # Fallback to echo (for testing without conversation engine)
        return f"You said: {text}"
```

**Acceptance Criteria**:
- **AC-ENG-001**: Given engine starts in GREETING phase, When first user message is received, Then LLM uses greeting system prompt
- **AC-ENG-002**: Given context has 3 user messages in GREETING, When next message is processed, Then phase transitions to ACTIVE
- **AC-ENG-003**: Given user says "hello", When process_transcription() is called, Then returns LLM-generated greeting response
- **AC-ENG-004**: Given conversation has 5 messages in history, When process_transcription() is called, Then LLM receives all 5 messages for context
- **AC-ENG-005**: Given agent is speaking response, When INTERRUPTION event occurs, Then current response stops and new user input is processed
- **AC-ENG-006**: Given conversation idle for 2 minutes (configurable), When timeout occurs, Then phase transitions to CLOSING
- **AC-ENG-007**: Given conversation in CLOSING phase, When user says "goodbye", Then generates closing response

**Test Strategy**:
- Integration tests with mocked LLM and TurnManager
- Test conversation flow: greeting → active → closing
- Test context accumulation across multiple turns
- Test interruption handling
- Test idle timeout transitions
- Test error recovery
- Test coverage target: 90%+

---

### Phase 5: ParticipantManager (Multi-Participant Support)

**Priority**: P2 (Medium - Multi-participant features)
**Estimated LOC**: 80-100 (source) + 100-120 (tests)
**Dependencies**: Phase 1 (ConversationContext)

#### Components to Build

**5.1 ParticipantManager Class** (`src/nora_livekit/conversation/participant_manager.py`)

**EARS Requirements**:
- **REQ-F-PART-001**: WHEN participant joins room, THEN it SHALL add participant to context with join timestamp
- **REQ-F-PART-002**: WHEN participant leaves room, THEN it SHALL update participant metadata with leave timestamp
- **REQ-F-PART-003**: WHEN participant speaks, THEN it SHALL update last_activity timestamp
- **REQ-F-PART-004**: WHEN multiple participants are active, THEN it SHALL track per-participant conversation state
- **REQ-F-PART-005**: WHEN participant list is requested, THEN it SHALL return list of active participants sorted by join time

**Class Structure**:
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

class ParticipantManager:
    """Manages multiple participants in conversation room."""

    def __init__(self, context: ConversationContext) -> None:
        """Initialize participant manager with conversation context."""

    def add_participant(
        self,
        participant_id: str,
        name: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Add new participant to conversation."""

    def remove_participant(self, participant_id: str) -> None:
        """Mark participant as inactive (left conversation)."""

    def update_activity(self, participant_id: str) -> None:
        """Update participant's last activity timestamp."""

    def get_active_participants(self) -> list[ParticipantActivity]:
        """Get list of currently active participants."""

    def get_participant_stats(self, participant_id: str) -> ParticipantActivity | None:
        """Get activity statistics for specific participant."""
```

**Integration with ConversationEngine**:
```python
# In ConversationEngine.process_transcription():
# Update participant activity
self.participant_manager.update_activity(participant_id)

# In VoicePipeline when LiveKit room events occur:
async def _handle_participant_connected(self, participant: rtc.Participant) -> None:
    """Handle new participant joining room."""
    self.conversation_engine.participant_manager.add_participant(
        participant_id=participant.sid,
        name=participant.name,
    )

async def _handle_participant_disconnected(self, participant: rtc.Participant) -> None:
    """Handle participant leaving room."""
    self.conversation_engine.participant_manager.remove_participant(
        participant_id=participant.sid,
    )
```

**Acceptance Criteria**:
- **AC-PART-001**: Given participant "user-123" joins, When add_participant() is called, Then participant appears in active participants list
- **AC-PART-002**: Given participant "user-123" leaves, When remove_participant() is called, Then is_active=False and leave_time is set
- **AC-PART-003**: Given participant "user-123" speaks, When update_activity() is called, Then last_activity timestamp is updated to current time
- **AC-PART-004**: Given 3 participants in room, When get_active_participants() is called, Then returns list of 3 participants sorted by join time
- **AC-PART-005**: Given participant has sent 5 messages, When get_participant_stats() is called, Then message_count=5

**Test Strategy**:
- Unit tests for participant lifecycle (join, leave, activity)
- Test multi-participant scenarios
- Test activity tracking and statistics
- Test edge cases (duplicate adds, remove non-existent participant)
- Test coverage target: 90%+

---

## Configuration Integration

### Extended Config Structure

**File**: `src/nora_livekit/config.py`

```python
@dataclass
class ConversationConfig:
    """Conversation engine configuration."""
    # LLM Configuration
    llm_provider: str = "openai"  # "openai" or "anthropic"
    llm_api_key: str = ""
    llm_model: str = "gpt-4"  # or "claude-3-sonnet-20240229"
    llm_temperature: float = 0.7
    llm_max_tokens: int = 150

    # Context Configuration
    max_history: int = 20

    # Turn Detection Configuration
    vad_threshold: float = 0.5
    min_speech_duration_ms: int = 300
    silence_duration_ms: int = 700

    # Conversation Behavior
    idle_timeout_seconds: int = 120  # 2 minutes
    enable_interruptions: bool = True
    fallback_response: str = "I'm having trouble right now. Please try again."

@dataclass
class Config:
    # Existing fields from SPEC-001 and SPEC-002
    livekit_url: str
    livekit_api_key: str
    livekit_api_secret: str
    health_check_port: int = 8080
    log_level: str = "INFO"
    log_format: str = "json"
    test_room: str | None = None
    voice: VoiceConfig | None = None

    # NEW: Conversation configuration
    conversation: ConversationConfig | None = None

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        # ... existing code ...

        # Load conversation configuration if LLM API key is present
        conversation_config = None
        llm_api_key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")

        if llm_api_key:
            llm_provider = os.getenv("LLM_PROVIDER", "openai")

            conversation_config = ConversationConfig(
                llm_provider=llm_provider,
                llm_api_key=llm_api_key,
                llm_model=os.getenv(
                    "LLM_MODEL",
                    "gpt-4" if llm_provider == "openai" else "claude-3-sonnet-20240229"
                ),
                llm_temperature=float(os.getenv("LLM_TEMPERATURE", "0.7")),
                llm_max_tokens=int(os.getenv("LLM_MAX_TOKENS", "150")),
                max_history=int(os.getenv("CONVERSATION_MAX_HISTORY", "20")),
                vad_threshold=float(os.getenv("VAD_THRESHOLD", "0.5")),
                min_speech_duration_ms=int(os.getenv("MIN_SPEECH_DURATION_MS", "300")),
                silence_duration_ms=int(os.getenv("SILENCE_DURATION_MS", "700")),
                idle_timeout_seconds=int(os.getenv("IDLE_TIMEOUT_SECONDS", "120")),
                enable_interruptions=os.getenv("ENABLE_INTERRUPTIONS", "true").lower() == "true",
                fallback_response=os.getenv(
                    "FALLBACK_RESPONSE",
                    "I'm having trouble right now. Please try again."
                ),
            )

        return cls(
            # ... existing fields ...
            conversation=conversation_config,
        )
```

### Environment Variables

**New Required Variables**:
```env
# LLM Configuration (REQUIRED)
LLM_PROVIDER=openai                    # or "anthropic"
LLM_API_KEY=sk-...                     # OpenAI or Anthropic API key
OPENAI_API_KEY=sk-...                  # Alternative: OpenAI-specific key
ANTHROPIC_API_KEY=sk-ant-...           # Alternative: Anthropic-specific key

# LLM Model Selection
LLM_MODEL=gpt-4                        # OpenAI: gpt-4, gpt-3.5-turbo
                                       # Anthropic: claude-3-sonnet-20240229, claude-3-opus-20240229
LLM_TEMPERATURE=0.7                    # 0.0-1.0 (default: 0.7)
LLM_MAX_TOKENS=150                     # Max response tokens (default: 150)

# Conversation Settings (OPTIONAL)
CONVERSATION_MAX_HISTORY=20            # Max messages in context (default: 20)
IDLE_TIMEOUT_SECONDS=120               # Conversation idle timeout (default: 120s)
ENABLE_INTERRUPTIONS=true              # Allow user interruptions (default: true)
FALLBACK_RESPONSE="I'm having trouble right now. Please try again."

# Turn Detection Settings (OPTIONAL - use voice config defaults)
VAD_THRESHOLD=0.5                      # Voice activity threshold (0.0-1.0)
MIN_SPEECH_DURATION_MS=300             # Min speech duration to count as turn (default: 300ms)
SILENCE_DURATION_MS=700                # Silence duration to end turn (default: 700ms)
```

---

## Testing Strategy

### Unit Test Coverage

**Phase 1 - ConversationContext** (`tests/conversation/test_context.py`):
- ✅ Test message addition and history management
- ✅ Test automatic pruning when max_history exceeded
- ✅ Test participant metadata CRUD operations
- ✅ Test conversation phase transitions
- ✅ Test LLM format conversion
- ✅ Test edge cases (empty history, invalid phase transitions)
- **Target Coverage**: 95%+

**Phase 2 - LLMIntegration** (`tests/conversation/test_llm.py`):
- ✅ Test OpenAI client initialization and calls
- ✅ Test Anthropic client initialization and calls
- ✅ Test system prompt construction for each phase
- ✅ Test TTS formatting (markdown removal)
- ✅ Test retry logic with simulated failures
- ✅ Test fallback behavior on permanent errors
- ✅ Test token counting and latency tracking
- **Target Coverage**: 90%+

**Phase 3 - TurnManager** (`tests/conversation/test_turn_manager.py`):
- ✅ Test turn detection with synthetic audio
- ✅ Test interruption handling
- ✅ Test agent speaking state management
- ✅ Test error recovery
- ✅ Test edge cases (rapid speech bursts, silence)
- **Target Coverage**: 90%+

**Phase 4 - ConversationEngine** (`tests/conversation/test_engine.py`):
- ✅ Test engine initialization and startup
- ✅ Test greeting generation
- ✅ Test transcription processing with context accumulation
- ✅ Test phase transitions (greeting → active → closing)
- ✅ Test idle timeout handling
- ✅ Test interruption handling
- **Target Coverage**: 90%+

**Phase 5 - ParticipantManager** (`tests/conversation/test_participant_manager.py`):
- ✅ Test participant lifecycle (join, leave)
- ✅ Test activity tracking
- ✅ Test multi-participant scenarios
- ✅ Test participant statistics
- **Target Coverage**: 90%+

### Integration Tests

**Integration Test Suite** (`tests/conversation/test_integration.py`):

**Test Scenario 1: End-to-End Greeting Flow**
```python
async def test_greeting_flow():
    """Test complete greeting conversation flow.

    Given: Engine starts with empty context
    When: User says "hello"
    Then:
      - Context enters GREETING phase
      - LLM generates greeting response
      - Response is formatted for TTS
      - Context transitions to ACTIVE after 2nd message
    """
```

**Test Scenario 2: Multi-Turn Contextual Conversation**
```python
async def test_multi_turn_context():
    """Test context retention across multiple turns.

    Given: Conversation with 5 previous messages
    When: User asks follow-up question
    Then:
      - LLM receives all 5 messages for context
      - Response is contextually relevant
      - New message added to context
    """
```

**Test Scenario 3: Interruption Handling**
```python
async def test_interruption_flow():
    """Test user interruption of agent response.

    Given: Agent is speaking response
    When: User starts speaking (interruption detected)
    Then:
      - TTS playback stops immediately
      - New user input is processed
      - New response generated without delay
    """
```

**Test Scenario 4: Conversation Lifecycle**
```python
async def test_conversation_lifecycle():
    """Test complete conversation lifecycle: greeting → active → closing.

    Given: Engine starts
    When: Greeting → 5 active turns → idle timeout
    Then:
      - Phase transitions correctly
      - Context accumulates all messages
      - Closing response generated
    """
```

**Test Scenario 5: Multi-Participant Support**
```python
async def test_multi_participant():
    """Test conversation with multiple participants.

    Given: 3 participants join room
    When: Each participant speaks in turn
    Then:
      - All participants tracked correctly
      - Activity timestamps updated
      - Conversation context includes all messages
    """
```

### Performance Tests

**Performance Benchmarks** (`tests/conversation/test_performance.py`):

**Benchmark 1: LLM Response Latency**
- Target: <1000ms for LLM API call (95th percentile)
- Measure: Time from process_transcription() call to response returned
- Test with: 100 sample requests with varying context sizes

**Benchmark 2: Context Operation Performance**
- Target: <10ms for add_message() operation
- Target: <5ms for get_history() operation
- Target: <5ms for format_for_llm() operation
- Measure: Operation execution time over 1000 iterations

**Benchmark 3: Turn Detection Latency**
- Target: <100ms from speech end to turn_complete event
- Measure: Time from audio silence to event emission
- Test with: Synthetic audio with known silence points

**Benchmark 4: Memory Usage**
- Target: <50MB memory for 20-message conversation context
- Measure: Memory consumption during 100-turn conversation
- Ensure no memory leaks over extended sessions

---

## Dependencies & Technology Stack

### New Python Dependencies

```toml
[tool.poetry.dependencies]
# Existing from SPEC-001 and SPEC-002
python = "^3.12"
livekit-agents = {version = "~1.0", extras = ["openai", "deepgram", "cartesia", "turn-detector"]}
fastapi = "~0.115"
uvicorn = {version = "~0.32", extras = ["standard"]}
python-dotenv = "~1.0"
structlog = "~24.4"
httpx = "~0.27"
deepgram-sdk = "~5.3"
cartesia = "~2.0.17"
numpy = "~2.0"
soundfile = "~0.12"

# NEW: Conversation & LLM dependencies
openai = "~1.54"                       # OpenAI API client
anthropic = "~0.39"                    # Anthropic API client
tenacity = "~9.0"                      # Retry logic with exponential backoff

[tool.poetry.group.dev.dependencies]
# Existing testing dependencies
pytest = "~8.3"
pytest-asyncio = "~0.24"
pytest-cov = "~6.0"
pytest-mock = "~3.14"
mypy = "~1.13"
ruff = "~0.8"
black = "~24.10"

# NEW: Additional testing tools
pytest-timeout = "~2.3"                # Timeout tests for async operations
pytest-benchmark = "~5.1"              # Performance benchmarking
respx = "~0.21"                        # HTTP mocking for API tests
```

### External Service Dependencies

**Required APIs**:
- OpenAI API (gpt-4, gpt-3.5-turbo) OR Anthropic API (claude-3-sonnet, claude-3-opus)
- Deepgram API (from SPEC-002)
- Cartesia Sonic API (from SPEC-002)
- LiveKit Cloud (from SPEC-001)

**Cost Considerations**:
- OpenAI gpt-4: ~$0.03 per 1K input tokens, ~$0.06 per 1K output tokens
- OpenAI gpt-3.5-turbo: ~$0.001 per 1K input tokens, ~$0.002 per 1K output tokens
- Anthropic claude-3-sonnet: ~$0.003 per 1K input tokens, ~$0.015 per 1K output tokens
- Estimated cost per conversation (20 messages, 150 tokens/response): $0.05-$0.15

---

## Risk Assessment & Mitigation

| Risk ID | Risk Description | Impact | Probability | Mitigation Strategy | Phase |
|---------|------------------|--------|-------------|---------------------|-------|
| RISK-CONV-001 | LLM API latency exceeds 1s, degrading conversation flow | High | Medium | Implement request timeout (2s), use streaming responses, optimize context size | Phase 2 |
| RISK-CONV-002 | LLM API rate limits hit during testing/production | Medium | High | Implement token bucket rate limiting, add backoff retry logic, monitor usage | Phase 2 |
| RISK-CONV-003 | Conversation context grows too large for LLM context window | High | Medium | Implement automatic context pruning, summarize old messages, enforce max_history | Phase 1 |
| RISK-CONV-004 | Turn detector false positives cause premature responses | Medium | Medium | Tune VAD thresholds, require minimum speech duration (300ms), test extensively | Phase 3 |
| RISK-CONV-005 | Memory leaks from accumulated conversation state | High | Low | Implement context cleanup on session end, monitor memory usage, profile code | Phase 1 |
| RISK-CONV-006 | LLM generates responses incompatible with TTS | Medium | Medium | Implement robust TTS formatting, validate response format, test with edge cases | Phase 2 |
| RISK-CONV-007 | Interruption handling causes state corruption | High | Low | Implement proper async cancellation, use locks for state updates, test race conditions | Phase 4 |
| RISK-CONV-008 | Multi-participant conversations cause context confusion | Medium | Low | Implement per-participant context isolation, test multi-participant scenarios | Phase 5 |

---

## Implementation Timeline & Milestones

### Development Approach

**TDD Methodology**: All phases follow RED-GREEN-REFACTOR cycle
1. **RED**: Write failing tests for acceptance criteria
2. **GREEN**: Implement minimal code to pass tests
3. **REFACTOR**: Clean up, optimize, ensure 90%+ coverage

### Milestones

**Milestone 1: Foundation (Phases 1-2)**
- ✅ ConversationContext with message history and phase management
- ✅ LLMIntegration with OpenAI/Anthropic support
- ✅ Configuration extension with ConversationConfig
- **Success Criteria**: Unit tests pass with 90%+ coverage, basic LLM response generation works

**Milestone 2: Turn Detection (Phase 3)**
- ✅ TurnManager with livekit-plugins-turn-detector integration
- ✅ Turn event handling and interruption detection
- **Success Criteria**: Turn detection works with synthetic audio, interruptions handled correctly

**Milestone 3: Engine Integration (Phase 4)**
- ✅ ConversationEngine orchestrates all components
- ✅ VoicePipeline integration (modify _generate_response())
- ✅ End-to-end conversation flow working
- **Success Criteria**: Complete conversation flow (greeting → active → closing) works in integration tests

**Milestone 4: Multi-Participant (Phase 5)**
- ✅ ParticipantManager tracks multiple participants
- ✅ LiveKit room event handling (join/leave)
- **Success Criteria**: Multi-participant scenarios tested and working

**Milestone 5: Testing & Optimization**
- ✅ Integration tests for all conversation scenarios
- ✅ Performance benchmarks meet targets
- ✅ Documentation complete
- **Success Criteria**: All tests pass, 90%+ coverage, performance targets met

---

## Integration Points

### VoicePipeline Modifications

**File**: `src/nora_livekit/voice/pipeline.py`

**Required Changes**:

1. **Add ConversationEngine dependency** (constructor):
```python
def __init__(
    self,
    config: Config,
    stt: DeepgramSTT,
    tts: CartesiaTTS,
    audio_handler: AudioHandler,
    conversation_engine: ConversationEngine | None = None,  # NEW
) -> None:
    self.config = config
    self.stt = stt
    self.tts = tts
    self.audio_handler = audio_handler
    self.conversation_engine = conversation_engine  # NEW
    self._running = False
```

2. **Modify _generate_response()** (replace echo with conversation logic):
```python
async def _generate_response(self, text: str, participant_id: str = "") -> str:
    """Generate response using ConversationEngine."""
    if self.conversation_engine:
        response = await self.conversation_engine.process_transcription(
            text=text,
            participant_id=participant_id,
        )
        return response
    else:
        # Fallback for testing without conversation engine
        return f"You said: {text}"
```

3. **Integrate TurnManager** (in process_audio_stream()):
```python
async def process_audio_stream(self, participant_id: str = "") -> None:
    """Process audio with turn detection."""
    if not self._running:
        raise RuntimeError("Voice pipeline not running")

    # Start turn manager
    if self.conversation_engine:
        audio_stream = self.audio_handler.subscribe_to_participant_audio(participant_id)
        await self.conversation_engine.turn_manager.start(audio_stream)

        # Listen for turn events
        async for turn_data in self.conversation_engine.turn_manager.wait_for_turn():
            if turn_data.event == TurnEvent.USER_TURN_END:
                # Process transcription when user finishes speaking
                await self._handle_transcription(turn_data.text, participant_id)
```

### NoraAgent Integration

**File**: `src/nora_livekit/agent.py`

**Required Changes**:

1. **Initialize ConversationEngine** (in agent startup):
```python
async def entrypoint(ctx: JobContext):
    """Agent entrypoint with conversation engine initialization."""
    config = Config.from_env()

    # Initialize voice pipeline (SPEC-002)
    stt = DeepgramSTT(...)
    tts = CartesiaTTS(...)
    audio_handler = AudioHandler(ctx.room)

    # NEW: Initialize conversation engine (SPEC-003)
    conversation_engine = None
    if config.conversation:
        context = ConversationContext(max_history=config.conversation.max_history)
        llm = LLMIntegration(
            provider=LLMProvider(config.conversation.llm_provider),
            api_key=config.conversation.llm_api_key,
            model=config.conversation.llm_model,
            temperature=config.conversation.llm_temperature,
            max_tokens=config.conversation.llm_max_tokens,
        )
        turn_manager = TurnManager(
            vad_threshold=config.conversation.vad_threshold,
            min_speech_duration_ms=config.conversation.min_speech_duration_ms,
            silence_duration_ms=config.conversation.silence_duration_ms,
        )
        conversation_engine = ConversationEngine(
            config=config.conversation,
            context=context,
            llm=llm,
            turn_manager=turn_manager,
        )
        await conversation_engine.start()

    # Initialize voice pipeline with conversation engine
    pipeline = VoicePipeline(
        config=config,
        stt=stt,
        tts=tts,
        audio_handler=audio_handler,
        conversation_engine=conversation_engine,  # NEW
    )
    await pipeline.start()
```

---

## Documentation Requirements

### Code Documentation

**Each module requires**:
- Module-level docstring explaining purpose and responsibilities
- Class docstrings with EARS-style requirements references
- Method docstrings with Args, Returns, Raises sections
- Type hints for all parameters and return values
- Inline comments for complex logic

### Architecture Documentation

**Create**: `docs/CONVERSATION_ENGINE.md`

**Contents**:
- Architecture diagram showing component relationships
- Data flow diagram: Audio → STT → Context → LLM → TTS
- Conversation state machine diagram
- LLM prompt strategy explanation
- Turn detection algorithm explanation
- Error handling and retry strategies
- Configuration guide with examples

### API Documentation

**Create**: `docs/CONVERSATION_API.md`

**Contents**:
- ConversationEngine public API reference
- Configuration options and environment variables
- Usage examples and code snippets
- Integration guide for custom implementations
- Troubleshooting guide

---

## Success Metrics

### Functional Metrics

**FM-001**: Conversation engine successfully generates contextually relevant responses
- **Verification**: Manual testing with sample conversations
- **Target**: >90% subjective response quality rating

**FM-002**: Turn detection accurately identifies speech boundaries
- **Verification**: Automated tests with synthetic audio
- **Target**: >95% turn detection accuracy

**FM-003**: Conversation phase transitions work correctly
- **Verification**: Integration tests covering all phase transitions
- **Target**: 100% test pass rate

**FM-004**: Multi-participant support tracks all participants correctly
- **Verification**: Multi-participant integration tests
- **Target**: 100% participant tracking accuracy

### Performance Metrics

**PM-001**: LLM response latency <1000ms at 95th percentile
- **Verification**: Performance benchmark tests
- **Target**: 95th percentile <1000ms

**PM-002**: Context operations <10ms
- **Verification**: Performance benchmark tests
- **Target**: add_message, get_history, format_for_llm <10ms

**PM-003**: Turn detection latency <100ms
- **Verification**: Performance benchmark tests
- **Target**: <100ms from speech end to event emission

**PM-004**: Memory usage <50MB for 20-message conversation
- **Verification**: Memory profiling during extended sessions
- **Target**: <50MB per conversation session

### Quality Metrics

**QM-001**: Test coverage ≥90% for all conversation modules
- **Verification**: pytest-cov report
- **Target**: ≥90% line coverage

**QM-002**: Mypy type checking passes with zero errors
- **Verification**: mypy src/nora_livekit/conversation/
- **Target**: 0 type errors

**QM-003**: Ruff linting passes with zero errors
- **Verification**: ruff check src/nora_livekit/conversation/
- **Target**: 0 linting errors

**QM-004**: All integration tests pass consistently
- **Verification**: pytest runs over 10 iterations
- **Target**: 100% pass rate

### Reliability Metrics

**RM-001**: LLM API error rate <1% with successful retries
- **Verification**: Production monitoring (error logs)
- **Target**: <1% permanent failures

**RM-002**: Conversation engine uptime ≥99.9%
- **Verification**: Production monitoring (health checks)
- **Target**: ≥99.9% uptime

**RM-003**: No memory leaks during extended conversations
- **Verification**: Memory profiling over 1-hour sessions
- **Target**: Memory growth <10% over 1 hour

---

## Glossary

**Conversation Context**: In-memory storage of conversation history, participant metadata, and session state
**LLM (Large Language Model)**: AI model (OpenAI GPT or Anthropic Claude) used for generating conversational responses
**Turn-Taking**: Protocol for managing when user and agent speak, preventing overlaps
**Turn Detector**: LiveKit plugin that identifies speech boundaries using Voice Activity Detection (VAD)
**Conversation Phase**: Lifecycle stage (greeting, active, closing) that determines conversation behavior
**Interruption**: Event where user starts speaking while agent is responding
**VAD (Voice Activity Detection)**: Algorithm to detect presence of speech in audio
**System Prompt**: Instructions given to LLM to guide its behavior and response style
**Context Window**: Maximum number of tokens (words) LLM can process in single request
**Fallback Response**: Default response used when LLM API fails
**Participant Metadata**: Information about conversation participant (name, join time, preferences)
**Message History**: Chronological list of conversation messages with roles and timestamps

---

## Appendix A: EARS Requirements Summary

### ConversationContext Requirements
- REQ-F-CTX-001: Empty history on initialization
- REQ-F-CTX-002: Add messages with role and timestamp
- REQ-F-CTX-003: Auto-prune history at max_history limit
- REQ-F-CTX-004: Return participant metadata
- REQ-F-CTX-005: Validate phase transitions

### LLMIntegration Requirements
- REQ-F-LLM-001: Initialize OpenAI client
- REQ-F-LLM-002: Initialize Anthropic client
- REQ-F-LLM-003: Format context for LLM API
- REQ-F-LLM-004: Return response with metrics
- REQ-F-LLM-005: Retry on transient errors
- REQ-F-LLM-006: Fallback on permanent errors
- REQ-F-LLM-007: Phase-specific system prompts
- REQ-F-LLM-008: Format response for TTS

### TurnManager Requirements
- REQ-F-TURN-001: Configure turn detector with VAD
- REQ-F-TURN-002: Emit turn_complete on speech end
- REQ-F-TURN-003: Emit interruption event
- REQ-F-TURN-004: Prevent detection during agent speech
- REQ-F-TURN-005: Handle errors gracefully

### ConversationEngine Requirements
- REQ-F-ENG-001: Initialize all dependencies
- REQ-F-ENG-002: Start with greeting phase
- REQ-F-ENG-003: Process user input with LLM
- REQ-F-ENG-004: Add responses to context
- REQ-F-ENG-005: Handle interruptions
- REQ-F-ENG-006: Transition on idle timeout
- REQ-F-ENG-007: Update phase and prompts

### ParticipantManager Requirements
- REQ-F-PART-001: Add participant on join
- REQ-F-PART-002: Mark inactive on leave
- REQ-F-PART-003: Update activity on speech
- REQ-F-PART-004: Track per-participant state
- REQ-F-PART-005: Return active participants list

---

## Appendix B: File Structure Summary

```
src/nora_livekit/
├── conversation/                        # NEW: Conversation engine module
│   ├── __init__.py                      # Module exports
│   ├── context.py                       # ConversationContext (Phase 1)
│   ├── llm.py                           # LLMIntegration (Phase 2)
│   ├── turn_manager.py                  # TurnManager (Phase 3)
│   ├── engine.py                        # ConversationEngine (Phase 4)
│   └── participant_manager.py           # ParticipantManager (Phase 5)
├── voice/
│   ├── pipeline.py                      # MODIFIED: Add conversation_engine parameter
│   └── ...                              # Other voice modules (unchanged)
├── agent.py                             # MODIFIED: Initialize ConversationEngine
└── config.py                            # MODIFIED: Add ConversationConfig

tests/
├── conversation/                        # NEW: Conversation tests
│   ├── __init__.py
│   ├── test_context.py                  # ConversationContext tests
│   ├── test_llm.py                      # LLMIntegration tests
│   ├── test_turn_manager.py             # TurnManager tests
│   ├── test_engine.py                   # ConversationEngine tests
│   ├── test_participant_manager.py      # ParticipantManager tests
│   ├── test_integration.py              # End-to-end integration tests
│   └── test_performance.py              # Performance benchmarks
└── ...                                  # Existing tests (unchanged)

docs/
├── CONVERSATION_ENGINE.md               # NEW: Architecture documentation
└── CONVERSATION_API.md                  # NEW: API reference
```

---

**END OF IMPLEMENTATION PLAN**
