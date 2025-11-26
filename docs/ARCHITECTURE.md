# Architecture Documentation - Nora-LiveKit Voice Agent

## System Overview

Nora-LiveKit is a modular voice agent framework built on the LiveKit Agents SDK. The system orchestrates real-time speech-to-text transcription (Deepgram), text-to-speech synthesis (Cartesia), and bidirectional audio streaming with LiveKit participants.

### Design Philosophy

The architecture follows these key principles:

1. **Separation of Concerns**: Each component has a single, well-defined responsibility
2. **Async-First**: Full async/await support for non-blocking I/O operations
3. **Dependency Injection**: Components accept dependencies in constructors for testability
4. **Error Resilience**: Graceful error handling with retry logic and fallbacks
5. **Observability**: Structured logging for debugging and monitoring

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         NoraAgent                               │
│                (Orchestration & Lifecycle)                      │
│                                                                 │
│  - Manages startup/shutdown                                    │
│  - Handles room connections                                    │
│  - Coordinates voice pipeline                                  │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│                      VoicePipeline                              │
│               (Voice Processing Orchestrator)                   │
│                                                                 │
│  - Manages STT, TTS, and audio handler lifecycle               │
│  - Coordinates audio input/output flow                         │
│  - Handles pipeline errors and recovery                        │
└────────────┬────────────────────────────┬───────────────────────┘
             │                            │
             ↓                            ↓
    ┌────────────────────┐      ┌────────────────────┐
    │   AudioHandler     │      │                    │
    │                    │      │  ┌──────────────┐  │
    │ - Subscribe to     │      │  │ DeepgramSTT  │  │
    │   LiveKit tracks   │      │  ├──────────────┤  │
    │ - Format convert   │      │  │ - WebSocket  │  │
    │ - Buffer manage    │      │  │ - Streaming  │  │
    │ - Publish audio    │      │  │ - Interim    │  │
    │                    │      │  │   results    │  │
    └────────────────────┘      │  └──────────────┘  │
                                │                    │
                                │  ┌──────────────┐  │
                                │  │ CartesiaTTS  │  │
                                │  ├──────────────┤  │
                                │  │ - Text→Audio │  │
                                │  │ - Streaming  │  │
                                │  │ - Voice      │  │
                                │  │   params     │  │
                                │  └──────────────┘  │
                                └────────────────────┘
                                         │
        ┌────────────────────────────────┴────────────────────────────────┐
        │                                                                  │
        ↓                                                                  ↓
┌──────────────────────┐                                          ┌──────────────────────┐
│  Deepgram API        │                                          │  Cartesia API        │
│  (Cloud STT)         │                                          │  (Cloud TTS)         │
│                      │                                          │                      │
│ - Real-time          │                                          │ - Voice synthesis    │
│   transcription      │                                          │ - Multiple voices    │
│ - Interim results    │                                          │ - Configurable tone  │
│ - Multiple models    │                                          │ - Stream output      │
└──────────────────────┘                                          └──────────────────────┘

        │                                                                  │
        └────────────────────────────────┬───────────────────────────────┘
                                         │
                         ┌───────────────┴───────────────┐
                         │                               │
                         ↓                               ↓
                  ┌──────────────────┐          ┌──────────────────┐
                  │   LiveKit Room   │          │   Participants   │
                  │   (WebRTC)       │          │   Audio Tracks   │
                  └──────────────────┘          └──────────────────┘
```

## Component Architecture

### 1. NoraAgent (Core Orchestrator)

**Responsibilities**:
- Agent lifecycle management (start/stop)
- Room connection handling
- Voice pipeline initialization and coordination
- Graceful shutdown with cleanup

**Key Methods**:
```python
class NoraAgent:
    async def start(self) -> None
    async def stop(self) -> None
    async def _process_room_messages(self) -> None
```

**Lifecycle Flow**:
1. Initialize with config
2. Create and start voice pipeline
3. Subscribe to room events
4. Process participant messages
5. Gracefully shutdown and cleanup

**State Management**:
- `_is_running`: Boolean flag for agent state
- `_shutdown_event`: Asyncio event for coordinated shutdown
- `_voice_pipeline`: Reference to active voice pipeline

### 2. VoicePipeline (Voice Processing Orchestrator)

**Responsibilities**:
- Orchestrate STT, TTS, and audio handler
- Manage audio flow from input to output
- Error handling and recovery
- Pipeline lifecycle management

**Key Methods**:
```python
class VoicePipeline:
    async def start(self) -> None
    async def stop(self) -> None
    async def process_audio_stream(self) -> None
    async def _handle_transcription(self, text: str) -> None
    async def _generate_response(self, text: str) -> str
```

**Audio Flow**:
```
Input Audio Stream
       ↓
AudioHandler (Subscribe)
       ↓
DeepgramSTT (Transcribe)
       ↓
Text Processing
       ↓
CartesiaTTS (Synthesize)
       ↓
AudioHandler (Publish)
       ↓
Output Audio Stream
```

**Error Recovery**:
- Transient errors trigger retry logic
- Permanent errors log and degrade service
- Pipeline continues despite component failures

### 3. AudioHandler (LiveKit Audio Management)

**Responsibilities**:
- Subscribe to participant audio tracks
- Publish synthesized audio to LiveKit track
- Audio format conversion between APIs
- Audio buffering for smooth playback

**Key Methods**:
```python
class AudioHandler:
    async def subscribe_to_participant_audio(self, participant_id: str) -> AsyncIterator[bytes]
    async def publish_audio(self, audio_stream: AsyncIterator[bytes]) -> None
    def convert_format(self, audio: bytes, source_format: str, target_format: str) -> bytes
    async def _buffer_audio(self, audio_stream: AsyncIterator[bytes]) -> AsyncIterator[bytes]
```

**Audio Format Pipeline**:
```
LiveKit Audio (WebRTC codec)
    ↓ (decode)
PCM 16-bit, 16kHz, Mono
    ↓ (stream to STT)
Deepgram (processes PCM)
    ↓
Deepgram (outputs text)
    ↓ (stream to TTS)
Cartesia (accepts text)
    ↓ (outputs PCM)
PCM 16-bit, 16kHz, Mono
    ↓ (encode)
LiveKit Audio (WebRTC codec)
```

**Key Features**:
- Transparent format conversion
- Audio buffering (100ms default)
- Voice activity detection (VAD) support
- Error handling for track failures

### 4. DeepgramSTT (Speech-to-Text)

**Responsibilities**:
- Establish WebSocket connection to Deepgram API
- Stream audio data for real-time transcription
- Parse and emit transcription results
- Handle STT errors with retry logic

**Key Methods**:
```python
class DeepgramSTT:
    async def connect(self) -> None
    async def disconnect(self) -> None
    async def transcribe_stream(self, audio_stream: AsyncIterator[bytes]) -> AsyncIterator[TranscriptionResult]
    async def _handle_deepgram_message(self, message: dict) -> TranscriptionResult
```

**Data Structures**:
```python
@dataclass
class TranscriptionResult:
    text: str                    # Transcribed text
    is_final: bool              # Is this the final result?
    confidence: float           # Confidence score (0.0-1.0)
    timestamp: float            # Result timestamp
```

**WebSocket Protocol**:
1. Open WebSocket connection to Deepgram
2. Send configuration and model selection
3. Stream audio chunks as they arrive
4. Receive interim and final transcription results
5. Close connection on completion

**Error Handling**:
- **Transient Errors** (retry): WebSocket failures, timeouts, 503 errors
- **Permanent Errors** (fail): Invalid API key (401), invalid format (400)
- **Retry Strategy**: 3 attempts with exponential backoff (1s, 2s, 4s)

### 5. CartesiaTTS (Text-to-Speech)

**Responsibilities**:
- Connect to Cartesia API
- Synthesize text into audio streams
- Configure voice parameters (speed, emotion, voice)
- Handle TTS errors with fallback behavior

**Key Methods**:
```python
class CartesiaTTS:
    async def connect(self) -> None
    async def disconnect(self) -> None
    async def synthesize(self, text: str, sample_rate: int = 16000) -> AsyncIterator[bytes]
    async def _stream_audio(self, response: Any) -> AsyncIterator[bytes]
```

**Voice Configuration**:
- `voice_id`: Model selection (e.g., "default-sonic-voice")
- `speed`: 0.5x to 2.0x (default: 1.0)
- `emotion`: neutral, happy, emphatic, sad, etc.
- `sample_rate`: 16000 Hz standard

**Error Handling**:
- **Transient Errors** (retry): Connection failures, timeouts
- **Permanent Errors** (degrade): Invalid voice_id, invalid parameters
- **Fallback**: Skip audio synthesis, continue with text-only response

### 6. Configuration Management

**Responsibilities**:
- Load and validate configuration from environment
- Provide typed configuration objects
- Setup logging infrastructure
- Validate API credentials

**Key Classes**:
```python
@dataclass
class VoiceConfig:
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
    livekit_url: str
    livekit_api_key: str
    livekit_api_secret: str
    health_check_port: int = 8080
    log_level: str = "INFO"
    log_format: str = "json"
    voice: VoiceConfig | None = None
```

**Configuration Sources**:
1. Environment variables (highest priority)
2. `.env` file (via python-dotenv)
3. Default values in dataclass definitions

## Data Flow Diagrams

### Complete Voice Interaction Flow

```
Participant
    │
    ├─→ [Speaks in microphone]
    │
    ↓
LiveKit Room (WebRTC)
    │
    ├─→ [Audio stream published]
    │
    ↓
NoraAgent.subscribe_to_audio()
    │
    ├─→ AudioHandler.subscribe_to_participant_audio()
    │
    ↓
Audio Stream (PCM 16-bit, 16kHz, Mono)
    │
    ├─→ VoicePipeline.process_audio_stream()
    │
    ├─→ DeepgramSTT.transcribe_stream()
    │
    ├─→ Deepgram API (WebSocket)
    │
    ↓
Transcription Result
    │ {"text": "Hello", "is_final": true}
    │
    ├─→ VoicePipeline._handle_transcription()
    │
    ├─→ VoicePipeline._generate_response()
    │
    ├─→ Response Text: "Hi there!"
    │
    ├─→ CartesiaTTS.synthesize()
    │
    ├─→ Cartesia API (HTTP)
    │
    ↓
Audio Stream (PCM 16-bit, 16kHz, Mono)
    │
    ├─→ AudioHandler.publish_audio()
    │
    ├─→ AudioHandler._buffer_audio()
    │
    ↓
LiveKit Room (WebRTC)
    │
    ├─→ [Audio stream published]
    │
    ↓
Participant Speaker
    │
    ├─→ [Plays synthesized audio]
```

### Error Recovery Flow

```
API Request
    │
    ├─→ [Attempt 1]
    │    └─→ Transient Error (timeout, 503)
    │         └─→ Log warning
    │         └─→ Wait 1s
    │         └─→ [Attempt 2]
    │
    ├─→ [Attempt 2]
    │    └─→ Transient Error (timeout)
    │         └─→ Log warning
    │         └─→ Wait 2s
    │         └─→ [Attempt 3]
    │
    ├─→ [Attempt 3]
    │    ├─→ Success → Continue
    │    └─→ Transient Error
    │         └─→ Log error
    │         └─→ Permanent failure
    │         └─→ Degrade service (skip component)
    │
    └─→ Permanent Error (401, 400, invalid data)
         └─→ Log error
         └─→ Degrade service
```

## Module Dependencies

### Dependency Graph

```
NoraAgent
  └─→ Config
  └─→ VoicePipeline
      └─→ Config
      └─→ DeepgramSTT
          └─→ httpx (HTTP client)
          └─→ External: Deepgram API
      └─→ CartesiaTTS
          └─→ httpx (HTTP client)
          └─→ External: Cartesia API
      └─→ AudioHandler
          └─→ livekit-agents (LiveKit SDK)
          └─→ numpy (audio processing)
```

### External Dependencies

**Runtime Dependencies**:
- `livekit`: LiveKit protocol implementation
- `livekit-agents`: LiveKit Agents SDK
- `livekit-api`: LiveKit API client
- `livekit-plugins-deepgram`: Deepgram plugin
- `livekit-plugins-cartesia`: Cartesia plugin
- `fastapi`: Web framework for health checks
- `uvicorn`: ASGI server
- `python-dotenv`: Environment variable loading
- `structlog`: Structured logging
- `httpx`: Async HTTP client
- `numpy`: Audio processing utilities

**Development Dependencies**:
- `pytest`: Testing framework
- `pytest-asyncio`: Async test support
- `pytest-cov`: Coverage reporting
- `black`: Code formatting
- `ruff`: Linting
- `mypy`: Type checking

## Performance Architecture

### Latency Optimization

**Target**: <500ms end-to-end latency

**Component Latencies**:
- Deepgram STT: 100-200ms (WebSocket streaming)
- Network round-trip: 20-50ms
- Cartesia TTS: 50-150ms (depends on text length)
- LiveKit encoding/decoding: 30-100ms

**Optimization Strategies**:
1. **Interim Results**: Use Deepgram interim results for early feedback
2. **Streaming**: Both STT and TTS use streaming (not batch processing)
3. **Buffering**: Small audio buffer (100ms) for smooth playback
4. **Concurrent Processing**: Handle STT input while TTS outputs
5. **Connection Pooling**: Reuse WebSocket and HTTP connections

### Concurrency Model

**Async/Await Architecture**:
- All I/O operations use async/await
- No blocking calls in main event loop
- Tasks run concurrently on single-threaded event loop

**Concurrent Operations**:
```
VoicePipeline
  │
  ├─ Task 1: STT (listen and transcribe)
  │
  └─ Task 2: TTS (synthesize and publish)

These run concurrently, allowing:
- Continue capturing audio while synthesizing response
- Publish response while listening for next input
```

### Memory Management

**Audio Buffer Design**:
- **Size**: 100ms of audio = 1600 samples × 2 bytes = ~3.2KB per buffer
- **Lifetime**: Buffers are discarded after processing
- **Reuse**: No persistent state between interactions

**Resource Cleanup**:
- WebSocket connections closed on shutdown
- Audio streams garbage collected
- Event handlers unsubscribed
- Graceful cleanup on exceptions

## Error Handling Architecture

### Error Categories

**1. Transient Errors** (recoverable with retry)
- Network timeouts
- Temporary API unavailability (503)
- WebSocket disconnections
- Rate limit temporary blocks

**Handling Strategy**: Exponential backoff retry (1s, 2s, 4s, fail)

**2. Permanent Errors** (non-recoverable)
- Invalid API keys (401 Unauthorized)
- Invalid model/voice ID (400 Bad Request)
- Invalid audio format (400 Bad Request)
- Authentication failures

**Handling Strategy**: Log error, degrade service, continue

**3. Catastrophic Errors** (agent-level failures)
- LiveKit connection failure
- Configuration invalid
- Missing required dependencies

**Handling Strategy**: Log error, stop agent, exit

### Error Flow

```
Operation
  │
  ├─→ [Execute]
  │
  ├─→ [Error?]
  │    │
  │    ├─ NO → Success, continue
  │    │
  │    └─ YES
  │        │
  │        ├─→ [Identify error type]
  │        │
  │        ├─ Transient Error
  │        │   ├─→ [Can retry?]
  │        │   ├─ YES → [Wait N seconds] → [Retry]
  │        │   └─ NO (max retries) → [Log] → [Degrade]
  │        │
  │        ├─ Permanent Error
  │        │   ├─→ [Log error] → [Degrade service]
  │        │
  │        └─ Catastrophic Error
  │            ├─→ [Log error] → [Stop agent]
  │
  └─→ Continue/Shutdown
```

## Logging Architecture

### Structured Logging

All events are logged as JSON for machine parsing:

```json
{
  "event": "voice.stt.transcription",
  "timestamp": "2025-11-25T12:34:56.789Z",
  "level": "info",
  "text": "hello world",
  "is_final": true,
  "confidence": 0.95,
  "duration_ms": 125
}
```

### Log Events

**Pipeline Lifecycle**:
- `voice.pipeline.started`: Pipeline initialization
- `voice.pipeline.stopped`: Pipeline shutdown
- `voice.pipeline.error`: Pipeline error

**STT Events**:
- `voice.stt.connected`: WebSocket connection established
- `voice.stt.transcription`: Transcription result received
- `voice.stt.error`: STT error occurred
- `voice.stt.retry`: Retry attempt

**TTS Events**:
- `voice.tts.synthesis_started`: Synthesis initiated
- `voice.tts.synthesis_completed`: Synthesis complete
- `voice.tts.error`: TTS error occurred

**Audio Events**:
- `voice.audio.subscribed`: Subscribed to participant audio
- `voice.audio.published`: Audio published to track
- `voice.audio.format_converted`: Audio format conversion
- `voice.audio.buffered`: Audio buffering event

### Log Levels

- **DEBUG**: Detailed operational information (buffer fills, frame counts)
- **INFO**: Major events (connections, transcriptions, synthesis)
- **WARNING**: Recoverable issues (retry attempts, degraded service)
- **ERROR**: Errors with recovery (API failures, format issues)
- **CRITICAL**: System failures requiring shutdown

## Scalability Architecture

### Single Agent Instance

Current architecture supports:
- **Concurrent Participants**: 1 per agent instance
- **Audio Streams**: Bidirectional (input + output)
- **API Connections**: 2 (STT + TTS)

### Scaling Strategies

**For Multiple Conversations**:
1. Deploy multiple agent instances (one per conversation)
2. Use load balancer to distribute room connections
3. Scale horizontally on cloud platform

**For High Volume**:
1. Connection pooling for API clients
2. Resource pooling for audio buffers
3. Implement circuit breaker pattern for API failures

## Testing Architecture

### Unit Testing

Each component tested independently with mocks:
- `test_config.py`: Configuration loading and validation
- `test_audio_handler.py`: Audio format conversion and buffering
- `test_stt.py`: Deepgram STT transcription
- `test_tts.py`: Cartesia TTS synthesis

### Integration Testing

End-to-end voice pipeline testing:
- `test_pipeline.py`: Complete STT → TTS flow
- Mock external APIs (Deepgram, Cartesia)
- Test error scenarios and recovery

### Quality Metrics

**Coverage**: 89% overall (target: ≥90%)
**Test Count**: 81 passing tests
**Execution Time**: ~0.27 seconds

## Security Architecture

### API Key Management

**Storage**:
- Load from environment variables (`.env` file)
- Never hardcode credentials
- Use separate keys for dev/staging/prod

**Transmission**:
- HTTPS/WSS only for API connections
- Credentials included in HTTP headers
- TLS 1.2+ required

### Data Handling

**Audio Data**:
- Not persisted locally (streamed directly to APIs)
- Cleared from buffers after processing
- No caching of audio content

**Transcription/Synthesis**:
- Handled by third-party APIs
- Covered by provider's privacy policy
- No local persistence

## Deployment Architecture

### Runtime Requirements

- Python 3.12+
- Network connectivity (LiveKit, Deepgram, Cartesia)
- API credentials for all services

### Deployment Options

1. **Local Development**: Poetry virtual environment
2. **Docker Container**: Containerized deployment
3. **Cloud Platform** (Railway, Heroku, etc.): Container-based deployment

### Health Checks

FastAPI health check endpoint:
- `GET /health`: Returns agent status
- Returns 200 if healthy, 503 if unhealthy
- Checks configuration, API connectivity

## Future Architecture Enhancements

### Phase 3+: Conversation Context

Additional components:
- Conversation state machine
- Context tracking system
- Database integration
- Memory management

### Planned Extensions

- Tool integration framework
- Custom prompt pipeline
- Advanced error recovery
- Performance monitoring dashboard

---

**Document Version**: 1.0
**Last Updated**: November 25, 2025
**Status**: Complete
