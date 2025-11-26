# API Reference - Nora-LiveKit Voice Agent

Complete API documentation for all public classes and methods in the Nora-LiveKit voice agent framework.

## Table of Contents

1. [NoraAgent](#noraagentagent)
2. [Configuration](#configuration)
3. [VoicePipeline](#voicepipeline)
4. [DeepgramSTT](#deepgramstt)
5. [CartesiaTTS](#cartesiatts)
6. [AudioHandler](#audiohandler)
7. [Data Structures](#data-structures)
8. [Exceptions](#exceptions)

---

## NoraAgent

### Class: `NoraAgent`

**Module**: `nora_livekit.agent`

Main orchestrator for the voice agent lifecycle. Manages LiveKit room connections, voice pipeline initialization, and graceful shutdown.

#### Constructor

```python
def __init__(self, config: Config) -> None
```

**Parameters**:
- `config` (Config): Configuration instance containing LiveKit credentials and voice settings

**Example**:
```python
from nora_livekit.config import Config
from nora_livekit.agent import NoraAgent

config = Config.from_env()
agent = NoraAgent(config)
```

#### Methods

##### `async start() -> None`

Start the voice agent and begin listening for LiveKit room connections.

**Raises**:
- `RuntimeError`: If the agent is already running or startup fails

**Example**:
```python
try:
    await agent.start()
    print("Agent started successfully")
except RuntimeError as e:
    print(f"Failed to start agent: {e}")
```

**Lifecycle**:
1. Initialize voice pipeline components
2. Connect to LiveKit
3. Subscribe to room events
4. Begin processing audio streams

##### `async stop() -> None`

Stop the voice agent and cleanup all resources.

**Raises**:
- `RuntimeError`: If shutdown fails

**Example**:
```python
try:
    await agent.stop()
    print("Agent stopped gracefully")
except RuntimeError as e:
    print(f"Error during shutdown: {e}")
```

**Cleanup**:
1. Disconnect from LiveKit
2. Stop voice pipeline
3. Close all connections
4. Unsubscribe from events

#### Properties

##### `is_running: bool`

Returns `True` if the agent is currently running and processing audio.

**Example**:
```python
if agent.is_running:
    print("Agent is active")
else:
    print("Agent is not running")
```

---

## Configuration

### Class: `Config`

**Module**: `nora_livekit.config`

Configuration dataclass for the LiveKit agent and voice pipeline.

#### Constructor

```python
def __init__(
    self,
    livekit_url: str,
    livekit_api_key: str,
    livekit_api_secret: str,
    health_check_port: int = 8080,
    log_level: str = "INFO",
    log_format: str = "json",
    test_room: Optional[str] = None,
    voice: Optional[VoiceConfig] = None,
) -> None
```

**Parameters**:
- `livekit_url` (str): WebSocket URL to LiveKit server (e.g., `wss://livekit.example.com`)
- `livekit_api_key` (str): LiveKit API key for authentication
- `livekit_api_secret` (str): LiveKit API secret for token generation
- `health_check_port` (int, optional): Port for health check server (default: 8080)
- `log_level` (str, optional): Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `log_format` (str, optional): Log format ('json' or 'text')
- `test_room` (str, optional): Test room name for testing
- `voice` (VoiceConfig, optional): Voice pipeline configuration

#### Class Methods

##### `@classmethod from_env(cls) -> Config`

Load configuration from environment variables.

**Environment Variables**:
```
# LiveKit
LIVEKIT_URL=wss://...
LIVEKIT_API_KEY=...
LIVEKIT_API_SECRET=...

# Voice
DEEPGRAM_API_KEY=...
DEEPGRAM_MODEL=nova-2
DEEPGRAM_LANGUAGE=en-US
CARTESIA_API_KEY=...
CARTESIA_VOICE_ID=default-sonic-voice
CARTESIA_SPEED=1.0
CARTESIA_EMOTION=neutral

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
```

**Returns**: `Config` instance

**Raises**:
- `ValueError`: If required environment variables are missing

**Example**:
```python
from nora_livekit.config import Config

config = Config.from_env()
print(f"LiveKit URL: {config.livekit_url}")
print(f"Log Level: {config.log_level}")
```

### Class: `VoiceConfig`

**Module**: `nora_livekit.config`

Configuration for voice pipeline (STT, TTS, audio settings).

#### Constructor

```python
def __init__(
    self,
    deepgram_api_key: str,
    cartesia_api_key: str,
    deepgram_model: str = "nova-2",
    deepgram_language: str = "en-US",
    cartesia_voice_id: str = "default-sonic-voice",
    cartesia_speed: float = 1.0,
    cartesia_emotion: str = "neutral",
    sample_rate: int = 16000,
    channels: int = 1,
    latency_target_ms: int = 500,
    vad_threshold: float = 0.5,
) -> None
```

**Parameters**:
- `deepgram_api_key` (str): Deepgram API key
- `cartesia_api_key` (str): Cartesia API key
- `deepgram_model` (str): STT model name (default: "nova-2")
- `deepgram_language` (str): Language code (default: "en-US")
- `cartesia_voice_id` (str): Voice model ID (default: "default-sonic-voice")
- `cartesia_speed` (float): Speech speed (0.5-2.0, default: 1.0)
- `cartesia_emotion` (str): Voice emotion (default: "neutral")
- `sample_rate` (int): Audio sample rate in Hz (default: 16000)
- `channels` (int): Audio channels (default: 1 for mono)
- `latency_target_ms` (int): Target latency in ms (default: 500)
- `vad_threshold` (float): Voice activity detection threshold (default: 0.5)

**Example**:
```python
from nora_livekit.config import VoiceConfig, Config

voice_config = VoiceConfig(
    deepgram_api_key="your-deepgram-key",
    cartesia_api_key="your-cartesia-key",
    deepgram_model="nova-3",
    cartesia_speed=1.2,
)

config = Config(
    livekit_url="wss://...",
    livekit_api_key="...",
    livekit_api_secret="...",
    voice=voice_config,
)
```

---

## VoicePipeline

### Class: `VoicePipeline`

**Module**: `nora_livekit.voice.pipeline`

Orchestrates real-time voice communication by coordinating STT, TTS, and audio handling.

#### Constructor

```python
def __init__(
    self,
    config: Config,
    stt: DeepgramSTT,
    tts: CartesiaTTS,
    audio_handler: AudioHandler,
) -> None
```

**Parameters**:
- `config` (Config): Configuration instance
- `stt` (DeepgramSTT): Speech-to-text processor
- `tts` (CartesiaTTS): Text-to-speech synthesizer
- `audio_handler` (AudioHandler): LiveKit audio track manager

**Example**:
```python
from nora_livekit.voice import VoicePipeline, DeepgramSTT, CartesiaTTS, AudioHandler
from nora_livekit.config import Config

config = Config.from_env()
stt = DeepgramSTT(api_key=config.voice.deepgram_api_key)
tts = CartesiaTTS(api_key=config.voice.cartesia_api_key)
audio_handler = AudioHandler(room)

pipeline = VoicePipeline(config, stt, tts, audio_handler)
```

#### Methods

##### `async start() -> None`

Initialize voice pipeline and establish connections to STT and TTS services.

**Raises**:
- `RuntimeError`: If pipeline is already running or initialization fails

**Example**:
```python
try:
    await pipeline.start()
    print("Voice pipeline started")
except RuntimeError as e:
    print(f"Failed to start pipeline: {e}")
```

**Operations**:
1. Connect to Deepgram STT API
2. Connect to Cartesia TTS API
3. Initialize audio handlers
4. Set running state to True

##### `async stop() -> None`

Stop voice pipeline and cleanup all resources.

**Raises**:
- `RuntimeError`: If shutdown fails

**Example**:
```python
try:
    await pipeline.stop()
    print("Voice pipeline stopped")
except RuntimeError as e:
    print(f"Error stopping pipeline: {e}")
```

**Operations**:
1. Set running state to False
2. Disconnect from Deepgram
3. Disconnect from Cartesia
4. Close audio resources

##### `async process_audio_stream(participant_id: str = "") -> None`

Process incoming audio from participant, transcribe, generate response, and synthesize audio.

**Parameters**:
- `participant_id` (str, optional): ID of participant to listen to

**Raises**:
- `RuntimeError`: If pipeline is not running

**Example**:
```python
async def handle_room_message(room_message):
    participant_id = room_message.speaker_identity
    await pipeline.process_audio_stream(participant_id)
```

**Audio Flow**:
1. Subscribe to participant audio track
2. Stream audio to Deepgram STT
3. Receive transcribed text
4. Generate response (placeholder for SPEC-003)
5. Synthesize response with Cartesia TTS
6. Publish synthesized audio to LiveKit track

#### Properties

##### `is_running: bool`

Returns `True` if pipeline is actively processing audio.

---

## DeepgramSTT

### Class: `DeepgramSTT`

**Module**: `nora_livekit.voice.stt`

Real-time speech-to-text transcription using Deepgram's WebSocket API.

#### Constructor

```python
def __init__(
    self,
    api_key: str,
    model: str = "nova-2",
    language: str = "en-US",
    interim_results: bool = True,
    max_retries: int = 3,
) -> None
```

**Parameters**:
- `api_key` (str): Deepgram API key
- `model` (str): STT model (default: "nova-2")
  - Options: `nova-2`, `nova-3`, `nova-3-general`, `nova-3-financial`
- `language` (str): Language code (default: "en-US")
  - Examples: `en-US`, `fr-FR`, `de-DE`, `es-ES`
- `interim_results` (bool): Enable interim results (default: True)
- `max_retries` (int): Max retry attempts for transient errors (default: 3)

**Raises**:
- `ValueError`: If API key is empty

**Example**:
```python
from nora_livekit.voice.stt import DeepgramSTT

stt = DeepgramSTT(
    api_key="your-deepgram-key",
    model="nova-3",
    language="en-US",
    interim_results=True,
)
```

#### Methods

##### `async connect() -> None`

Establish connection to Deepgram API.

**Raises**:
- `RuntimeError`: If connection fails

**Example**:
```python
try:
    await stt.connect()
    print("Connected to Deepgram")
except RuntimeError as e:
    print(f"Connection failed: {e}")
```

##### `async disconnect() -> None`

Close connection to Deepgram API.

**Example**:
```python
await stt.disconnect()
print("Disconnected from Deepgram")
```

##### `async transcribe_stream(audio_stream: AsyncIterator[bytes]) -> AsyncIterator[TranscriptionResult]`

Stream audio to Deepgram and receive transcription results.

**Parameters**:
- `audio_stream` (AsyncIterator[bytes]): Audio data as 16-bit PCM bytes

**Yields**:
- `TranscriptionResult`: Transcription results (interim and final)

**Retry Strategy**:
- Transient errors (timeout, 503): Retry with exponential backoff (1s, 2s, 4s)
- Permanent errors (401, 400): Fail immediately and log

**Example**:
```python
# Assume audio_stream is an AsyncIterator of audio bytes
try:
    async for result in stt.transcribe_stream(audio_stream):
        if result.is_final:
            print(f"Final transcription: {result.text}")
            print(f"Confidence: {result.confidence}")
        else:
            print(f"Interim: {result.text}")
except RuntimeError as e:
    print(f"Transcription error: {e}")
```

#### Properties

##### `is_connected: bool`

Returns `True` if currently connected to Deepgram API.

##### `model: str`

Current STT model in use.

##### `language: str`

Current language setting.

---

## CartesiaTTS

### Class: `CartesiaTTS`

**Module**: `nora_livekit.voice.tts`

Text-to-speech synthesis using Cartesia's Sonic engine.

#### Constructor

```python
def __init__(
    self,
    api_key: str,
    voice_id: str = "default-sonic-voice",
    speed: float = 1.0,
    emotion: str = "neutral",
    max_retries: int = 3,
) -> None
```

**Parameters**:
- `api_key` (str): Cartesia API key
- `voice_id` (str): Voice model ID (default: "default-sonic-voice")
- `speed` (float): Speech speed multiplier (0.5-2.0, default: 1.0)
  - 0.5 = 50% speed (slower)
  - 1.0 = normal speed
  - 2.0 = 200% speed (faster)
- `emotion` (str): Voice emotion (default: "neutral")
  - Options: `neutral`, `happy`, `emphatic`, `sad`
- `max_retries` (int): Max retry attempts (default: 3)

**Raises**:
- `ValueError`: If API key is empty

**Example**:
```python
from nora_livekit.voice.tts import CartesiaTTS

tts = CartesiaTTS(
    api_key="your-cartesia-key",
    voice_id="default-sonic-voice",
    speed=1.2,
    emotion="happy",
)
```

#### Methods

##### `async connect() -> None`

Initialize connection to Cartesia API.

**Raises**:
- `RuntimeError`: If connection fails

**Example**:
```python
try:
    await tts.connect()
    print("Connected to Cartesia")
except RuntimeError as e:
    print(f"Connection failed: {e}")
```

##### `async disconnect() -> None`

Close connection to Cartesia API.

**Example**:
```python
await tts.disconnect()
print("Disconnected from Cartesia")
```

##### `async synthesize(text: str, sample_rate: int = 16000) -> AsyncIterator[bytes]`

Synthesize text to audio stream.

**Parameters**:
- `text` (str): Text to synthesize (max 5000 characters)
- `sample_rate` (int): Output sample rate in Hz (default: 16000)

**Yields**:
- bytes: Audio chunks as 16-bit PCM data

**Raises**:
- `ValueError`: If text exceeds max length
- `RuntimeError`: If synthesis fails

**Retry Strategy**:
- Transient errors (timeout, connection): Retry with exponential backoff
- Permanent errors (invalid voice_id): Log warning and return silence

**Example**:
```python
try:
    text = "Hello! How can I help you today?"
    audio_stream = tts.synthesize(text)

    async for audio_chunk in audio_stream:
        # Process audio chunk (e.g., send to LiveKit)
        await send_to_livekit(audio_chunk)

except ValueError as e:
    print(f"Invalid input: {e}")
except RuntimeError as e:
    print(f"Synthesis error: {e}")
```

#### Properties

##### `is_connected: bool`

Returns `True` if currently connected to Cartesia API.

##### `voice_id: str`

Current voice model ID.

##### `speed: float`

Current speech speed setting.

##### `emotion: str`

Current emotion setting.

---

## AudioHandler

### Class: `AudioHandler`

**Module**: `nora_livekit.voice.audio_handler`

Manages LiveKit audio track subscription and publishing.

#### Constructor

```python
def __init__(
    self,
    room: Any,
    sample_rate: int = 16000,
    channels: int = 1,
) -> None
```

**Parameters**:
- `room` (LiveKit Room): LiveKit room instance
- `sample_rate` (int): Audio sample rate in Hz (default: 16000)
- `channels` (int): Number of audio channels (default: 1 for mono)

**Example**:
```python
from nora_livekit.voice.audio_handler import AudioHandler

# Assume room is a LiveKit Room instance
audio_handler = AudioHandler(room, sample_rate=16000, channels=1)
```

#### Methods

##### `async subscribe_to_participant_audio(participant_id: str) -> AsyncIterator[bytes]`

Subscribe to a participant's audio track and yield audio chunks.

**Parameters**:
- `participant_id` (str): ID of participant

**Yields**:
- bytes: Audio chunks (16-bit PCM)

**Raises**:
- `RuntimeError`: If subscription fails

**Example**:
```python
try:
    async for audio_chunk in audio_handler.subscribe_to_participant_audio(participant_id):
        # Process audio chunk
        print(f"Received {len(audio_chunk)} bytes")
except RuntimeError as e:
    print(f"Subscription error: {e}")
```

##### `async publish_audio(audio_stream: AsyncIterator[bytes]) -> None`

Publish audio stream to LiveKit track.

**Parameters**:
- `audio_stream` (AsyncIterator[bytes]): Audio chunks to publish

**Raises**:
- `RuntimeError`: If publishing fails

**Example**:
```python
async def generate_response_audio():
    # Assume tts.synthesize returns AsyncIterator[bytes]
    async for chunk in tts.synthesize("Hello world"):
        yield chunk

try:
    await audio_handler.publish_audio(generate_response_audio())
    print("Audio published successfully")
except RuntimeError as e:
    print(f"Publishing error: {e}")
```

##### `def convert_format(audio: bytes, source_format: str, target_format: str) -> bytes`

Convert audio between formats.

**Parameters**:
- `audio` (bytes): Audio data
- `source_format` (str): Source format ("pcm", "wav", etc.)
- `target_format` (str): Target format ("pcm", "wav", etc.)

**Returns**:
- bytes: Converted audio data

**Example**:
```python
# Convert WAV to PCM
pcm_audio = audio_handler.convert_format(wav_audio, "wav", "pcm")
```

##### `async _buffer_audio(audio_stream: AsyncIterator[bytes], buffer_duration_ms: int = 100) -> AsyncIterator[bytes]`

Buffer audio stream for smooth playback.

**Parameters**:
- `audio_stream` (AsyncIterator[bytes]): Input audio stream
- `buffer_duration_ms` (int): Buffer duration in ms (default: 100)

**Yields**:
- bytes: Buffered audio chunks

**Note**: This is an internal method (starts with `_`)

---

## Data Structures

### Class: `TranscriptionResult`

**Module**: `nora_livekit.voice.stt`

Result from speech-to-text transcription.

#### Fields

```python
@dataclass
class TranscriptionResult:
    text: str                        # Transcribed text
    is_final: bool                   # Is this the final result?
    confidence: Optional[float] = None  # Confidence score (0.0-1.0)
```

**Example**:
```python
async for result in stt.transcribe_stream(audio_stream):
    print(f"Text: {result.text}")
    print(f"Final: {result.is_final}")
    if result.confidence:
        print(f"Confidence: {result.confidence:.2%}")
```

---

## Exceptions

### Standard Exceptions

The Nora-LiveKit framework uses standard Python exceptions:

#### `ValueError`

Raised when configuration or input validation fails.

**Scenarios**:
- Empty API key
- Invalid text length (TTS)
- Missing required configuration

**Example**:
```python
try:
    stt = DeepgramSTT(api_key="")  # Empty key
except ValueError as e:
    print(f"Configuration error: {e}")
```

#### `RuntimeError`

Raised when runtime operations fail (connection, processing).

**Scenarios**:
- Connection failures
- Pipeline not running
- Subscription failures
- Publishing failures

**Example**:
```python
try:
    await pipeline.start()
except RuntimeError as e:
    print(f"Runtime error: {e}")
```

#### `asyncio.TimeoutError`

Raised when async operations exceed timeout.

**Scenarios**:
- API timeouts
- Connection timeouts
- Processing timeouts

**Example**:
```python
import asyncio

try:
    await asyncio.wait_for(pipeline.start(), timeout=5.0)
except asyncio.TimeoutError:
    print("Pipeline startup timed out")
```

---

## Usage Examples

### Complete Voice Agent Setup

```python
import asyncio
from nora_livekit.config import Config
from nora_livekit.agent import NoraAgent

async def main():
    # Load configuration from environment
    config = Config.from_env()

    # Create agent
    agent = NoraAgent(config)

    try:
        # Start agent
        await agent.start()
        print("Agent running. Press Ctrl+C to stop.")

        # Keep agent running
        await asyncio.Event().wait()

    except KeyboardInterrupt:
        print("Shutting down...")
    finally:
        # Graceful shutdown
        await agent.stop()
        print("Agent stopped")

if __name__ == "__main__":
    asyncio.run(main())
```

### Voice Pipeline Processing

```python
async def process_voice_interaction(config, room, participant_id):
    from nora_livekit.voice import VoicePipeline, DeepgramSTT, CartesiaTTS, AudioHandler

    # Initialize components
    stt = DeepgramSTT(api_key=config.voice.deepgram_api_key)
    tts = CartesiaTTS(api_key=config.voice.cartesia_api_key)
    audio_handler = AudioHandler(room)

    # Create pipeline
    pipeline = VoicePipeline(config, stt, tts, audio_handler)

    try:
        # Start pipeline
        await pipeline.start()

        # Process audio from participant
        await pipeline.process_audio_stream(participant_id)

    finally:
        # Stop pipeline
        await pipeline.stop()
```

### Manual STT/TTS Processing

```python
async def transcribe_and_synthesize():
    from nora_livekit.voice.stt import DeepgramSTT
    from nora_livekit.voice.tts import CartesiaTTS

    stt = DeepgramSTT(api_key="your-key")
    tts = CartesiaTTS(api_key="your-key")

    await stt.connect()
    await tts.connect()

    try:
        # Transcribe audio (assume audio_stream is available)
        async for result in stt.transcribe_stream(audio_stream):
            if result.is_final:
                print(f"Transcribed: {result.text}")

                # Synthesize response
                async for audio_chunk in tts.synthesize(f"You said: {result.text}"):
                    # Process audio
                    pass
    finally:
        await stt.disconnect()
        await tts.disconnect()
```

---

## API Compatibility

- **Python**: 3.12+
- **Async Runtime**: asyncio
- **Deepgram SDK**: 5.3.0+
- **Cartesia SDK**: 2.0.17+
- **LiveKit**: 1.0.19+

---

**Document Version**: 1.0
**Last Updated**: November 25, 2025
**Status**: Complete
