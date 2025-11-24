---
spec_id: SPEC-LIVEKIT-002
created: 2025-11-24
updated: 2025-11-24
status: pending
---

# Acceptance Criteria: SPEC-LIVEKIT-002 - Voice Pipeline Integration

**TAG-ACCEPT-VOICE-001**: Voice Pipeline Integration Acceptance Criteria

---

## Overview

This document defines the acceptance criteria for SPEC-LIVEKIT-002 voice pipeline integration. All criteria must be satisfied before considering this SPEC complete and ready for integration with future SPECs.

**Scope**: Voice input/output pipeline with Deepgram STT and Cartesia Sonic TTS
**Dependencies**: SPEC-LIVEKIT-001 foundation must be operational
**Test Approach**: Automated tests using Given-When-Then format + manual verification

---

## Acceptance Criteria Categories

### 1. Configuration and Setup
### 2. Deepgram STT Integration
### 3. Cartesia TTS Integration
### 4. Audio Handler Functionality
### 5. Voice Pipeline Orchestration
### 6. Error Handling and Resilience
### 7. Performance and Quality
### 8. Code Quality and Testing

---

## 1. Configuration and Setup

### AC-001: Voice Configuration Loading

**Given** the .env file contains valid Deepgram and Cartesia API keys
**When** the NoraAgent initializes
**Then** the VoiceConfig is loaded correctly with all required parameters

**Test Implementation**:
```python
def test_voice_config_loading():
    """Test voice configuration loads from environment."""
    os.environ["DEEPGRAM_API_KEY"] = "test-deepgram-key"
    os.environ["CARTESIA_API_KEY"] = "test-cartesia-key"

    config = Config.from_env()

    assert config.voice is not None
    assert config.voice.deepgram_api_key == "test-deepgram-key"
    assert config.voice.cartesia_api_key == "test-cartesia-key"
    assert config.voice.deepgram_model == "nova-2"
    assert config.voice.sample_rate == 16000
```

**Verification**: Unit test passes with 100% coverage

**Status**: ⏳ Pending

---

### AC-002: Missing API Key Validation

**Given** the Deepgram API key is missing from environment variables
**When** the NoraAgent attempts to start
**Then** the agent fails fast with clear error message indicating missing API key

**Test Implementation**:
```python
def test_missing_deepgram_api_key():
    """Test agent fails gracefully when Deepgram API key missing."""
    # Remove Deepgram API key from environment
    if "DEEPGRAM_API_KEY" in os.environ:
        del os.environ["DEEPGRAM_API_KEY"]

    with pytest.raises(ValueError) as exc_info:
        config = Config.from_env()

    assert "DEEPGRAM_API_KEY" in str(exc_info.value)
```

**Verification**: Unit test confirms error handling

**Status**: ⏳ Pending

---

### AC-003: Environment Template Documentation

**Given** a new developer sets up the project
**When** they copy .env.template to .env
**Then** all voice configuration variables are documented with examples and descriptions

**Test Implementation**: Manual verification

**Verification Checklist**:
- [ ] DEEPGRAM_API_KEY documented in .env.template
- [ ] DEEPGRAM_MODEL documented with default value
- [ ] CARTESIA_API_KEY documented in .env.template
- [ ] CARTESIA_VOICE_ID documented with default value
- [ ] VOICE_SAMPLE_RATE documented with default value
- [ ] All optional parameters have default values shown

**Status**: ⏳ Pending

---

## 2. Deepgram STT Integration

### AC-004: Deepgram STT Initialization

**Given** valid Deepgram API credentials
**When** DeepgramSTT client is initialized
**Then** the client is ready for WebSocket connection without errors

**Test Implementation**:
```python
def test_deepgram_stt_initialization():
    """Test Deepgram STT client initializes correctly."""
    stt = DeepgramSTT(
        api_key="test-api-key",
        model="nova-2",
        language="en-US",
    )

    assert stt.api_key == "test-api-key"
    assert stt.model == "nova-2"
    assert stt.language == "en-US"
```

**Verification**: Unit test passes

**Status**: ⏳ Pending

---

### AC-005: Real-time Audio Transcription

**Given** an active Deepgram WebSocket connection
**When** audio stream is sent to Deepgram
**Then** transcription results are received and parsed correctly

**Test Implementation**:
```python
@pytest.mark.asyncio
async def test_audio_transcription():
    """Test audio transcription via Deepgram."""
    stt = DeepgramSTT(api_key="test-key")
    await stt.connect()

    # Mock audio stream
    async def mock_audio_stream():
        yield audio_chunk_1
        yield audio_chunk_2

    results = []
    async for result in stt.transcribe_stream(mock_audio_stream()):
        results.append(result)

    assert len(results) > 0
    assert results[-1].is_final == True
    assert results[-1].text == "expected transcription"
```

**Verification**: Integration test with mocked Deepgram API

**Status**: ⏳ Pending

---

### AC-006: Interim Results Processing

**Given** Deepgram interim results are enabled
**When** audio is being transcribed in real-time
**Then** both interim and final transcription results are emitted

**Test Implementation**:
```python
@pytest.mark.asyncio
async def test_interim_results():
    """Test interim transcription results are processed."""
    stt = DeepgramSTT(api_key="test-key", interim_results=True)

    results = []
    async for result in stt.transcribe_stream(audio_stream):
        results.append(result)

    # Verify we received both interim and final results
    interim_results = [r for r in results if not r.is_final]
    final_results = [r for r in results if r.is_final]

    assert len(interim_results) > 0
    assert len(final_results) > 0
```

**Verification**: Integration test confirms interim result handling

**Status**: ⏳ Pending

---

### AC-007: STT Error Handling

**Given** Deepgram API returns a transient error (503 Service Unavailable)
**When** the error occurs during transcription
**Then** the client retries with exponential backoff (max 3 retries)

**Test Implementation**:
```python
@pytest.mark.asyncio
async def test_stt_retry_on_transient_error():
    """Test STT retries on transient errors."""
    stt = DeepgramSTT(api_key="test-key")

    # Mock Deepgram to return 503 twice, then success
    with patch_deepgram_with_errors(errors=[503, 503, 200]):
        result = await stt.transcribe_stream(audio_stream)

        # Verify 3 attempts were made (2 retries + 1 success)
        assert mock_api.call_count == 3
        assert result is not None
```

**Verification**: Unit test with fault injection

**Status**: ⏳ Pending

---

## 3. Cartesia TTS Integration

### AC-008: Cartesia TTS Initialization

**Given** valid Cartesia API credentials
**When** CartesiaTTS client is initialized
**Then** the client is ready for synthesis without errors

**Test Implementation**:
```python
def test_cartesia_tts_initialization():
    """Test Cartesia TTS client initializes correctly."""
    tts = CartesiaTTS(
        api_key="test-api-key",
        voice_id="default-sonic-voice",
        speed=1.0,
        emotion="neutral",
    )

    assert tts.api_key == "test-api-key"
    assert tts.voice_id == "default-sonic-voice"
    assert tts.speed == 1.0
    assert tts.emotion == "neutral"
```

**Verification**: Unit test passes

**Status**: ⏳ Pending

---

### AC-009: Text-to-Speech Synthesis

**Given** initialized CartesiaTTS client
**When** text input is provided for synthesis
**Then** audio stream is generated and returned

**Test Implementation**:
```python
@pytest.mark.asyncio
async def test_text_to_speech_synthesis():
    """Test text synthesis to audio."""
    tts = CartesiaTTS(api_key="test-key")
    await tts.connect()

    audio_chunks = []
    async for chunk in tts.synthesize("Hello, world!", sample_rate=16000):
        audio_chunks.append(chunk)

    assert len(audio_chunks) > 0
    # Verify audio format
    assert is_valid_audio_format(audio_chunks[0])
```

**Verification**: Integration test with mocked Cartesia API

**Status**: ⏳ Pending

---

### AC-010: Voice Parameter Configuration

**Given** custom voice parameters (speed, emotion)
**When** TTS synthesis is performed
**Then** synthesized audio reflects the configured parameters

**Test Implementation**:
```python
@pytest.mark.asyncio
async def test_voice_parameters():
    """Test voice parameter configuration."""
    tts = CartesiaTTS(
        api_key="test-key",
        speed=1.5,  # Faster speech
        emotion="cheerful",
    )

    audio = await tts.synthesize("Test message")

    # Verify API was called with correct parameters
    assert mock_api.last_request.speed == 1.5
    assert mock_api.last_request.emotion == "cheerful"
```

**Verification**: Unit test with API mocking

**Status**: ⏳ Pending

---

### AC-011: TTS Error Handling

**Given** Cartesia API returns an error
**When** the error occurs during synthesis
**Then** the client handles gracefully with fallback behavior (skip audio response)

**Test Implementation**:
```python
@pytest.mark.asyncio
async def test_tts_error_fallback():
    """Test TTS error handling with fallback."""
    tts = CartesiaTTS(api_key="test-key")

    # Mock Cartesia to return error
    with patch_cartesia_with_error(status=500):
        audio = await tts.synthesize("Test message")

        # Fallback: returns None or empty stream
        assert audio is None or len(list(audio)) == 0

        # Verify error was logged
        assert "voice.tts.error" in captured_logs
```

**Verification**: Unit test with fault injection

**Status**: ⏳ Pending

---

## 4. Audio Handler Functionality

### AC-012: LiveKit Audio Track Subscription

**Given** a participant joins the LiveKit room
**When** AudioHandler subscribes to participant's audio track
**Then** audio chunks are received and yielded correctly

**Test Implementation**:
```python
@pytest.mark.asyncio
async def test_audio_track_subscription():
    """Test subscription to LiveKit audio track."""
    handler = AudioHandler(mock_room, sample_rate=16000)

    audio_chunks = []
    async for chunk in handler.subscribe_to_participant_audio("participant-123"):
        audio_chunks.append(chunk)
        if len(audio_chunks) >= 5:
            break

    assert len(audio_chunks) == 5
    assert all(isinstance(chunk, bytes) for chunk in audio_chunks)
```

**Verification**: Integration test with mocked LiveKit room

**Status**: ⏳ Pending

---

### AC-013: Audio Publishing

**Given** synthesized audio stream from TTS
**When** AudioHandler publishes audio to LiveKit track
**Then** audio is successfully published to the room

**Test Implementation**:
```python
@pytest.mark.asyncio
async def test_audio_publishing():
    """Test publishing audio to LiveKit track."""
    handler = AudioHandler(mock_room)

    async def mock_audio_stream():
        yield audio_chunk_1
        yield audio_chunk_2

    await handler.publish_audio(mock_audio_stream())

    # Verify audio was published to room
    assert mock_room.published_audio_chunks == [audio_chunk_1, audio_chunk_2]
```

**Verification**: Integration test with mocked LiveKit room

**Status**: ⏳ Pending

---

### AC-014: Audio Format Conversion

**Given** audio in one format (e.g., WAV)
**When** conversion to another format is requested (e.g., PCM)
**Then** audio is converted correctly maintaining quality

**Test Implementation**:
```python
def test_audio_format_conversion():
    """Test audio format conversion."""
    handler = AudioHandler(mock_room)

    wav_audio = load_test_audio("test.wav")
    pcm_audio = handler.convert_format(
        wav_audio,
        source_format="wav",
        target_format="pcm",
    )

    assert pcm_audio is not None
    assert len(pcm_audio) > 0
    # Verify PCM format characteristics
    assert is_pcm_format(pcm_audio)
```

**Verification**: Unit test with sample audio files

**Status**: ⏳ Pending

---

### AC-015: Audio Buffering

**Given** incoming audio stream with network jitter
**When** audio buffering is applied
**Then** output audio stream is smooth without gaps

**Test Implementation**:
```python
@pytest.mark.asyncio
async def test_audio_buffering():
    """Test audio buffering smooths playback."""
    handler = AudioHandler(mock_room)

    # Simulate jittery input (irregular chunk timing)
    async def jittery_audio():
        yield chunk1
        await asyncio.sleep(0.05)
        yield chunk2
        await asyncio.sleep(0.15)  # Longer delay
        yield chunk3

    buffered_chunks = []
    async for chunk in handler._buffer_audio(jittery_audio(), buffer_duration_ms=100):
        buffered_chunks.append(chunk)

    # Verify smooth output (chunks delivered at consistent intervals)
    assert len(buffered_chunks) == 3
```

**Verification**: Unit test with timing verification

**Status**: ⏳ Pending

---

## 5. Voice Pipeline Orchestration

### AC-016: Voice Pipeline Initialization

**Given** NoraAgent has joined a LiveKit room
**When** VoicePipeline is started
**Then** STT, TTS, and AudioHandler are initialized and ready

**Test Implementation**:
```python
@pytest.mark.asyncio
async def test_voice_pipeline_initialization():
    """Test voice pipeline initializes all components."""
    config = Config.from_env()
    stt = DeepgramSTT(api_key=config.voice.deepgram_api_key)
    tts = CartesiaTTS(api_key=config.voice.cartesia_api_key)
    audio_handler = AudioHandler(mock_room)

    pipeline = VoicePipeline(config, stt, tts, audio_handler)
    await pipeline.start()

    # Verify components are initialized
    assert stt.is_connected
    assert tts.is_connected
    assert pipeline.is_running
```

**Verification**: Integration test

**Status**: ⏳ Pending

---

### AC-017: End-to-End Voice Processing

**Given** a participant speaks to the agent
**When** audio is received through the voice pipeline
**Then** audio is transcribed, processed, synthesized, and response is played back

**Test Implementation**:
```python
@pytest.mark.asyncio
async def test_end_to_end_voice_processing():
    """Test complete voice pipeline flow."""
    pipeline = VoicePipeline(config, stt, tts, audio_handler)
    await pipeline.start()

    # Simulate participant speaking
    mock_room.simulate_participant_audio(test_audio_file)

    # Wait for processing
    await asyncio.sleep(1.0)

    # Verify transcription occurred
    assert "voice.stt.transcription" in captured_logs

    # Verify synthesis occurred
    assert "voice.tts.synthesis_completed" in captured_logs

    # Verify audio was published
    assert mock_room.has_published_audio
```

**Verification**: End-to-end integration test

**Status**: ⏳ Pending

---

### AC-018: Graceful Pipeline Shutdown

**Given** voice pipeline is running
**When** pipeline.stop() is called
**Then** all resources are cleaned up within 5 seconds

**Test Implementation**:
```python
@pytest.mark.asyncio
async def test_pipeline_graceful_shutdown():
    """Test voice pipeline shuts down gracefully."""
    pipeline = VoicePipeline(config, stt, tts, audio_handler)
    await pipeline.start()

    start_time = time.time()
    await pipeline.stop()
    shutdown_duration = time.time() - start_time

    # Verify shutdown completed within 5 seconds
    assert shutdown_duration < 5.0

    # Verify resources cleaned up
    assert not stt.is_connected
    assert not tts.is_connected
    assert not pipeline.is_running
```

**Verification**: Integration test with timing

**Status**: ⏳ Pending

---

## 6. Error Handling and Resilience

### AC-019: STT Connection Failure Retry

**Given** Deepgram WebSocket connection fails
**When** the failure is transient (network issue)
**Then** connection is retried with exponential backoff (1s, 2s, 4s)

**Test Implementation**:
```python
@pytest.mark.asyncio
async def test_stt_connection_retry():
    """Test STT connection retry with exponential backoff."""
    stt = DeepgramSTT(api_key="test-key")

    with patch_deepgram_connection_failure(fail_count=2):
        await stt.connect()

        # Verify 3 attempts (1 initial + 2 retries)
        assert mock_connection.attempt_count == 3

        # Verify backoff delays
        assert mock_connection.delays == [0, 1.0, 2.0]
```

**Verification**: Unit test with fault injection

**Status**: ⏳ Pending

---

### AC-020: TTS Rate Limit Handling

**Given** Cartesia API returns 429 (Too Many Requests)
**When** synthesis is attempted
**Then** request is not retried, error is logged, and fallback behavior activates

**Test Implementation**:
```python
@pytest.mark.asyncio
async def test_tts_rate_limit_handling():
    """Test TTS rate limit handling."""
    tts = CartesiaTTS(api_key="test-key")

    with patch_cartesia_rate_limit():
        audio = await tts.synthesize("Test message")

        # Fallback: no audio returned
        assert audio is None

        # Verify error logged
        assert "voice.tts.error" in captured_logs
        assert "rate_limit" in captured_logs[-1]
```

**Verification**: Unit test with rate limit simulation

**Status**: ⏳ Pending

---

### AC-021: Pipeline Continues After TTS Failure

**Given** voice pipeline is running
**When** TTS synthesis fails for one response
**Then** pipeline continues operating for subsequent requests

**Test Implementation**:
```python
@pytest.mark.asyncio
async def test_pipeline_resilience_to_tts_failure():
    """Test pipeline continues after TTS failure."""
    pipeline = VoicePipeline(config, stt, tts, audio_handler)
    await pipeline.start()

    # First request: TTS fails
    with patch_cartesia_error():
        await pipeline._handle_transcription("First message")

    # Second request: TTS succeeds
    await pipeline._handle_transcription("Second message")

    # Verify pipeline still running
    assert pipeline.is_running

    # Verify second request succeeded
    assert mock_room.has_published_audio
```

**Verification**: Integration test with fault injection

**Status**: ⏳ Pending

---

## 7. Performance and Quality

### AC-022: End-to-End Latency <500ms

**Given** a complete voice interaction
**When** latency is measured from audio input to audio output
**Then** 95th percentile latency is less than 500ms

**Test Implementation**:
```python
@pytest.mark.asyncio
async def test_end_to_end_latency():
    """Test end-to-end voice latency."""
    pipeline = VoicePipeline(config, stt, tts, audio_handler)
    await pipeline.start()

    latencies = []
    for _ in range(100):
        start_time = time.time()

        # Simulate audio input
        mock_room.simulate_participant_audio(test_audio)

        # Wait for audio output
        await wait_for_audio_output()

        latency_ms = (time.time() - start_time) * 1000
        latencies.append(latency_ms)

    p95_latency = np.percentile(latencies, 95)
    assert p95_latency < 500.0
```

**Verification**: Performance benchmark test

**Status**: ⏳ Pending

---

### AC-023: Transcription Accuracy >90%

**Given** a standard test dataset with clear speech
**When** audio samples are transcribed
**Then** transcription accuracy is greater than 90%

**Test Implementation**:
```python
@pytest.mark.asyncio
async def test_transcription_accuracy():
    """Test STT transcription accuracy."""
    stt = DeepgramSTT(api_key=config.voice.deepgram_api_key)
    await stt.connect()

    test_dataset = load_standard_test_dataset()

    correct = 0
    total = len(test_dataset)

    for sample in test_dataset:
        transcription = await stt.transcribe_audio(sample.audio)
        if transcription == sample.expected_text:
            correct += 1

    accuracy = (correct / total) * 100
    assert accuracy > 90.0
```

**Verification**: Accuracy benchmark with standard dataset

**Status**: ⏳ Pending

---

### AC-024: Continuous Conversation (10 Minutes)

**Given** voice pipeline handling continuous conversation
**When** conversation runs for 10 minutes
**Then** pipeline maintains quality without memory leaks or degradation

**Test Implementation**:
```python
@pytest.mark.asyncio
async def test_continuous_conversation():
    """Test voice pipeline handles 10-minute conversation."""
    pipeline = VoicePipeline(config, stt, tts, audio_handler)
    await pipeline.start()

    start_memory = get_memory_usage()
    start_time = time.time()

    # Simulate 10 minutes of conversation
    while time.time() - start_time < 600:
        mock_room.simulate_participant_audio(test_audio)
        await asyncio.sleep(5)

    end_memory = get_memory_usage()

    # Verify no significant memory increase (< 50MB growth)
    memory_growth = end_memory - start_memory
    assert memory_growth < 50 * 1024 * 1024  # 50MB

    # Verify pipeline still functional
    assert pipeline.is_running
```

**Verification**: Stress test with memory monitoring

**Status**: ⏳ Pending

---

## 8. Code Quality and Testing

### AC-025: Test Coverage ≥90%

**Given** voice pipeline implementation complete
**When** test coverage is measured
**Then** all voice modules achieve ≥90% code coverage

**Test Implementation**: Automated coverage measurement

**Verification Command**:
```bash
poetry run pytest --cov=src/nora_livekit/voice --cov-report=term-missing
```

**Coverage Requirements**:
- [ ] pipeline.py: ≥90%
- [ ] stt.py: ≥90%
- [ ] tts.py: ≥90%
- [ ] audio_handler.py: ≥90%
- [ ] Overall voice module: ≥90%

**Status**: ⏳ Pending

---

### AC-026: Type Checking Passes

**Given** voice pipeline code with type hints
**When** mypy strict mode is run
**Then** zero type errors are reported

**Test Implementation**: Automated type checking

**Verification Command**:
```bash
poetry run mypy src/nora_livekit/voice --strict
```

**Status**: ⏳ Pending

---

### AC-027: Linting Passes

**Given** voice pipeline code
**When** Ruff linter is run
**Then** zero linting errors are reported

**Test Implementation**: Automated linting

**Verification Command**:
```bash
poetry run ruff check src/nora_livekit/voice
```

**Status**: ⏳ Pending

---

### AC-028: Code Formatting Passes

**Given** voice pipeline code
**When** Black formatter check is run
**Then** zero formatting changes are required

**Test Implementation**: Automated formatting check

**Verification Command**:
```bash
poetry run black --check src/nora_livekit/voice
```

**Status**: ⏳ Pending

---

## Manual Verification Checklist

### Documentation

- [ ] Voice pipeline architecture documented in docs/VOICE_PIPELINE.md
- [ ] API rate limits and costs documented in docs/API_COSTS.md
- [ ] README updated with voice pipeline usage examples
- [ ] .env.template contains all voice configuration variables with descriptions

### Integration

- [ ] Voice pipeline integrates with NoraAgent lifecycle
- [ ] Voice pipeline starts automatically after room join
- [ ] Voice pipeline stops cleanly during agent shutdown
- [ ] Health check endpoint reflects voice pipeline status (optional)

### User Experience

- [ ] Voice interaction feels natural (subjective test)
- [ ] Response latency is acceptable (<500ms perceived)
- [ ] Voice quality is clear and understandable
- [ ] Transcription accuracy is acceptable for typical use cases
- [ ] Error messages are helpful and actionable

---

## Definition of Done

**All acceptance criteria must be satisfied**:

✅ **Configuration and Setup** (AC-001 to AC-003)
✅ **Deepgram STT Integration** (AC-004 to AC-007)
✅ **Cartesia TTS Integration** (AC-008 to AC-011)
✅ **Audio Handler Functionality** (AC-012 to AC-015)
✅ **Voice Pipeline Orchestration** (AC-016 to AC-018)
✅ **Error Handling and Resilience** (AC-019 to AC-021)
✅ **Performance and Quality** (AC-022 to AC-024)
✅ **Code Quality and Testing** (AC-025 to AC-028)

**Quality Gates**:
- [ ] Test coverage ≥90% for all voice modules
- [ ] Mypy passes with zero errors
- [ ] Ruff passes with zero errors
- [ ] Black passes with zero changes
- [ ] All integration tests pass consistently (100% over 10 runs)
- [ ] Performance targets met (latency <500ms, accuracy >90%)
- [ ] Documentation complete and reviewed

**Deployment Readiness**:
- [ ] Voice pipeline successfully deploys to Railway
- [ ] Health check endpoint reports healthy status
- [ ] Logs confirm voice pipeline operational
- [ ] Manual smoke test confirms end-to-end voice interaction

---

## Review and Sign-Off

**Reviewed By**: [Reviewer Name]
**Review Date**: [Date]
**Approved By**: [Approver Name]
**Approval Date**: [Date]

**Notes**: [Any additional notes or observations]

---

**TAG-ACCEPT-VOICE-001**: End of Acceptance Criteria
