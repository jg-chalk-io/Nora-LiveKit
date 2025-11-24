---
id: SPEC-LIVEKIT-002
version: 1.0.0
status: pending
created: 2025-11-24
updated: 2025-11-24
completed_at: null
author: @user
priority: P0
domain: VOICE
estimated_loc: 500
actual_loc: null
complexity: medium
dependencies: ["SPEC-LIVEKIT-001"]
---

# SPEC-LIVEKIT-002: Voice Pipeline - Deepgram STT & Cartesia Sonic TTS Integration

## HISTORY

### [1.0.0] - 2025-11-24
- Initial specification created
- Voice pipeline integration for SPEC-002 in 8-SPEC migration roadmap
- Deepgram STT for speech-to-text processing
- Cartesia Sonic TTS for text-to-speech output
- LiveKit audio track handling for bidirectional voice I/O

---

## Executive Summary

This specification defines the voice pipeline integration for Nora LiveKit agent, implementing bidirectional voice communication through Deepgram's speech-to-text (STT) service and Cartesia's Sonic text-to-speech (TTS) engine. The pipeline processes incoming audio from LiveKit rooms, transcribes speech to text, and generates natural-sounding voice responses that are streamed back to participants.

**Strategic Importance**: This is the second critical SPEC in the 8-SPEC migration roadmap. It builds upon SPEC-LIVEKIT-001's foundation infrastructure to deliver core voice interaction capabilities that enable all subsequent conversation features (Session Context, Business Hours, State Tracking).

**Scope**: Voice input/output pipeline only. Conversation logic, business hours, session management, and tool integrations are explicitly out of scope for this SPEC (deferred to SPEC-003 through SPEC-007).

---

## Environment

### Technical Environment

**Development Environment**:
- Python 3.12+ with Poetry dependency management
- Deepgram SDK 5.3.0+ for STT processing
- Cartesia SDK 2.0.17+ for TTS generation
- LiveKit Agents SDK 1.0 with audio plugins
- Existing foundation from SPEC-LIVEKIT-001

**Runtime Environment**:
- Railway cloud platform deployment
- LiveKit Cloud audio tracks (WebRTC transport)
- Deepgram API (cloud-based STT service)
- Cartesia Sonic API (cloud-based TTS service)
- Real-time audio streaming with low latency (<500ms end-to-end)

**External Dependencies**:
- Deepgram API key and credentials
- Cartesia API key and credentials
- LiveKit audio track permissions (publish/subscribe)
- Network connectivity for real-time API calls

### Operational Context

**Audio Pipeline Model**: Real-time streaming pipeline with asynchronous processing
**Voice Quality**: High-quality audio (16kHz sample rate minimum, 24-bit depth preferred)
**Latency Requirements**: <500ms end-to-end latency (audio input → transcription → response → audio output)
**Scalability**: Single agent instance handles one conversation (multi-participant support in future SPECs)

---

## Assumptions

### Technology Assumptions

**ASM-T-001**: Deepgram SDK 5.3.0+ API provides stable WebSocket streaming for real-time STT
**ASM-T-002**: Cartesia Sonic SDK 2.0.17+ supports high-quality voice synthesis with <200ms latency
**ASM-T-003**: LiveKit audio tracks deliver consistent 16kHz PCM audio format
**ASM-T-004**: Network bandwidth supports concurrent STT/TTS API calls (minimum 256kbps)
**ASM-T-005**: LiveKit Agents SDK audio plugin handles audio encoding/decoding automatically

### Business Assumptions

**ASM-B-001**: Voice pipeline implementation is prioritized over conversation logic
**ASM-B-002**: Deepgram and Cartesia API costs are acceptable for development and initial production
**ASM-B-003**: Default voice responses are sufficient (custom voice profiles in future SPECs)
**ASM-B-004**: English language support is primary requirement (multi-language in future SPECs)

### Constraint Assumptions

**ASM-C-001**: No conversation state management or context tracking in this SPEC (deferred to SPEC-003)
**ASM-C-002**: No business hours or availability logic in this SPEC (deferred to SPEC-004)
**ASM-C-003**: Test coverage target remains 90%+ for voice pipeline code
**ASM-C-004**: Voice pipeline must process audio within 500ms end-to-end latency (95th percentile)
**ASM-C-005**: Audio quality must maintain >90% transcription accuracy for clear speech

---

## Requirements

### Functional Requirements

#### Deepgram STT Integration

**REQ-F-001**: MUST integrate Deepgram SDK 5.3.0+ for real-time speech-to-text transcription
- **Rationale**: Industry-leading STT accuracy and low latency for conversational AI
- **Verification**: `poetry show deepgram-sdk` confirms >=5.3.0 installation
- **Traceability**: Links to pyproject.toml dependencies

**REQ-F-002**: MUST establish WebSocket connection to Deepgram API for streaming audio
- **Rationale**: Real-time transcription requires continuous audio streaming
- **Verification**: Integration test confirms WebSocket connection established
- **Traceability**: Links to src/nora_livekit/voice/stt.py

**REQ-F-003**: MUST capture audio from LiveKit audio tracks and stream to Deepgram
- **Rationale**: Process incoming participant audio in real-time
- **Verification**: Unit test confirms audio capture from LiveKit track
- **Traceability**: Links to src/nora_livekit/voice/audio_handler.py

**REQ-F-004**: MUST process Deepgram transcription results and emit text events
- **Rationale**: Enable downstream processing of transcribed speech
- **Verification**: Integration test verifies transcription event emission
- **Traceability**: Links to stt.py transcription handler

**REQ-F-005**: SHOULD handle Deepgram interim results for real-time feedback
- **Rationale**: Provides partial transcriptions for responsive user experience
- **Verification**: Test confirms interim result processing
- **Traceability**: Links to stt.py interim result handler

#### Cartesia Sonic TTS Integration

**REQ-F-006**: MUST integrate Cartesia SDK 2.0.17+ for text-to-speech synthesis
- **Rationale**: High-quality, natural-sounding voice output with low latency
- **Verification**: `poetry show cartesia` confirms >=2.0.17 installation
- **Traceability**: Links to pyproject.toml dependencies

**REQ-F-007**: MUST synthesize text input into audio using Cartesia Sonic API
- **Rationale**: Generate voice responses for participant playback
- **Verification**: Integration test confirms audio synthesis
- **Traceability**: Links to src/nora_livekit/voice/tts.py

**REQ-F-008**: MUST stream synthesized audio to LiveKit audio track for playback
- **Rationale**: Deliver voice responses to conversation participants
- **Verification**: Integration test confirms audio playback on LiveKit track
- **Traceability**: Links to audio_handler.py audio publishing

**REQ-F-009**: SHOULD support configurable voice parameters (pitch, speed, voice model)
- **Rationale**: Enable voice customization for different use cases
- **Verification**: Configuration test confirms parameter setting
- **Traceability**: Links to config.py voice configuration

#### Audio Processing

**REQ-F-010**: MUST handle audio format conversion between LiveKit, Deepgram, and Cartesia
- **Rationale**: Ensure compatible audio formats across different APIs
- **Verification**: Unit test confirms format conversion accuracy
- **Traceability**: Links to audio_handler.py format conversion

**REQ-F-011**: MUST implement audio buffering to handle network latency
- **Rationale**: Smooth audio playback despite variable network conditions
- **Verification**: Load test confirms smooth playback under network jitter
- **Traceability**: Links to audio_handler.py buffer management

**REQ-F-012**: SHOULD implement voice activity detection (VAD) to reduce unnecessary API calls
- **Rationale**: Optimize API costs by processing only speech segments
- **Verification**: Test confirms VAD triggers transcription only during speech
- **Traceability**: Links to audio_handler.py VAD implementation

#### Error Handling

**REQ-F-013**: MUST handle Deepgram API errors gracefully with retry logic
- **Rationale**: Ensure service continuity during temporary API failures
- **Verification**: Test confirms retry on transient errors (max 3 retries)
- **Traceability**: Links to stt.py error handler

**REQ-F-014**: MUST handle Cartesia API errors gracefully with fallback behavior
- **Rationale**: Maintain conversation flow during TTS failures
- **Verification**: Test confirms fallback to text-only response
- **Traceability**: Links to tts.py error handler

**REQ-F-015**: MUST log all voice pipeline errors with structured logging
- **Rationale**: Enable debugging and monitoring in production
- **Verification**: Log output contains structured error events
- **Traceability**: Links to voice module logging configuration

### Non-Functional Requirements

#### Performance

**REQ-NF-001**: SHOULD achieve <500ms end-to-end latency (audio → transcription → synthesis → playback)
- **Rationale**: Maintain natural conversation flow
- **Verification**: Performance test measures 95th percentile latency <500ms
- **Traceability**: Links to performance benchmarks

**REQ-NF-002**: SHOULD maintain >90% transcription accuracy for clear speech
- **Rationale**: Ensure reliable voice interaction
- **Verification**: Accuracy test with standard test dataset
- **Traceability**: Links to accuracy test suite

**REQ-NF-003**: SHOULD handle concurrent audio streams without quality degradation
- **Rationale**: Support simultaneous input/output audio processing
- **Verification**: Concurrency test with multiple audio tracks
- **Traceability**: Links to concurrency test suite

#### Reliability

**REQ-NF-004**: MUST maintain 99.9% uptime for voice pipeline (excluding external API outages)
- **Rationale**: Ensure reliable voice service availability
- **Verification**: Uptime monitoring over 30-day period
- **Traceability**: Links to monitoring dashboard

**REQ-NF-005**: SHOULD implement exponential backoff for API retries (max 3 attempts)
- **Rationale**: Handle transient API failures gracefully
- **Verification**: Test confirms backoff behavior (1s, 2s, 4s delays)
- **Traceability**: Links to retry logic implementation

#### Code Quality

**REQ-NF-006**: SHOULD achieve 90%+ test coverage for voice pipeline modules
- **Rationale**: Maintain code quality standards from SPEC-001
- **Verification**: pytest-cov report shows 90%+ coverage
- **Traceability**: Links to tests/voice/ test suite

**REQ-NF-007**: SHOULD use type hints throughout voice pipeline code
- **Rationale**: Enable static type checking with mypy
- **Verification**: mypy runs without errors on voice modules
- **Traceability**: Links to voice module type annotations

#### Documentation

**REQ-NF-008**: SHOULD document voice pipeline architecture and data flow
- **Rationale**: Enable developer understanding and maintenance
- **Verification**: Architecture diagram in docs/VOICE_PIPELINE.md
- **Traceability**: Links to voice pipeline documentation

**REQ-NF-009**: SHOULD document API rate limits and cost considerations
- **Rationale**: Inform developers of usage constraints and costs
- **Verification**: Documentation includes rate limit table
- **Traceability**: Links to docs/API_COSTS.md

### Interface Requirements

**REQ-I-001**: SHALL expose DeepgramSTT class with async transcribe() method
- **Rationale**: Consistent API for STT processing
- **Verification**: Unit test confirms method signature
- **Traceability**: Links to stt.py DeepgramSTT class

**REQ-I-002**: SHALL expose CartesiaTTS class with async synthesize() method
- **Rationale**: Consistent API for TTS processing
- **Verification**: Unit test confirms method signature
- **Traceability**: Links to tts.py CartesiaTTS class

**REQ-I-003**: SHALL expose AudioHandler class with publish/subscribe methods
- **Rationale**: Consistent API for LiveKit audio track management
- **Verification**: Unit test confirms method signatures
- **Traceability**: Links to audio_handler.py AudioHandler class

**REQ-I-004**: SHALL use structured logging events for all voice pipeline operations
- **Rationale**: Maintain consistency with SPEC-001 logging standards
- **Verification**: Log output follows structlog JSON format
- **Traceability**: Links to voice module logging

### Design Constraints

**REQ-DC-001**: MUST use Deepgram SDK 5.3.0+ (no alternative STT providers)
- **Rationale**: Strategic decision for STT provider consistency
- **Verification**: Poetry lock file confirms deepgram-sdk>=5.3.0
- **Traceability**: Links to pyproject.toml

**REQ-DC-002**: MUST use Cartesia SDK 2.0.17+ for Sonic TTS (no alternative TTS providers)
- **Rationale**: Strategic decision for TTS provider consistency and quality
- **Verification**: Poetry lock file confirms cartesia>=2.0.17
- **Traceability**: Links to pyproject.toml

**REQ-DC-003**: MUST NOT implement conversation state management in voice pipeline
- **Rationale**: Separation of concerns - state management deferred to SPEC-003
- **Verification**: Code review confirms no state tracking in voice modules
- **Traceability**: Links to SPEC-LIVEKIT-003 dependency

**REQ-DC-004**: MUST integrate with existing NoraAgent from SPEC-LIVEKIT-001
- **Rationale**: Build on foundation infrastructure
- **Verification**: Voice pipeline uses NoraAgent lifecycle methods
- **Traceability**: Links to agent.py integration points

---

## Specifications

### Voice Pipeline Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    NoraAgent                            │
│              (SPEC-LIVEKIT-001 Foundation)              │
└────────────────┬────────────────────────────────────────┘
                 │
                 ↓
┌─────────────────────────────────────────────────────────┐
│                  VoicePipeline                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │            AudioHandler                          │   │
│  │  - Subscribe to LiveKit audio tracks             │   │
│  │  - Publish synthesized audio                     │   │
│  │  - Audio format conversion                       │   │
│  │  - Buffer management                             │   │
│  └────────┬─────────────────────────┬─────────────────┘ │
│           │                         │                   │
│           ↓                         ↓                   │
│  ┌──────────────────┐      ┌──────────────────┐        │
│  │  DeepgramSTT     │      │  CartesiaTTS     │        │
│  │  - WebSocket STT │      │  - Text→Audio    │        │
│  │  - Streaming     │      │  - Voice params  │        │
│  │  - Interim results│      │  - Audio stream  │        │
│  └──────────────────┘      └──────────────────┘        │
└──────────┬─────────────────────────┬───────────────────┘
           │                         │
           ↓                         ↓
   ┌──────────────────┐    ┌──────────────────┐
   │  Deepgram API    │    │  Cartesia API    │
   │  (Cloud STT)     │    │  (Cloud TTS)     │
   └──────────────────┘    └──────────────────┘
```

### Project Structure Extension

```
src/nora_livekit/
├── __init__.py
├── __main__.py
├── agent.py                      # SPEC-001 foundation
├── config.py                     # Extended with voice config
├── server.py                     # SPEC-001 health check
└── voice/                        # NEW: Voice pipeline module
    ├── __init__.py
    ├── pipeline.py               # VoicePipeline orchestrator
    ├── stt.py                    # DeepgramSTT implementation
    ├── tts.py                    # CartesiaTTS implementation
    └── audio_handler.py          # LiveKit audio track management

tests/
├── test_agent.py                 # SPEC-001 tests
├── test_config.py
├── test_server.py
└── voice/                        # NEW: Voice pipeline tests
    ├── __init__.py
    ├── test_stt.py               # STT unit tests
    ├── test_tts.py               # TTS unit tests
    ├── test_audio_handler.py     # Audio handling tests
    └── test_pipeline.py          # Integration tests
```

### Technology Stack Extension

#### New Dependencies

```toml
[tool.poetry.dependencies]
# Existing from SPEC-001
python = "^3.12"
livekit-agents = {version = "~1.0", extras = ["openai", "deepgram", "cartesia", "turn-detector"]}
fastapi = "~0.115"
uvicorn = {version = "~0.32", extras = ["standard"]}
python-dotenv = "~1.0"
structlog = "~24.4"
httpx = "~0.27"

# NEW: Voice pipeline dependencies
deepgram-sdk = "~5.3"           # Deepgram STT
cartesia = "~2.0.17"            # Cartesia Sonic TTS
numpy = "~2.0"                  # Audio processing
soundfile = "~0.12"             # Audio file I/O
```

**Version Pinning Strategy**:
- Deepgram SDK pinned to 5.3.x for stable STT API
- Cartesia SDK pinned to 2.0.17+ for stable TTS API (excluding 3.0.0b1 beta)
- Audio processing libraries pinned to latest stable versions

#### Environment Configuration Extension

**New Required Variables**:
```env
# Deepgram Configuration
DEEPGRAM_API_KEY=your-deepgram-api-key
DEEPGRAM_MODEL=nova-2               # STT model (default: nova-2)
DEEPGRAM_LANGUAGE=en-US             # Language code (default: en-US)

# Cartesia Configuration
CARTESIA_API_KEY=your-cartesia-api-key
CARTESIA_VOICE_ID=default-sonic-voice   # Voice model ID
CARTESIA_SPEED=1.0                  # Speech speed (0.5-2.0, default: 1.0)
CARTESIA_EMOTION=neutral            # Voice emotion (default: neutral)

# Voice Pipeline Configuration
VOICE_SAMPLE_RATE=16000             # Audio sample rate (default: 16000 Hz)
VOICE_CHANNELS=1                    # Audio channels (default: 1 = mono)
VOICE_LATENCY_TARGET=500            # Target latency in ms (default: 500)
VAD_THRESHOLD=0.5                   # Voice activity detection threshold (0.0-1.0)
```

### Voice Pipeline Implementation Specifications

#### VoicePipeline Class

**File**: `src/nora_livekit/voice/pipeline.py`

**Class Definition**:
```python
class VoicePipeline:
    """Orchestrates voice input/output pipeline for LiveKit agent.

    Manages Deepgram STT, Cartesia TTS, and LiveKit audio track handling
    for bidirectional voice communication.
    """

    def __init__(
        self,
        config: Config,
        stt: DeepgramSTT,
        tts: CartesiaTTS,
        audio_handler: AudioHandler,
    ) -> None:
        """Initialize voice pipeline with STT, TTS, and audio handler."""

    async def start(self) -> None:
        """Start voice pipeline and audio processing."""

    async def stop(self) -> None:
        """Stop voice pipeline and cleanup resources."""

    async def process_audio_stream(self) -> None:
        """Process incoming audio stream from LiveKit tracks."""

    async def _handle_transcription(self, text: str) -> None:
        """Handle transcribed text from STT."""

    async def _generate_response(self, text: str) -> str:
        """Generate response text (placeholder for SPEC-003 conversation logic)."""
```

**Lifecycle Flow**:
1. Initialize with STT, TTS, and audio handler dependencies
2. Start audio processing on pipeline.start()
3. Subscribe to LiveKit audio tracks
4. Stream audio to Deepgram STT
5. Process transcription results
6. Generate response text (simple echo for this SPEC)
7. Synthesize response with Cartesia TTS
8. Publish audio to LiveKit track
9. Stop and cleanup on pipeline.stop()

#### DeepgramSTT Class

**File**: `src/nora_livekit/voice/stt.py`

**Class Definition**:
```python
class DeepgramSTT:
    """Deepgram speech-to-text integration for real-time transcription."""

    def __init__(
        self,
        api_key: str,
        model: str = "nova-2",
        language: str = "en-US",
        interim_results: bool = True,
    ) -> None:
        """Initialize Deepgram STT client."""

    async def connect(self) -> None:
        """Establish WebSocket connection to Deepgram API."""

    async def disconnect(self) -> None:
        """Close WebSocket connection and cleanup."""

    async def transcribe_stream(
        self,
        audio_stream: AsyncIterator[bytes],
    ) -> AsyncIterator[TranscriptionResult]:
        """Stream audio to Deepgram and yield transcription results."""

    async def _handle_deepgram_message(self, message: dict) -> TranscriptionResult:
        """Parse Deepgram WebSocket messages into structured results."""
```

**Key Features**:
- WebSocket streaming for real-time transcription
- Support for interim results (partial transcriptions)
- Configurable model and language
- Structured error handling with retry logic
- Structured logging for all events

#### CartesiaTTS Class

**File**: `src/nora_livekit/voice/tts.py`

**Class Definition**:
```python
class CartesiaTTS:
    """Cartesia Sonic text-to-speech integration for voice synthesis."""

    def __init__(
        self,
        api_key: str,
        voice_id: str = "default-sonic-voice",
        speed: float = 1.0,
        emotion: str = "neutral",
    ) -> None:
        """Initialize Cartesia TTS client."""

    async def connect(self) -> None:
        """Initialize connection to Cartesia API."""

    async def disconnect(self) -> None:
        """Close connection and cleanup."""

    async def synthesize(
        self,
        text: str,
        sample_rate: int = 16000,
    ) -> AsyncIterator[bytes]:
        """Synthesize text to audio stream."""

    async def _stream_audio(
        self,
        response: Any,
    ) -> AsyncIterator[bytes]:
        """Stream audio bytes from Cartesia API response."""
```

**Key Features**:
- Streaming audio synthesis for low latency
- Configurable voice parameters (voice_id, speed, emotion)
- Asynchronous processing for concurrent synthesis
- Error handling with fallback behavior
- Structured logging for synthesis events

#### AudioHandler Class

**File**: `src/nora_livekit/voice/audio_handler.py`

**Class Definition**:
```python
class AudioHandler:
    """Manages LiveKit audio track publishing and subscription."""

    def __init__(
        self,
        room: Any,  # LiveKit Room instance
        sample_rate: int = 16000,
        channels: int = 1,
    ) -> None:
        """Initialize audio handler for LiveKit room."""

    async def subscribe_to_participant_audio(
        self,
        participant_id: str,
    ) -> AsyncIterator[bytes]:
        """Subscribe to participant's audio track and yield audio chunks."""

    async def publish_audio(
        self,
        audio_stream: AsyncIterator[bytes],
    ) -> None:
        """Publish audio stream to LiveKit track."""

    def convert_format(
        self,
        audio: bytes,
        source_format: str,
        target_format: str,
    ) -> bytes:
        """Convert audio between formats (PCM, WAV, etc.)."""

    async def _buffer_audio(
        self,
        audio_stream: AsyncIterator[bytes],
        buffer_duration_ms: int = 100,
    ) -> AsyncIterator[bytes]:
        """Buffer audio stream to smooth playback."""
```

**Key Features**:
- LiveKit audio track subscription/publishing
- Audio format conversion (PCM ↔ WAV ↔ other formats)
- Audio buffering for smooth playback
- Voice activity detection (VAD) integration
- Error handling for track failures

### Configuration Extension

**File**: `src/nora_livekit/config.py`

**Extended Configuration**:
```python
@dataclass
class VoiceConfig:
    """Voice pipeline configuration."""
    deepgram_api_key: str
    deepgram_model: str = "nova-2"
    deepgram_language: str = "en-US"
    cartesia_api_key: str
    cartesia_voice_id: str = "default-sonic-voice"
    cartesia_speed: float = 1.0
    cartesia_emotion: str = "neutral"
    sample_rate: int = 16000
    channels: int = 1
    latency_target_ms: int = 500
    vad_threshold: float = 0.5

@dataclass
class Config:
    # Existing from SPEC-001
    livekit_url: str
    livekit_api_key: str
    livekit_api_secret: str
    health_check_port: int = 8080
    log_level: str = "INFO"
    log_format: str = "json"
    test_room: str | None = None

    # NEW: Voice pipeline configuration
    voice: VoiceConfig | None = None

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        # Existing validation from SPEC-001
        # NEW: Load voice configuration if API keys present
```

### Logging Extension

**Voice Pipeline Log Events**:
- `voice.pipeline.started`: Voice pipeline initialized
- `voice.pipeline.stopped`: Voice pipeline shutdown
- `voice.stt.connected`: Deepgram WebSocket connected
- `voice.stt.transcription`: Transcription result received (include text, is_final)
- `voice.stt.error`: STT error occurred (include error details)
- `voice.tts.synthesis_started`: TTS synthesis initiated (include text)
- `voice.tts.synthesis_completed`: TTS synthesis completed (include duration_ms)
- `voice.tts.error`: TTS error occurred (include error details)
- `voice.audio.published`: Audio published to LiveKit track
- `voice.audio.subscribed`: Subscribed to participant audio track

### Error Handling Specifications

#### STT Error Handling

**Transient Errors** (retry with exponential backoff):
- WebSocket connection failures
- Temporary API unavailability (503 errors)
- Network timeouts

**Retry Strategy**:
- Max 3 retry attempts
- Backoff delays: 1s, 2s, 4s
- Log each retry attempt

**Permanent Errors** (log and fail):
- Invalid API key (401 Unauthorized)
- Rate limit exceeded (429 Too Many Requests)
- Invalid audio format (400 Bad Request)

#### TTS Error Handling

**Transient Errors** (retry with exponential backoff):
- API connection failures
- Temporary service unavailability

**Fallback Behavior**:
- On TTS failure: Log error, skip audio response, continue conversation
- On repeated failures: Disable TTS temporarily, log warning

**Permanent Errors** (log and degrade service):
- Invalid API key (401 Unauthorized)
- Invalid voice_id or parameters (400 Bad Request)

### Testing Specifications

#### Unit Tests

**tests/voice/test_stt.py**:
- Test Deepgram client initialization
- Test WebSocket connection establishment
- Test transcription result parsing
- Test error handling and retries
- Mock Deepgram API responses

**tests/voice/test_tts.py**:
- Test Cartesia client initialization
- Test audio synthesis
- Test voice parameter configuration
- Test error handling and fallback
- Mock Cartesia API responses

**tests/voice/test_audio_handler.py**:
- Test audio track subscription
- Test audio publishing
- Test format conversion
- Test audio buffering
- Mock LiveKit room and tracks

#### Integration Tests

**tests/voice/test_pipeline.py**:
- Test end-to-end voice pipeline
- Test audio stream processing
- Test STT → TTS flow
- Test concurrent audio handling
- Test graceful shutdown

**Test Fixtures**:
- Sample audio files (WAV, PCM)
- Mock API responses (Deepgram, Cartesia)
- Mock LiveKit rooms and tracks

#### Performance Tests

**Latency Benchmarks**:
- Measure end-to-end latency (audio → transcription → synthesis → playback)
- Target: <500ms at 95th percentile
- Test with various audio inputs

**Accuracy Tests**:
- Test transcription accuracy with standard test dataset
- Target: >90% accuracy for clear speech
- Test with various accents and speech patterns

---

## Traceability

### SPEC Dependencies

**Depends On**:
- SPEC-LIVEKIT-001 (Foundation): Agent lifecycle, health checks, configuration, logging

**Enables**:
- SPEC-LIVEKIT-003 (Session Context): Voice pipeline provides transcription for context tracking
- SPEC-LIVEKIT-004 (Business Hours): Voice pipeline enables conversation availability logic
- SPEC-LIVEKIT-005 (Conversation State): Voice pipeline provides input for state machine
- SPEC-LIVEKIT-006 (Supabase Integration): Voice pipeline data stored in database
- SPEC-LIVEKIT-007 (Tool Integrations): Voice pipeline enables voice-driven tool execution

### Implementation Tags

**TAG-IMPL-VOICE-001**: src/nora_livekit/voice/pipeline.py VoicePipeline class
**TAG-IMPL-VOICE-002**: src/nora_livekit/voice/stt.py DeepgramSTT implementation
**TAG-IMPL-VOICE-003**: src/nora_livekit/voice/tts.py CartesiaTTS implementation
**TAG-IMPL-VOICE-004**: src/nora_livekit/voice/audio_handler.py AudioHandler class
**TAG-IMPL-VOICE-005**: Extended config.py with VoiceConfig
**TAG-IMPL-VOICE-006**: pyproject.toml with deepgram-sdk and cartesia dependencies
**TAG-IMPL-VOICE-007**: Environment configuration for Deepgram and Cartesia

### Test Tags

**TAG-TEST-VOICE-001**: tests/voice/test_stt.py STT unit tests
**TAG-TEST-VOICE-002**: tests/voice/test_tts.py TTS unit tests
**TAG-TEST-VOICE-003**: tests/voice/test_audio_handler.py audio handling tests
**TAG-TEST-VOICE-004**: tests/voice/test_pipeline.py integration tests
**TAG-TEST-VOICE-005**: Performance benchmarks for latency
**TAG-TEST-VOICE-006**: Accuracy tests for transcription

---

## Risk Assessment

| Risk ID | Risk Description | Impact | Probability | Mitigation Strategy | Owner |
|---------|------------------|--------|-------------|---------------------|-------|
| RISK-001 | Deepgram API latency exceeds target | High | Medium | Implement local buffering, use interim results, optimize network path | Backend Expert |
| RISK-002 | Cartesia API rate limits hit during testing | Medium | High | Implement request throttling, use development rate limits, cache common responses | Backend Expert |
| RISK-003 | Audio format incompatibility between APIs | Medium | Low | Standardize on PCM 16kHz mono, implement robust format conversion | Backend Expert |
| RISK-004 | Voice pipeline memory leaks during streaming | High | Medium | Implement proper resource cleanup, add memory monitoring, profile streaming code | Backend Expert |
| RISK-005 | Network failures disrupt audio streaming | Medium | Medium | Implement retry logic, buffer audio, graceful degradation | Backend Expert |
| RISK-006 | API costs exceed budget during development | Medium | High | Monitor API usage, implement usage alerts, use free tier limits | Project Manager |
| RISK-007 | Voice quality degradation under load | High | Low | Load test voice pipeline, implement quality monitoring, optimize audio processing | Performance Engineer |
| RISK-008 | Deepgram/Cartesia SDK version incompatibility | Medium | Low | Pin exact versions, test immediately after upgrade, maintain version matrix | Backend Expert |

---

## Success Metrics

### Performance Metrics

**PM-001**: End-to-end voice latency <500ms at 95th percentile
**PM-002**: STT transcription accuracy >90% for clear speech
**PM-003**: TTS audio quality rated >4.0/5.0 in subjective testing
**PM-004**: Voice pipeline handles continuous 10-minute conversations without degradation

### Reliability Metrics

**RM-001**: Voice pipeline uptime ≥99.9% (excluding external API outages)
**RM-002**: STT API error rate <1% with successful retries
**RM-003**: TTS API error rate <1% with successful retries
**RM-004**: Audio streaming maintains consistent quality during network jitter (±50ms)

### Quality Metrics

**QM-001**: Test coverage ≥90% for voice pipeline modules
**QM-002**: Mypy type checking passes with zero errors
**QM-003**: Ruff linting passes with zero errors
**QM-004**: Black formatting passes with zero changes
**QM-005**: All integration tests pass consistently (100% pass rate over 10 runs)

### Cost Metrics

**CM-001**: Deepgram API costs <$0.05 per conversation minute
**CM-002**: Cartesia API costs <$0.10 per conversation minute
**CM-003**: Total voice pipeline cost <$0.15 per conversation minute

---

## Glossary

**STT (Speech-to-Text)**: Process of converting spoken audio into text transcription
**TTS (Text-to-Speech)**: Process of synthesizing text into spoken audio
**Deepgram**: Cloud-based STT API provider with real-time WebSocket streaming
**Cartesia Sonic**: High-quality TTS engine with natural-sounding voice synthesis
**Voice Pipeline**: End-to-end processing flow from audio input to audio output
**VAD (Voice Activity Detection)**: Algorithm to detect presence of human speech in audio
**PCM (Pulse Code Modulation)**: Uncompressed audio format (raw audio samples)
**Interim Results**: Partial transcription results before final transcription
**Audio Buffering**: Temporary storage of audio data to smooth playback
**WebSocket**: Protocol for full-duplex communication over TCP (used for real-time streaming)
**Sample Rate**: Number of audio samples per second (16kHz = 16,000 samples/second)
**Latency**: Time delay between input and output (target: <500ms end-to-end)

---

**END OF SPECIFICATION**
