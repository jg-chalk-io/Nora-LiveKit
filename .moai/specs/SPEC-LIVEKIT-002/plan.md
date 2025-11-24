---
spec_id: SPEC-LIVEKIT-002
created: 2025-11-24
updated: 2025-11-24
status: pending
---

# Implementation Plan: SPEC-LIVEKIT-002 - Voice Pipeline Integration

**TAG-PLAN-VOICE-001**: Voice Pipeline Integration Implementation Plan

---

## Overview

This implementation plan outlines the development approach for integrating Deepgram STT and Cartesia Sonic TTS into the Nora LiveKit agent foundation. The plan follows Test-Driven Development (TDD) principles with RED-GREEN-REFACTOR cycles for each component.

**Dependencies**:
- SPEC-LIVEKIT-001 (Foundation) must be completed and stable
- Agent lifecycle and room management must be operational
- Health check infrastructure must be in place

**Scope**:
- Voice input processing (Deepgram STT)
- Voice output generation (Cartesia Sonic TTS)
- Audio track handling for LiveKit
- End-to-end voice pipeline orchestration

**Out of Scope** (Deferred to Future SPECs):
- Conversation context and state management (SPEC-003)
- Business hours logic (SPEC-004)
- Supabase database integration (SPEC-006)
- Tool integrations (SPEC-007)

---

## Technology Stack

### Core Dependencies

| Library | Version | Purpose | Installation |
|---------|---------|---------|--------------|
| deepgram-sdk | ~5.3.0 | Speech-to-text transcription | `poetry add deepgram-sdk~5.3` |
| cartesia | ~2.0.17 | Text-to-speech synthesis | `poetry add cartesia~2.0.17` |
| numpy | ~2.0 | Audio processing and manipulation | `poetry add numpy~2.0` |
| soundfile | ~0.12 | Audio file I/O | `poetry add soundfile~0.12` |

**Note**: Exact versions will be finalized during dependency installation. These versions represent the latest stable releases as of November 2025.

### Existing Foundation (SPEC-001)

- Python 3.12+
- livekit-agents ~1.0 (with audio plugins)
- FastAPI ~0.115
- structlog ~24.4

---

## Implementation Milestones

### Phase 1: Foundation and Configuration (Primary Goal)

**Objective**: Extend project configuration and establish voice pipeline module structure

**Priority**: Primary Goal

**Dependencies**: SPEC-LIVEKIT-001 completed

**Tasks**:
1. **Extend Configuration Module**
   - Add VoiceConfig dataclass to config.py
   - Implement environment variable loading for Deepgram and Cartesia
   - Add validation for API keys and voice parameters
   - Update .env.template with voice configuration

2. **Create Voice Module Structure**
   - Create src/nora_livekit/voice/ directory
   - Create __init__.py with module exports
   - Setup voice module logging configuration
   - Create test directory structure: tests/voice/

3. **Add Dependencies**
   - Update pyproject.toml with deepgram-sdk, cartesia, numpy, soundfile
   - Run `poetry lock` to resolve dependencies
   - Run `poetry install` to install new dependencies
   - Verify installations with version checks

**Deliverables**:
- Extended config.py with VoiceConfig
- Voice module structure created
- Updated pyproject.toml and poetry.lock
- Updated .env.template with voice variables

**Test Coverage Target**: 90%+ for configuration validation

---

### Phase 2: Audio Handler Implementation (Primary Goal)

**Objective**: Implement LiveKit audio track management for publishing and subscribing

**Priority**: Primary Goal

**Dependencies**: Phase 1 completed

**Tasks**:
1. **Implement AudioHandler Class**
   - Create audio_handler.py with AudioHandler class
   - Implement subscribe_to_participant_audio() method
   - Implement publish_audio() method
   - Implement audio format conversion utilities

2. **Audio Buffering and Processing**
   - Implement audio buffering logic for smooth playback
   - Add voice activity detection (VAD) integration
   - Implement audio format conversion (PCM, WAV)
   - Add sample rate conversion utilities

3. **Unit Tests for AudioHandler**
   - Write tests for audio subscription (mock LiveKit tracks)
   - Write tests for audio publishing
   - Write tests for format conversion
   - Write tests for buffering logic

**Deliverables**:
- AudioHandler class with full functionality
- Audio processing utilities
- Comprehensive unit tests (90%+ coverage)

**Test Coverage Target**: 90%+ for AudioHandler module

---

### Phase 3: Deepgram STT Integration (Primary Goal)

**Objective**: Integrate Deepgram SDK for real-time speech-to-text transcription

**Priority**: Primary Goal

**Dependencies**: Phase 2 completed

**Tasks**:
1. **Implement DeepgramSTT Class**
   - Create stt.py with DeepgramSTT class
   - Implement WebSocket connection to Deepgram API
   - Implement transcribe_stream() method
   - Handle interim and final transcription results

2. **Error Handling and Retries**
   - Implement retry logic with exponential backoff
   - Handle transient errors (connection failures, timeouts)
   - Handle permanent errors (invalid API key, rate limits)
   - Add structured logging for all STT events

3. **Unit Tests for DeepgramSTT**
   - Write tests for STT initialization
   - Write tests for WebSocket connection
   - Write tests for transcription result parsing
   - Write tests for error handling and retries
   - Mock Deepgram API responses

**Deliverables**:
- DeepgramSTT class with streaming transcription
- Error handling and retry logic
- Comprehensive unit tests with mocked API

**Test Coverage Target**: 90%+ for STT module

---

### Phase 4: Cartesia TTS Integration (Primary Goal)

**Objective**: Integrate Cartesia SDK for text-to-speech synthesis

**Priority**: Primary Goal

**Dependencies**: Phase 2 completed (can be developed in parallel with Phase 3)

**Tasks**:
1. **Implement CartesiaTTS Class**
   - Create tts.py with CartesiaTTS class
   - Implement synthesize() method for text-to-audio conversion
   - Support configurable voice parameters (voice_id, speed, emotion)
   - Implement streaming audio generation

2. **Error Handling and Fallback**
   - Implement retry logic for transient errors
   - Add fallback behavior for TTS failures
   - Handle API rate limits gracefully
   - Add structured logging for all TTS events

3. **Unit Tests for CartesiaTTS**
   - Write tests for TTS initialization
   - Write tests for audio synthesis
   - Write tests for voice parameter configuration
   - Write tests for error handling and fallback
   - Mock Cartesia API responses

**Deliverables**:
- CartesiaTTS class with streaming synthesis
- Error handling and fallback logic
- Comprehensive unit tests with mocked API

**Test Coverage Target**: 90%+ for TTS module

---

### Phase 5: Voice Pipeline Orchestration (Secondary Goal)

**Objective**: Integrate STT, TTS, and audio handler into unified voice pipeline

**Priority**: Secondary Goal

**Dependencies**: Phases 3 and 4 completed

**Tasks**:
1. **Implement VoicePipeline Class**
   - Create pipeline.py with VoicePipeline class
   - Orchestrate audio flow: input → STT → processing → TTS → output
   - Implement start() and stop() lifecycle methods
   - Integrate with NoraAgent from SPEC-001

2. **Audio Stream Processing**
   - Implement process_audio_stream() method
   - Handle transcription results
   - Generate response text (simple echo for this SPEC)
   - Synthesize and publish response audio

3. **Integration Tests**
   - Write end-to-end pipeline tests
   - Test audio stream processing flow
   - Test concurrent audio handling
   - Test graceful shutdown and cleanup

**Deliverables**:
- VoicePipeline orchestrator class
- Integration with NoraAgent
- End-to-end integration tests

**Test Coverage Target**: 90%+ for pipeline module

---

### Phase 6: Agent Integration (Secondary Goal)

**Objective**: Integrate voice pipeline into NoraAgent lifecycle

**Priority**: Secondary Goal

**Dependencies**: Phase 5 completed

**Tasks**:
1. **Extend NoraAgent**
   - Initialize VoicePipeline in agent startup
   - Start voice pipeline after room join
   - Stop voice pipeline during shutdown
   - Handle voice pipeline errors gracefully

2. **Configuration Integration**
   - Load voice configuration from environment
   - Validate voice API keys on startup
   - Initialize STT and TTS clients with configuration
   - Add voice status to health check endpoint (optional)

3. **Integration Tests**
   - Test agent lifecycle with voice pipeline
   - Test room join with voice pipeline activation
   - Test graceful shutdown with voice cleanup
   - Test error handling and recovery

**Deliverables**:
- Extended NoraAgent with voice pipeline
- Full lifecycle integration
- Updated integration tests

**Test Coverage Target**: Maintain 90%+ overall test coverage

---

### Phase 7: Performance Optimization and Benchmarking (Final Goal)

**Objective**: Optimize voice pipeline performance and validate latency targets

**Priority**: Final Goal

**Dependencies**: Phase 6 completed

**Tasks**:
1. **Latency Benchmarking**
   - Measure end-to-end latency (audio → transcription → synthesis → playback)
   - Identify bottlenecks in pipeline
   - Optimize audio buffering and format conversion
   - Target: <500ms at 95th percentile

2. **Accuracy Testing**
   - Test transcription accuracy with standard dataset
   - Test with various accents and speech patterns
   - Target: >90% accuracy for clear speech
   - Document known limitations

3. **Stress Testing**
   - Test continuous conversation (10+ minutes)
   - Test under network jitter and latency
   - Test concurrent audio streams
   - Verify resource cleanup and no memory leaks

4. **Documentation**
   - Document voice pipeline architecture
   - Document API rate limits and costs
   - Document performance benchmarks
   - Update README with voice pipeline usage

**Deliverables**:
- Performance benchmark results
- Accuracy test results
- Stress test results
- Comprehensive documentation

**Performance Targets**:
- Latency: <500ms end-to-end (95th percentile)
- Accuracy: >90% transcription accuracy
- Reliability: 99.9% uptime (excluding API outages)

---

## Technical Approach

### Test-Driven Development (TDD)

**RED-GREEN-REFACTOR Cycle**:

1. **RED**: Write failing test for desired behavior
   - Define expected interface and behavior
   - Write test that fails because feature not implemented
   - Ensure test fails for the right reason

2. **GREEN**: Implement minimum code to pass test
   - Write simplest code that makes test pass
   - Don't optimize prematurely
   - Verify test passes

3. **REFACTOR**: Improve code quality while keeping tests passing
   - Improve code structure and readability
   - Remove duplication
   - Optimize performance where needed
   - Ensure all tests still pass

**Test Strategy**:
- Unit tests for each class and method (mock external APIs)
- Integration tests for component interactions
- End-to-end tests for full pipeline flow
- Performance tests for latency and throughput
- Accuracy tests for transcription quality

### Error Handling Strategy

**Transient Errors** (Retry with exponential backoff):
- Network failures
- Temporary API unavailability
- Connection timeouts

**Retry Configuration**:
- Max retries: 3
- Backoff delays: 1s, 2s, 4s
- Log each retry attempt with structured logging

**Permanent Errors** (Log and fail gracefully):
- Invalid API keys (401 Unauthorized)
- Rate limits exceeded (429 Too Many Requests)
- Invalid parameters (400 Bad Request)

**Fallback Behavior**:
- STT failure: Log error, skip processing, continue listening
- TTS failure: Log error, skip audio response, continue conversation
- Pipeline failure: Log error, attempt restart, fallback to degraded mode

### Logging Strategy

**Structured Logging Events**:
- All events use structlog JSON format
- Include contextual information (timestamps, request IDs, durations)
- Log levels: DEBUG (detailed), INFO (operational), WARNING (recoverable), ERROR (failures)

**Voice Pipeline Events**:
- `voice.pipeline.started`: Pipeline initialization
- `voice.stt.transcription`: Transcription result (include text, is_final, confidence)
- `voice.tts.synthesis_started`: TTS synthesis initiated
- `voice.tts.synthesis_completed`: TTS completed (include duration_ms)
- `voice.audio.published`: Audio published to LiveKit track
- `voice.error.*`: All error events with full context

### Performance Considerations

**Latency Optimization**:
- Use WebSocket streaming for real-time processing
- Minimize audio buffering (target: 100ms buffers)
- Process audio in parallel with synthesis when possible
- Use interim STT results for faster feedback

**Resource Management**:
- Properly close WebSocket connections on shutdown
- Cleanup audio buffers and resources
- Monitor memory usage during long conversations
- Implement connection pooling if needed

**API Cost Optimization**:
- Implement voice activity detection (VAD) to reduce unnecessary API calls
- Cache common responses (future enhancement)
- Monitor API usage and implement alerts
- Use development API rate limits during testing

---

## Architecture Design

### Component Dependencies

```
NoraAgent (SPEC-001)
    ↓
VoicePipeline
    ├── AudioHandler (LiveKit audio tracks)
    ├── DeepgramSTT (Speech-to-text)
    └── CartesiaTTS (Text-to-speech)
```

### Data Flow

```
1. Participant speaks → LiveKit audio track
2. AudioHandler subscribes to track → audio stream
3. DeepgramSTT receives audio → WebSocket to Deepgram API
4. Deepgram returns transcription → text result
5. VoicePipeline processes text → generate response
6. CartesiaTTS synthesizes response → audio stream
7. AudioHandler publishes audio → LiveKit track
8. Participant hears response
```

### Concurrency Model

- Asynchronous I/O for all API calls
- Separate tasks for STT input and TTS output
- Audio streaming uses AsyncIterator pattern
- Graceful shutdown waits for in-flight operations (max 5s timeout)

---

## Risk Mitigation

### Technical Risks

**RISK-001: Deepgram API latency exceeds target**
- **Mitigation**: Use interim results, optimize network path, implement local buffering
- **Contingency**: Document latency issues, consider alternative STT providers if persistent

**RISK-002: Audio format incompatibility**
- **Mitigation**: Standardize on PCM 16kHz mono, implement robust format conversion
- **Contingency**: Add support for multiple audio formats if needed

**RISK-003: Memory leaks during streaming**
- **Mitigation**: Implement proper resource cleanup, add memory monitoring, profile code
- **Contingency**: Add memory limits and automatic restart on high memory usage

### Operational Risks

**RISK-004: API costs exceed budget**
- **Mitigation**: Monitor API usage, implement usage alerts, use free tier limits during development
- **Contingency**: Implement request throttling and rate limiting

**RISK-005: Network failures disrupt audio**
- **Mitigation**: Implement retry logic, buffer audio, graceful degradation
- **Contingency**: Provide fallback to text-only mode if voice fails

---

## Quality Gates

### Code Quality

- [ ] 90%+ test coverage for all voice modules
- [ ] Mypy type checking passes with zero errors
- [ ] Ruff linting passes with zero errors
- [ ] Black formatting passes with zero changes

### Performance

- [ ] End-to-end latency <500ms (95th percentile)
- [ ] STT transcription accuracy >90% for clear speech
- [ ] Voice pipeline handles 10-minute conversations without degradation
- [ ] No memory leaks during extended operation

### Reliability

- [ ] All unit tests pass consistently (100% pass rate over 10 runs)
- [ ] All integration tests pass consistently
- [ ] Error handling tested with fault injection
- [ ] Graceful shutdown completes within 5 seconds

### Documentation

- [ ] Voice pipeline architecture documented
- [ ] API usage and costs documented
- [ ] Configuration options documented in .env.template
- [ ] README updated with voice pipeline usage examples

---

## Success Criteria

**Definition of Done**:
1. All implementation phases completed
2. All quality gates passed
3. Performance targets met
4. Test coverage ≥90%
5. Documentation complete and reviewed
6. Voice pipeline integrated into NoraAgent lifecycle
7. End-to-end voice conversation functional

**User Acceptance Criteria**:
- User can speak to agent and receive voice response
- Transcription accuracy is acceptable (>90% for clear speech)
- Response latency feels natural (<500ms)
- Voice quality is clear and natural-sounding
- Agent handles errors gracefully without crashing

---

**Next Steps After SPEC-002 Completion**:
1. Review and document lessons learned
2. Measure actual API costs for future budgeting
3. Prepare for SPEC-LIVEKIT-003 (Session Context Management)
4. Consider voice quality improvements based on feedback

---

**TAG-PLAN-VOICE-001**: End of Implementation Plan
