---
id: SPEC-LIVEKIT-003
version: 0.2.0
status: completed
created: 2025-11-24
updated: 2025-11-25
author: GOOS
priority: P0
---

# SPEC-LIVEKIT-003: Context & Conversation Engine

## HISTORY

| Version | Date       | Author | Changes                                    |
|---------|------------|--------|--------------------------------------------|
| 0.1.0   | 2025-11-24 | GOOS   | Initial draft - conversation engine SPEC  |
| 0.2.0   | 2025-11-25 | GOOS   | Implementation complete, documentation synced |

---

## 1. ENVIRONMENT

### 1.1 System Context

**WHEN** the Nora LiveKit agent operates in production environments, **THEN** the following conditions apply:

- The agent processes real-time voice conversations over LiveKit WebRTC connections
- Users expect natural, contextual responses with minimal latency (<1 second)
- Conversations may include multiple turns with context spanning 5-20 messages
- The system must support both single and multi-participant conversations
- LLM providers (OpenAI or Anthropic) are accessed via public APIs with rate limits
- Turn-taking must feel natural with support for user interruptions

### 1.2 Technical Environment

**WHEN** the conversation engine is deployed, **THEN** it operates under these constraints:

- Python 3.12+ runtime environment
- LiveKit server infrastructure with WebRTC support
- Deepgram STT for speech-to-text (from SPEC-LIVEKIT-002)
- Cartesia Sonic TTS for text-to-speech (from SPEC-LIVEKIT-002)
- OpenAI API (gpt-4, gpt-3.5-turbo) OR Anthropic API (claude-3-sonnet, claude-3-opus)
- LiveKit turn detector plugin for Voice Activity Detection (VAD)
- In-memory conversation state (no external database required)

### 1.3 Integration Environment

**WHEN** this SPEC is implemented, **THEN** it integrates with:

- **SPEC-LIVEKIT-001**: Foundation (configuration, logging, health checks)
- **SPEC-LIVEKIT-002**: Voice Pipeline (STT, TTS, audio handling)
- **SPEC-AGENT-001**: Multi-provider LLM patterns (reference architecture)
- **VoicePipeline._generate_response()**: Primary integration point (line 133 in pipeline.py)

---

## 2. ASSUMPTIONS

### 2.1 User Behavior Assumptions

**Assumption A1**: Users will engage in short-to-moderate length conversations (5-30 turns)
- **Rationale**: Voice conversations naturally trend shorter than text chat
- **Impact**: Context window of 20 messages is sufficient

**Assumption A2**: Turn-taking can be managed through VAD-based detection with 700ms silence threshold
- **Rationale**: Human conversation typically includes 500-1000ms pauses between turns
- **Impact**: No complex turn-taking protocol needed

**Assumption A3**: Users will tolerate 500-1000ms response latency for intelligent responses
- **Rationale**: Trade-off between response quality (LLM-powered) and speed
- **Impact**: LLM API latency is acceptable if <1 second

### 2.2 Technical Assumptions

**Assumption T1**: LLM APIs (OpenAI/Anthropic) will maintain >99% uptime with <1s average latency
- **Rationale**: Commercial APIs have SLA guarantees
- **Impact**: Retry logic with exponential backoff is sufficient

**Assumption T2**: In-memory conversation context is sufficient (no persistence required)
- **Rationale**: Conversations are session-based and transient
- **Impact**: Context lost on agent restart (acceptable for MVP)

**Assumption T3**: TTS can handle LLM-generated text after minimal formatting (markdown removal)
- **Rationale**: Cartesia TTS is robust to text variations
- **Impact**: Simple regex-based formatting is sufficient

### 2.3 Scope Assumptions

**Assumption S1**: Conversation scope is moderate (greeting, Q&A, context-aware responses, conversation phases)
- **Rationale**: User decision from requirement clarification
- **Impact**: No need for complex dialogue management or multi-intent handling

**Assumption S2**: Multi-participant support is basic (tracking join/leave, per-participant activity)
- **Rationale**: Primary use case is 1-on-1 conversations
- **Impact**: No complex multi-party dialogue orchestration needed

---

## 3. REQUIREMENTS

### 3.1 Functional Requirements (FR)

#### 3.1.1 Conversation Context Management

**REQ-F-CTX-001**: Message History
- **WHEN** a user or agent message is added to conversation context,
- **THEN** the system **MUST** append the message with role (user/assistant/system), content, timestamp, and participant_id to the conversation history list

**REQ-F-CTX-002**: History Limit Enforcement
- **WHEN** conversation history exceeds the configured max_history limit (default: 20 messages),
- **THEN** the system **MUST** automatically remove the oldest messages to maintain the limit while preserving chronological order

**REQ-F-CTX-003**: Participant Metadata Management
- **WHEN** a participant joins the conversation,
- **THEN** the system **MUST** store participant metadata including participant_id, name (optional), join_time, and preferences dictionary

**REQ-F-CTX-004**: Conversation Phase Tracking
- **WHEN** the conversation progresses through lifecycle stages,
- **THEN** the system **MUST** transition through valid phases (GREETING → ACTIVE → CLOSING) and reject invalid transitions

**REQ-F-CTX-005**: LLM Format Conversion
- **WHEN** conversation history is prepared for LLM API calls,
- **THEN** the system **MUST** convert internal Message objects to OpenAI/Anthropic API format with "role" and "content" keys

#### 3.1.2 LLM Integration

**REQ-F-LLM-001**: Multi-Provider Support
- **WHEN** ConversationEngine is configured with llm_provider="openai",
- **THEN** the system **MUST** initialize OpenAI client with API key from configuration
- **WHEN** ConversationEngine is configured with llm_provider="anthropic",
- **THEN** the system **MUST** initialize Anthropic client with API key from configuration

**REQ-F-LLM-002**: Context-Aware Response Generation
- **WHEN** generate_response() is called with conversation context,
- **THEN** the system **MUST** format the full conversation history for LLM, include phase-specific system prompt, and call the appropriate LLM API

**REQ-F-LLM-003**: Response Metrics Logging
- **WHEN** LLM API call completes successfully,
- **THEN** the system **MUST** log generation metrics including tokens_used, latency_ms, model name, and finish_reason

**REQ-F-LLM-004**: Retry Logic with Exponential Backoff
- **WHEN** LLM API call fails with retryable error (429, 500, 503),
- **THEN** the system **MUST** retry with exponential backoff (1s, 2s, 4s delays) for maximum 3 attempts

**REQ-F-LLM-005**: Fallback Response on Permanent Failure
- **WHEN** all LLM API retry attempts fail,
- **THEN** the system **MUST** return configured fallback_response and log error with severity level ERROR

**REQ-F-LLM-006**: TTS-Compatible Formatting
- **WHEN** LLM response is received,
- **THEN** the system **MUST** remove markdown syntax (**bold**, _italic_, bullet points, code blocks) and format text for TTS compatibility

**REQ-F-LLM-007**: Phase-Specific System Prompts
- **WHEN** conversation is in GREETING phase,
- **THEN** the system **MUST** use greeting-optimized system prompt instructing short (1-2 sentence) warm greetings
- **WHEN** conversation is in ACTIVE phase,
- **THEN** the system **MUST** use active-conversation system prompt for concise (2-3 sentence) informative responses
- **WHEN** conversation is in CLOSING phase,
- **THEN** the system **MUST** use closing system prompt for brief (1 sentence) friendly farewells

#### 3.1.3 Turn Management

**REQ-F-TURN-001**: Turn Detector Initialization
- **WHEN** TurnManager is initialized,
- **THEN** the system **MUST** configure livekit-plugins-turn-detector with vad_threshold, min_speech_duration_ms, and silence_duration_ms from configuration

**REQ-F-TURN-002**: Turn Completion Detection
- **WHEN** user speech ends (silence detected for configured duration),
- **THEN** the system **MUST** emit USER_TURN_END event with transcribed text and participant_id

**REQ-F-TURN-003**: Interruption Detection
- **WHEN** user starts speaking while agent is speaking,
- **THEN** the system **MUST** emit INTERRUPTION event and trigger TTS playback stop

**REQ-F-TURN-004**: Turn Suppression During Agent Speech
- **WHEN** agent is speaking (set_agent_speaking=True),
- **THEN** the system **MUST** prevent new turn detection until agent speech completes (set_agent_speaking=False)

**REQ-F-TURN-005**: Error Recovery in Turn Detection
- **WHEN** turn detection encounters audio processing error,
- **THEN** the system **MUST** log error with context and continue monitoring without crashing the conversation

#### 3.1.4 Conversation Engine Orchestration

**REQ-F-ENG-001**: Engine Initialization
- **WHEN** ConversationEngine is initialized,
- **THEN** the system **MUST** create instances of ConversationContext, LLMIntegration, TurnManager, and ParticipantManager with provided configuration

**REQ-F-ENG-002**: Conversation Startup
- **WHEN** engine.start() is called,
- **THEN** the system **MUST** initialize conversation in GREETING phase and generate initial greeting message using LLM

**REQ-F-ENG-003**: Transcription Processing
- **WHEN** USER_TURN_END event occurs with transcribed text,
- **THEN** the system **MUST** add user message to context, call LLM to generate response, add assistant response to context, and return response text for TTS

**REQ-F-ENG-004**: Interruption Handling
- **WHEN** INTERRUPTION event occurs,
- **THEN** the system **MUST** stop current TTS playback, clear TTS buffer, and process new user input immediately

**REQ-F-ENG-005**: Idle Timeout Transition
- **WHEN** conversation has been idle (no messages) for configured timeout (default: 120 seconds),
- **THEN** the system **MUST** transition conversation phase to CLOSING and generate closing message

**REQ-F-ENG-006**: Phase Transition Logic
- **WHEN** conversation has received 2+ user messages in GREETING phase,
- **THEN** the system **MUST** automatically transition to ACTIVE phase
- **WHEN** conversation transitions to CLOSING phase,
- **THEN** the system **MUST** update context phase and use closing system prompt for subsequent LLM calls

#### 3.1.5 Participant Management

**REQ-F-PART-001**: Participant Join Tracking
- **WHEN** participant joins LiveKit room,
- **THEN** the system **MUST** add participant to context with join_time timestamp and is_active=True

**REQ-F-PART-002**: Participant Leave Tracking
- **WHEN** participant leaves LiveKit room,
- **THEN** the system **MUST** update participant metadata with leave_time timestamp and set is_active=False

**REQ-F-PART-003**: Activity Timestamp Updates
- **WHEN** participant speaks (message added to context),
- **THEN** the system **MUST** update participant's last_activity timestamp to current time

**REQ-F-PART-004**: Active Participants Query
- **WHEN** get_active_participants() is called,
- **THEN** the system **MUST** return list of participants with is_active=True, sorted by join_time ascending

**REQ-F-PART-005**: Participant Statistics
- **WHEN** get_participant_stats(participant_id) is called,
- **THEN** the system **MUST** return ParticipantActivity object containing message_count, join_time, leave_time, last_activity, and is_active status

### 3.2 Non-Functional Requirements (NFR)

#### 3.2.1 Performance Requirements

**REQ-NFR-PERF-001**: LLM Response Latency
- **WHEN** conversation engine processes user input,
- **THEN** the system **SHOULD** complete LLM response generation in <1000ms at 95th percentile

**REQ-NFR-PERF-002**: Context Operation Performance
- **WHEN** context operations (add_message, get_history, format_for_llm) are executed,
- **THEN** the system **SHOULD** complete each operation in <10ms to avoid blocking conversation flow

**REQ-NFR-PERF-003**: Turn Detection Latency
- **WHEN** user stops speaking (silence detected),
- **THEN** the system **SHOULD** emit turn event within 100ms to maintain natural conversation rhythm

**REQ-NFR-PERF-004**: Memory Efficiency
- **WHEN** conversation maintains 20-message context,
- **THEN** the system **SHOULD** use <50MB memory per conversation session

#### 3.2.2 Reliability Requirements

**REQ-NFR-REL-001**: LLM API Resilience
- **WHEN** LLM API is temporarily unavailable,
- **THEN** the system **SHOULD** successfully recover using retry logic in >99% of cases

**REQ-NFR-REL-002**: Memory Leak Prevention
- **WHEN** conversation runs for extended duration (>1 hour),
- **THEN** the system **SHOULD** maintain stable memory usage with <10% growth over time

**REQ-NFR-REL-003**: Graceful Degradation
- **WHEN** conversation engine encounters non-critical errors,
- **THEN** the system **SHOULD** log errors and continue conversation without user-facing failures

#### 3.2.3 Usability Requirements

**REQ-NFR-USE-001**: Natural Turn-Taking
- **WHEN** users engage in conversation,
- **THEN** the system **SHOULD** detect turn boundaries with >95% accuracy to minimize awkward pauses or interruptions

**REQ-NFR-USE-002**: Contextual Response Quality
- **WHEN** users ask follow-up questions,
- **THEN** the system **SHOULD** maintain context across turns to provide relevant responses

**REQ-NFR-USE-003**: TTS Voice Quality
- **WHEN** LLM-generated responses are synthesized,
- **THEN** the system **SHOULD** produce natural-sounding speech without pronunciation artifacts from markdown or formatting

### 3.3 Interface Requirements (IR)

#### 3.3.1 VoicePipeline Integration

**REQ-IR-PIPE-001**: VoicePipeline Constructor Extension
- **WHEN** VoicePipeline is initialized,
- **THEN** it **SHALL** accept optional conversation_engine parameter of type ConversationEngine | None

**REQ-IR-PIPE-002**: Response Generation Integration
- **WHEN** VoicePipeline._generate_response(text: str, participant_id: str) is called,
- **THEN** it **SHALL** delegate to conversation_engine.process_transcription() if engine is present, otherwise return fallback echo response

**REQ-IR-PIPE-003**: Turn Event Propagation
- **WHEN** VoicePipeline processes audio stream,
- **THEN** it **SHALL** forward turn events from TurnManager to _handle_transcription() method

#### 3.3.2 LiveKit Room Event Integration

**REQ-IR-ROOM-001**: Participant Connected Handler
- **WHEN** LiveKit room emits participant_connected event,
- **THEN** agent **SHALL** call conversation_engine.participant_manager.add_participant() with participant.sid and participant.name

**REQ-IR-ROOM-002**: Participant Disconnected Handler
- **WHEN** LiveKit room emits participant_disconnected event,
- **THEN** agent **SHALL** call conversation_engine.participant_manager.remove_participant() with participant.sid

#### 3.3.3 Configuration Interface

**REQ-IR-CONFIG-001**: Environment Variable Loading
- **WHEN** Config.from_env() is called,
- **THEN** the system **SHALL** load ConversationConfig from environment variables: LLM_PROVIDER, LLM_API_KEY, LLM_MODEL, LLM_TEMPERATURE, LLM_MAX_TOKENS, CONVERSATION_MAX_HISTORY, VAD_THRESHOLD, MIN_SPEECH_DURATION_MS, SILENCE_DURATION_MS, IDLE_TIMEOUT_SECONDS, ENABLE_INTERRUPTIONS, FALLBACK_RESPONSE

**REQ-IR-CONFIG-002**: Optional LLM Configuration
- **WHEN** LLM_API_KEY environment variable is not set,
- **THEN** the system **SHALL** set Config.conversation to None and VoicePipeline **SHALL** operate in fallback echo mode

### 3.4 Design Constraints (DC)

**REQ-DC-001**: In-Memory State Only
- **WHEN** conversation state is managed,
- **THEN** the system **MUST** use in-memory data structures exclusively (no external database, no file persistence)

**REQ-DC-002**: LLM Provider Compatibility
- **WHEN** LLM integration is implemented,
- **THEN** the system **MUST** support OpenAI API (gpt-4, gpt-3.5-turbo) and Anthropic API (claude-3-sonnet, claude-3-opus) with identical functional behavior

**REQ-DC-003**: LiveKit Turn Detector Plugin
- **WHEN** turn detection is implemented,
- **THEN** the system **MUST** use livekit-plugins-turn-detector library and **MUST NOT** implement custom VAD algorithms

**REQ-DC-004**: Minimal VoicePipeline Modifications
- **WHEN** integrating conversation engine with VoicePipeline,
- **THEN** the system **MUST** modify only VoicePipeline.__init__() and VoicePipeline._generate_response() to minimize regression risk

**REQ-DC-005**: Synchronous Context Operations
- **WHEN** conversation context operations are implemented,
- **THEN** all ConversationContext methods **MUST** be synchronous (not async) to avoid deadlocks in LLM integration flow

**REQ-DC-006**: Python Type Safety
- **WHEN** conversation engine code is written,
- **THEN** all public methods **MUST** include type hints for parameters and return values, and **MUST** pass mypy type checking with zero errors

### 3.5 Acceptance Criteria (AC)

**AC-001**: Basic Greeting Flow
- **GIVEN** ConversationEngine is started with GREETING phase
- **WHEN** user says "hello"
- **THEN** system generates warm greeting using LLM (1-2 sentences)
- **AND** adds user message and assistant response to context
- **AND** returns response text for TTS synthesis

**AC-002**: Multi-Turn Q&A with Context
- **GIVEN** conversation has 5 previous messages in history
- **WHEN** user asks follow-up question "What was my first question?"
- **THEN** LLM receives all 5 messages for context
- **AND** generates contextually relevant response
- **AND** response references earlier conversation content

**AC-003**: Turn-Taking Detection
- **GIVEN** user speaks for 400ms then pauses for 800ms
- **WHEN** TurnManager detects silence
- **THEN** USER_TURN_END event is emitted within 100ms
- **AND** transcription processing begins immediately

**AC-004**: Participant Join/Leave Handling
- **GIVEN** LiveKit room with 0 participants
- **WHEN** participant "user-123" joins with name "Alice"
- **THEN** participant is added to ParticipantManager
- **AND** get_active_participants() returns list containing Alice
- **WHEN** participant "user-123" leaves
- **THEN** participant is marked inactive (is_active=False)
- **AND** leave_time timestamp is recorded

**AC-005**: LLM Integration and Response Generation
- **GIVEN** ConversationEngine configured with provider="openai"
- **WHEN** process_transcription("What is the weather today?") is called
- **THEN** OpenAI API is called with conversation history
- **AND** response text is returned with markdown removed
- **AND** tokens_used and latency_ms are logged

**AC-006**: Error Handling and Fallbacks
- **GIVEN** OpenAI API returns 429 (rate limit) error
- **WHEN** generate_response() is called
- **THEN** system retries with exponential backoff (1s, 2s, 4s)
- **WHEN** all 3 retry attempts fail
- **THEN** system returns fallback_response "I'm having trouble right now. Please try again."
- **AND** error is logged with severity ERROR

**AC-007**: Conversation State Transitions
- **GIVEN** conversation starts in GREETING phase
- **WHEN** user sends 2 messages
- **THEN** conversation automatically transitions to ACTIVE phase
- **AND** subsequent LLM calls use ACTIVE system prompt
- **WHEN** conversation is idle for 120 seconds (configurable)
- **THEN** conversation transitions to CLOSING phase
- **AND** closing message is generated

**AC-008**: Context Retention Across Turns
- **GIVEN** conversation with max_history=20
- **WHEN** 25 messages are added
- **THEN** only most recent 20 messages are retained
- **AND** oldest 5 messages are automatically pruned
- **WHEN** format_for_llm() is called
- **THEN** returns list of 20 messages in OpenAI format

**AC-009**: Performance Requirements
- **GIVEN** 100 sample conversations with varying context sizes
- **WHEN** process_transcription() is called for each
- **THEN** 95th percentile LLM response latency is <1000ms
- **AND** add_message() operation completes in <10ms
- **AND** get_history() operation completes in <5ms

**AC-010**: Multi-Participant Scenarios
- **GIVEN** conversation with 3 active participants (Alice, Bob, Charlie)
- **WHEN** each participant speaks in turn
- **THEN** ParticipantManager tracks all 3 participants
- **AND** each participant's last_activity timestamp is updated when they speak
- **AND** message_count is incremented correctly for each participant
- **AND** get_active_participants() returns all 3 in join_time order

---

## 4. SPECIFICATIONS

### 4.1 Component Architecture

#### 4.1.1 ConversationContext

**Purpose**: Manage in-memory conversation state, message history, and participant metadata

**Location**: `src/nora_livekit/conversation/context.py`

**Data Structures**:

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
```

**Class Definition**:

```python
class ConversationContext:
    """Manages in-memory conversation state and history.

    Satisfies: REQ-F-CTX-001, REQ-F-CTX-002, REQ-F-CTX-003,
               REQ-F-CTX-004, REQ-F-CTX-005
    """

    def __init__(self, max_history: int = 20) -> None:
        """Initialize conversation context with history limit."""
        self._history: list[Message] = []
        self._participants: dict[str, ParticipantMetadata] = {}
        self._phase: ConversationPhase = ConversationPhase.GREETING
        self._max_history = max_history
        self._session_id: str = str(uuid.uuid4())
        self._created_at: datetime = datetime.now(timezone.utc)

    def add_message(
        self,
        role: str,
        content: str,
        participant_id: str | None = None
    ) -> None:
        """Add message to history and auto-prune if limit exceeded.

        Satisfies: REQ-F-CTX-001, REQ-F-CTX-002
        """

    def get_history(self, limit: int | None = None) -> list[Message]:
        """Get conversation history with optional limit.

        Satisfies: REQ-F-CTX-001
        """

    def add_participant(
        self,
        participant_id: str,
        name: str | None = None
    ) -> None:
        """Add or update participant metadata.

        Satisfies: REQ-F-CTX-003
        """

    def get_participant(
        self,
        participant_id: str
    ) -> ParticipantMetadata | None:
        """Get participant metadata by ID.

        Satisfies: REQ-F-CTX-003
        """

    def set_phase(self, phase: ConversationPhase) -> None:
        """Update conversation phase with validation.

        Satisfies: REQ-F-CTX-004
        """

    def format_for_llm(self) -> list[dict[str, str]]:
        """Format conversation history for LLM API.

        Returns OpenAI/Anthropic compatible message list.

        Satisfies: REQ-F-CTX-005
        """

    def clear_history(self) -> None:
        """Clear conversation history (for testing)."""
```

**Key Behaviors**:
- Auto-prunes messages when max_history exceeded (FIFO)
- Validates phase transitions (GREETING → ACTIVE → CLOSING only)
- Thread-safe for single-threaded async use (no locks needed)

#### 4.1.2 LLMIntegration

**Purpose**: Abstract LLM API calls with multi-provider support, retry logic, and TTS formatting

**Location**: `src/nora_livekit/conversation/llm.py`

**Data Structures**:

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
```

**Class Definition**:

```python
class LLMIntegration:
    """Handles LLM API integration for conversation generation.

    Satisfies: REQ-F-LLM-001, REQ-F-LLM-002, REQ-F-LLM-003,
               REQ-F-LLM-004, REQ-F-LLM-005, REQ-F-LLM-006, REQ-F-LLM-007
    """

    def __init__(
        self,
        provider: LLMProvider,
        api_key: str,
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 150,
    ) -> None:
        """Initialize LLM integration with provider configuration.

        Satisfies: REQ-F-LLM-001
        """

    async def generate_response(
        self,
        context: ConversationContext,
        system_prompt: str | None = None,
    ) -> LLMResponse:
        """Generate response using LLM based on conversation context.

        Satisfies: REQ-F-LLM-002, REQ-F-LLM-003, REQ-F-LLM-004, REQ-F-LLM-005

        Args:
            context: Current conversation context
            system_prompt: Optional override for system prompt

        Returns:
            LLMResponse with text and metrics

        Raises:
            LLMError: On permanent API failure after retries
        """

    def _construct_system_prompt(
        self,
        phase: ConversationPhase
    ) -> str:
        """Construct phase-specific system prompt.

        Satisfies: REQ-F-LLM-007
        """

    def _format_for_tts(self, text: str) -> str:
        """Format LLM response for TTS compatibility.

        Removes markdown, code blocks, bullet points.

        Satisfies: REQ-F-LLM-006
        """

    async def _call_openai(
        self,
        messages: list[dict]
    ) -> LLMResponse:
        """Call OpenAI API with retry logic.

        Satisfies: REQ-F-LLM-001, REQ-F-LLM-004
        """

    async def _call_anthropic(
        self,
        messages: list[dict]
    ) -> LLMResponse:
        """Call Anthropic API with retry logic.

        Satisfies: REQ-F-LLM-001, REQ-F-LLM-004
        """
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

**Retry Strategy**:
- Retryable errors: 429 (rate limit), 500 (server error), 503 (unavailable)
- Backoff delays: 1s, 2s, 4s (exponential)
- Max attempts: 3
- Fallback response on permanent failure

#### 4.1.3 TurnManager

**Purpose**: Detect turn boundaries and interruptions using LiveKit turn detector plugin

**Location**: `src/nora_livekit/conversation/turn_manager.py`

**Data Structures**:

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
```

**Class Definition**:

```python
class TurnManager:
    """Manages turn-taking detection and coordination.

    Satisfies: REQ-F-TURN-001, REQ-F-TURN-002, REQ-F-TURN-003,
               REQ-F-TURN-004, REQ-F-TURN-005
    """

    def __init__(
        self,
        vad_threshold: float = 0.5,
        min_speech_duration_ms: int = 300,
        silence_duration_ms: int = 700,
    ) -> None:
        """Initialize turn manager with VAD configuration.

        Satisfies: REQ-F-TURN-001
        """

    async def start(self, audio_stream: AsyncIterator[bytes]) -> None:
        """Start monitoring audio stream for turn events.

        Satisfies: REQ-F-TURN-002
        """

    async def stop(self) -> None:
        """Stop turn detection and cleanup."""

    async def wait_for_turn(self) -> TurnData:
        """Wait for next turn event (blocking).

        Satisfies: REQ-F-TURN-002, REQ-F-TURN-003
        """

    def set_agent_speaking(self, speaking: bool) -> None:
        """Notify turn manager when agent is speaking.

        Satisfies: REQ-F-TURN-004
        """

    async def _detect_turns(
        self,
        audio_stream: AsyncIterator[bytes]
    ) -> None:
        """Internal turn detection loop using livekit-plugins-turn-detector.

        Satisfies: REQ-F-TURN-001, REQ-F-TURN-005
        """
```

**Turn Detection Logic**:
- Uses `livekit.plugins.turn_detector` (REQ-DC-003)
- VAD threshold: 0.5 (configurable)
- Min speech duration: 300ms (filters out short bursts)
- Silence duration: 700ms (end-of-turn threshold)
- Interruption: Detected when user speaks while agent_speaking=True

#### 4.1.4 ConversationEngine

**Purpose**: Orchestrate conversation flow, integrate all components, manage lifecycle

**Location**: `src/nora_livekit/conversation/engine.py`

**Class Definition**:

```python
class ConversationEngine:
    """Orchestrates conversation flow with context, LLM, and turn management.

    Satisfies: REQ-F-ENG-001, REQ-F-ENG-002, REQ-F-ENG-003,
               REQ-F-ENG-004, REQ-F-ENG-005, REQ-F-ENG-006, REQ-F-ENG-007
    """

    def __init__(
        self,
        config: ConversationConfig,
        context: ConversationContext,
        llm: LLMIntegration,
        turn_manager: TurnManager,
    ) -> None:
        """Initialize conversation engine with dependencies.

        Satisfies: REQ-F-ENG-001
        """

    async def start(self) -> None:
        """Start conversation engine and generate initial greeting.

        Satisfies: REQ-F-ENG-002
        """

    async def stop(self) -> None:
        """Stop conversation engine and cleanup."""

    async def process_transcription(
        self,
        text: str,
        participant_id: str
    ) -> str:
        """Process transcribed text and generate response.

        This is the main entry point for conversation processing.
        Called by VoicePipeline._handle_transcription().

        Satisfies: REQ-F-ENG-003, REQ-F-ENG-004

        Args:
            text: Transcribed user text
            participant_id: ID of speaking participant

        Returns:
            Response text for TTS synthesis
        """

    async def handle_turn_event(self, turn_data: TurnData) -> None:
        """Handle turn-taking events from TurnManager.

        Satisfies: REQ-F-ENG-005
        """

    async def _generate_greeting(self) -> str:
        """Generate initial greeting message.

        Satisfies: REQ-F-ENG-002
        """

    async def _handle_idle_timeout(self) -> None:
        """Handle conversation idle timeout and transition to closing.

        Satisfies: REQ-F-ENG-006
        """

    def _should_transition_to_active(self) -> bool:
        """Check if conversation should transition from greeting to active.

        Satisfies: REQ-F-ENG-007
        """

    def _should_transition_to_closing(self) -> bool:
        """Check if conversation should transition to closing phase.

        Satisfies: REQ-F-ENG-006
        """
```

**Conversation Flow**:

```
1. start() → Generate greeting (GREETING phase)
2. User speaks → process_transcription() → Add to context → LLM call → Response
3. After 2 user messages → Transition to ACTIVE phase
4. Idle for 120s → Transition to CLOSING phase → Generate closing
5. stop() → Cleanup resources
```

#### 4.1.5 ParticipantManager

**Purpose**: Track multiple participants in conversation room

**Location**: `src/nora_livekit/conversation/participant_manager.py`

**Data Structures**:

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

**Class Definition**:

```python
class ParticipantManager:
    """Manages multiple participants in conversation room.

    Satisfies: REQ-F-PART-001, REQ-F-PART-002, REQ-F-PART-003,
               REQ-F-PART-004, REQ-F-PART-005
    """

    def __init__(self, context: ConversationContext) -> None:
        """Initialize participant manager with conversation context."""

    def add_participant(
        self,
        participant_id: str,
        name: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Add new participant to conversation.

        Satisfies: REQ-F-PART-001
        """

    def remove_participant(self, participant_id: str) -> None:
        """Mark participant as inactive (left conversation).

        Satisfies: REQ-F-PART-002
        """

    def update_activity(self, participant_id: str) -> None:
        """Update participant's last activity timestamp.

        Satisfies: REQ-F-PART-003
        """

    def get_active_participants(self) -> list[ParticipantActivity]:
        """Get list of currently active participants.

        Satisfies: REQ-F-PART-004
        """

    def get_participant_stats(
        self,
        participant_id: str
    ) -> ParticipantActivity | None:
        """Get activity statistics for specific participant.

        Satisfies: REQ-F-PART-005
        """
```

### 4.2 Integration Specifications

#### 4.2.1 VoicePipeline Integration

**Modified File**: `src/nora_livekit/voice/pipeline.py`

**Changes**:

1. **Constructor Modification**:
```python
def __init__(
    self,
    config: Config,
    stt: DeepgramSTT,
    tts: CartesiaTTS,
    audio_handler: AudioHandler,
    conversation_engine: ConversationEngine | None = None,  # NEW
) -> None:
    """Initialize voice pipeline with optional conversation engine.

    Satisfies: REQ-IR-PIPE-001
    """
    self.config = config
    self.stt = stt
    self.tts = tts
    self.audio_handler = audio_handler
    self.conversation_engine = conversation_engine  # NEW
    self._running = False
```

2. **Response Generation Modification** (line 133):
```python
async def _generate_response(
    self,
    text: str,
    participant_id: str = ""
) -> str:
    """Generate response using ConversationEngine.

    Satisfies: REQ-IR-PIPE-002

    Args:
        text: Transcribed user text
        participant_id: ID of speaking participant

    Returns:
        Response text for TTS synthesis
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

**Satisfies**: REQ-DC-004 (minimal modifications)

#### 4.2.2 Configuration Extension

**Modified File**: `src/nora_livekit/config.py`

**New Configuration Class**:

```python
@dataclass
class ConversationConfig:
    """Conversation engine configuration.

    Satisfies: REQ-IR-CONFIG-001
    """
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
```

**Config Class Extension**:

```python
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
        """Load configuration from environment variables.

        Satisfies: REQ-IR-CONFIG-001, REQ-IR-CONFIG-002
        """
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
                    "gpt-4" if llm_provider == "openai"
                    else "claude-3-sonnet-20240229"
                ),
                llm_temperature=float(os.getenv("LLM_TEMPERATURE", "0.7")),
                llm_max_tokens=int(os.getenv("LLM_MAX_TOKENS", "150")),
                max_history=int(os.getenv("CONVERSATION_MAX_HISTORY", "20")),
                vad_threshold=float(os.getenv("VAD_THRESHOLD", "0.5")),
                min_speech_duration_ms=int(
                    os.getenv("MIN_SPEECH_DURATION_MS", "300")
                ),
                silence_duration_ms=int(
                    os.getenv("SILENCE_DURATION_MS", "700")
                ),
                idle_timeout_seconds=int(
                    os.getenv("IDLE_TIMEOUT_SECONDS", "120")
                ),
                enable_interruptions=os.getenv(
                    "ENABLE_INTERRUPTIONS", "true"
                ).lower() == "true",
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

### 4.3 Dependencies

#### 4.3.1 Python Package Dependencies

**New Dependencies** (add to `pyproject.toml`):

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
```

**Development Dependencies**:

```toml
[tool.poetry.group.dev.dependencies]
# Existing
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

#### 4.3.2 External Service Dependencies

**Required APIs**:
- OpenAI API (gpt-4, gpt-3.5-turbo) OR Anthropic API (claude-3-sonnet, claude-3-opus)
- Deepgram API (from SPEC-002)
- Cartesia Sonic API (from SPEC-002)
- LiveKit Cloud (from SPEC-001)

**Environment Variables**:

```env
# LLM Configuration (REQUIRED)
LLM_PROVIDER=openai                    # or "anthropic"
LLM_API_KEY=sk-...                     # OpenAI or Anthropic API key
OPENAI_API_KEY=sk-...                  # Alternative: OpenAI-specific
ANTHROPIC_API_KEY=sk-ant-...           # Alternative: Anthropic-specific

# LLM Model Selection
LLM_MODEL=gpt-4                        # OpenAI: gpt-4, gpt-3.5-turbo
                                       # Anthropic: claude-3-sonnet-20240229
LLM_TEMPERATURE=0.7                    # 0.0-1.0 (default: 0.7)
LLM_MAX_TOKENS=150                     # Max response tokens (default: 150)

# Conversation Settings (OPTIONAL)
CONVERSATION_MAX_HISTORY=20            # Max messages in context
IDLE_TIMEOUT_SECONDS=120               # Idle timeout (default: 120s)
ENABLE_INTERRUPTIONS=true              # Allow interruptions (default: true)
FALLBACK_RESPONSE="I'm having trouble right now. Please try again."

# Turn Detection Settings (OPTIONAL)
VAD_THRESHOLD=0.5                      # Voice activity threshold (0.0-1.0)
MIN_SPEECH_DURATION_MS=300             # Min speech duration (default: 300ms)
SILENCE_DURATION_MS=700                # Silence duration (default: 700ms)
```

---

## 5. TRACEABILITY

### 5.1 SPEC Dependencies

- **SPEC-LIVEKIT-001**: Foundation (configuration, logging) - **COMPLETE**
- **SPEC-LIVEKIT-002**: Voice Pipeline (STT, TTS, audio handling) - **COMPLETE**
- **SPEC-AGENT-001**: Multi-provider LLM patterns - **REFERENCE**

### 5.2 Integration Points

- `VoicePipeline._generate_response()` (line 133 in `src/nora_livekit/voice/pipeline.py`)
- `Config.from_env()` (in `src/nora_livekit/config.py`)
- LiveKit room events (participant_connected, participant_disconnected)

### 5.3 Test Coverage

- **Unit Tests**: 90%+ coverage for all conversation modules
- **Integration Tests**: 5 scenarios (greeting, multi-turn, interruption, lifecycle, multi-participant)
- **Performance Tests**: 4 benchmarks (LLM latency, context ops, turn detection, memory)

### 5.4 Documentation

- `docs/CONVERSATION_ENGINE.md`: Architecture and design
- `docs/CONVERSATION_API.md`: API reference and usage guide
- Module docstrings: All classes and methods

---

## 6. TAGS

**TAG-BLOCK-START**

```yaml
spec_id: SPEC-LIVEKIT-003
title: Context & Conversation Engine
category: conversation
status: draft
priority: P0
dependencies:
  - SPEC-LIVEKIT-001  # Foundation
  - SPEC-LIVEKIT-002  # Voice Pipeline
  - SPEC-AGENT-001    # LLM patterns (reference)
components:
  - ConversationContext
  - LLMIntegration
  - TurnManager
  - ConversationEngine
  - ParticipantManager
integration_points:
  - VoicePipeline._generate_response
  - Config.from_env
  - LiveKit room events
test_coverage_target: 90
performance_targets:
  llm_latency_p95_ms: 1000
  context_operation_ms: 10
  turn_detection_ms: 100
  memory_mb: 50
```

**TAG-BLOCK-END**

---

**END OF SPECIFICATION**
