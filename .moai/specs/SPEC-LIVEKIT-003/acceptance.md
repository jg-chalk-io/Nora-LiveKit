# SPEC-LIVEKIT-003: Acceptance Criteria

**SPEC ID**: SPEC-LIVEKIT-003
**Title**: Context & Conversation Engine
**Version**: 0.1.0
**Status**: Draft

---

## Overview

This document defines comprehensive acceptance criteria for the Context & Conversation Engine using Given/When/Then format. Each scenario includes:

- **Given**: Initial state and preconditions
- **When**: Action or event trigger
- **Then**: Expected outcomes and verification steps
- **Verification Method**: How to validate the acceptance criteria

**Test Coverage Target**: 90%+ for all conversation modules

**Success Criteria**: All scenarios must pass with deterministic, repeatable results

---

## AC-001: Basic Greeting Flow

### Scenario 1.1: Initial Greeting Generation

**Given**:
- ConversationEngine is initialized with OpenAI provider
- Conversation context is empty (no messages)
- Conversation phase is GREETING
- LLM model is configured as gpt-4

**When**:
- engine.start() is called
- User says "hello" (transcribed as "hello")
- process_transcription("hello", participant_id="user-123") is called

**Then**:
- LLM receives system prompt for GREETING phase
- System prompt includes: "You are Nora, a friendly AI voice assistant. The conversation is just starting..."
- LLM generates warm greeting response (1-2 sentences)
- Response text is formatted for TTS (no markdown)
- User message is added to context with role="user", content="hello"
- Assistant response is added to context with role="assistant"
- Context history contains exactly 2 messages (user + assistant)
- Response text is returned for TTS synthesis
- Metrics logged: tokens_used, latency_ms, model="gpt-4"

**Verification Method**:
```python
async def test_basic_greeting_flow():
    # Arrange
    config = ConversationConfig(
        llm_provider="openai",
        llm_api_key="test-key",
        llm_model="gpt-4",
    )
    context = ConversationContext(max_history=20)
    llm = LLMIntegration(...)
    engine = ConversationEngine(config, context, llm, turn_manager)

    # Act
    await engine.start()
    response = await engine.process_transcription("hello", "user-123")

    # Assert
    assert len(context.get_history()) == 2
    assert context.get_history()[0].role == "user"
    assert context.get_history()[0].content == "hello"
    assert context.get_history()[1].role == "assistant"
    assert response == context.get_history()[1].content
    assert "**" not in response  # No markdown
    assert "_" not in response   # No markdown
```

**Success Metrics**:
- ✅ Response generated in <1000ms (95th percentile)
- ✅ Response contains 1-2 sentences
- ✅ No markdown syntax in response
- ✅ Context history accurately reflects conversation

---

## AC-002: Multi-Turn Q&A with Context

### Scenario 2.1: Context Retention Across Turns

**Given**:
- Conversation has progressed to ACTIVE phase
- Context contains 5 previous messages:
  1. User: "What is the capital of France?"
  2. Assistant: "The capital of France is Paris."
  3. User: "How about Germany?"
  4. Assistant: "The capital of Germany is Berlin."
  5. User: "Which one is larger?"

**When**:
- User asks follow-up: "What was my first question?"
- process_transcription("What was my first question?", "user-123") is called

**Then**:
- LLM receives ALL 6 messages (5 previous + new question) in format_for_llm() format
- LLM response references first question: "Your first question was about the capital of France."
- Response demonstrates contextual awareness
- New user message is added to context (total: 7 messages)
- Assistant response is added to context (total: 8 messages)
- Context history maintains chronological order

**Verification Method**:
```python
async def test_context_retention():
    # Arrange: Pre-populate context with 5 messages
    context = ConversationContext(max_history=20)
    context.add_message("user", "What is the capital of France?", "user-123")
    context.add_message("assistant", "The capital of France is Paris.", None)
    context.add_message("user", "How about Germany?", "user-123")
    context.add_message("assistant", "The capital of Germany is Berlin.", None)
    context.add_message("user", "Which one is larger?", "user-123")

    # Act: Ask follow-up question referencing first message
    response = await engine.process_transcription(
        "What was my first question?",
        "user-123"
    )

    # Assert: Verify LLM received full context
    assert len(context.get_history()) == 8  # 5 previous + 2 new + 1 response
    assert "France" in response or "capital" in response.lower()
    # Verify LLM API was called with 6 messages (5 + new question)
    mock_llm.generate_response.assert_called_once()
    call_args = mock_llm.generate_response.call_args
    assert len(call_args[0][0].format_for_llm()) == 6
```

**Success Metrics**:
- ✅ LLM receives complete conversation history
- ✅ Response demonstrates understanding of previous context
- ✅ Context history grows correctly (2 messages per turn)
- ✅ Message order is chronological

### Scenario 2.2: Context Window Auto-Pruning

**Given**:
- ConversationContext initialized with max_history=20
- Context currently contains 20 messages (at limit)

**When**:
- User sends 21st message: "Tell me more"
- process_transcription("Tell me more", "user-123") is called
- Assistant response is generated (22nd message attempt)

**Then**:
- Oldest message (message 1) is automatically removed
- Message 2 becomes the oldest message
- New user message (21st) is added
- Total messages remains at 20 (not 21)
- When assistant response is added, message 2 is removed
- Final history contains messages 3-22 (20 total)
- Pruning happens FIFO (First In, First Out)

**Verification Method**:
```python
async def test_context_pruning():
    # Arrange: Fill context to max_history limit
    context = ConversationContext(max_history=20)
    for i in range(20):
        context.add_message(
            "user" if i % 2 == 0 else "assistant",
            f"Message {i+1}",
            "user-123" if i % 2 == 0 else None
        )

    # Capture first message content before pruning
    first_message = context.get_history()[0].content

    # Act: Add 21st and 22nd messages
    await engine.process_transcription("Tell me more", "user-123")

    # Assert: Oldest messages pruned
    history = context.get_history()
    assert len(history) == 20
    assert first_message not in [msg.content for msg in history]
    assert "Message 3" == history[0].content  # Message 1-2 pruned
```

**Success Metrics**:
- ✅ Context never exceeds max_history limit
- ✅ Pruning is automatic and transparent
- ✅ FIFO order is maintained
- ✅ No memory leaks from unbounded growth

---

## AC-003: Turn-Taking Detection

### Scenario 3.1: Normal Turn Boundary Detection

**Given**:
- TurnManager is initialized with:
  - vad_threshold=0.5
  - min_speech_duration_ms=300
  - silence_duration_ms=700
- Audio stream is active
- Agent is NOT speaking (set_agent_speaking=False)

**When**:
- User speaks for 400ms (exceeds min_speech_duration_ms)
- User pauses for 800ms (exceeds silence_duration_ms)

**Then**:
- USER_TURN_END event is emitted within 100ms of silence detection
- Event contains participant_id
- Event timestamp is accurate to within 50ms
- Transcription processing begins immediately
- No additional turn events are emitted during silence

**Verification Method**:
```python
async def test_turn_detection():
    # Arrange
    turn_manager = TurnManager(
        vad_threshold=0.5,
        min_speech_duration_ms=300,
        silence_duration_ms=700,
    )
    audio_stream = create_synthetic_audio(
        speech_duration_ms=400,
        silence_duration_ms=800,
    )

    # Act
    start_time = time.time()
    await turn_manager.start(audio_stream)
    turn_data = await turn_manager.wait_for_turn()
    detection_latency = (time.time() - start_time - 1.2) * 1000  # ms

    # Assert
    assert turn_data.event == TurnEvent.USER_TURN_END
    assert detection_latency < 100  # <100ms latency
    assert turn_data.participant_id is not None
```

**Success Metrics**:
- ✅ Turn detection latency <100ms (95th percentile)
- ✅ 95%+ accuracy on synthetic audio
- ✅ No false positives during silence

### Scenario 3.2: Short Speech Burst Filtering

**Given**:
- TurnManager configured with min_speech_duration_ms=300
- Audio stream is active

**When**:
- User makes short vocal noise (100ms) - e.g., cough, "um"
- Followed by 800ms silence

**Then**:
- No USER_TURN_END event is emitted (speech too short)
- Turn manager continues monitoring
- Only speech >300ms triggers turn events
- Short bursts are ignored

**Verification Method**:
```python
async def test_short_speech_filtering():
    # Arrange
    turn_manager = TurnManager(min_speech_duration_ms=300)
    audio_stream = create_synthetic_audio(
        speech_duration_ms=100,  # Below threshold
        silence_duration_ms=800,
    )

    # Act
    await turn_manager.start(audio_stream)
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(turn_manager.wait_for_turn(), timeout=2.0)

    # Assert: No event emitted (timeout expected)
```

**Success Metrics**:
- ✅ Speech <300ms is filtered out
- ✅ No false positive turn events
- ✅ Reduces over-sensitivity to noise

---

## AC-004: Participant Join/Leave Handling

### Scenario 4.1: Participant Join Event

**Given**:
- LiveKit room is active with 0 participants
- ConversationEngine is running
- ParticipantManager is initialized

**When**:
- Participant "user-123" joins room with name="Alice"
- LiveKit emits participant_connected event
- Agent calls participant_manager.add_participant("user-123", name="Alice")

**Then**:
- Participant is added to ParticipantManager
- Participant metadata includes:
  - participant_id="user-123"
  - name="Alice"
  - join_time=current_timestamp
  - is_active=True
  - message_count=0
- get_active_participants() returns list containing Alice
- Participant appears in ConversationContext participant dictionary

**Verification Method**:
```python
async def test_participant_join():
    # Arrange
    context = ConversationContext()
    participant_manager = ParticipantManager(context)

    # Act
    participant_manager.add_participant("user-123", name="Alice")

    # Assert
    active = participant_manager.get_active_participants()
    assert len(active) == 1
    assert active[0].participant_id == "user-123"
    assert active[0].name == "Alice"
    assert active[0].is_active is True
    assert active[0].message_count == 0

    # Verify in context
    participant_meta = context.get_participant("user-123")
    assert participant_meta is not None
    assert participant_meta.name == "Alice"
```

**Success Metrics**:
- ✅ Participant tracked immediately on join
- ✅ Metadata accurately reflects join event
- ✅ Active participant list updated

### Scenario 4.2: Participant Leave Event

**Given**:
- Participant "user-123" (Alice) is active in room
- Alice has sent 5 messages (message_count=5)
- last_activity timestamp is 10 seconds ago

**When**:
- Alice leaves the room
- LiveKit emits participant_disconnected event
- Agent calls participant_manager.remove_participant("user-123")

**Then**:
- Participant is marked inactive (is_active=False)
- leave_time timestamp is set to current time
- join_time remains unchanged
- message_count remains 5 (preserved)
- last_activity remains unchanged
- get_active_participants() no longer includes Alice
- get_participant_stats("user-123") still returns data (historical)

**Verification Method**:
```python
async def test_participant_leave():
    # Arrange
    participant_manager = ParticipantManager(context)
    participant_manager.add_participant("user-123", name="Alice")
    # Simulate 5 messages
    for _ in range(5):
        participant_manager.update_activity("user-123")

    # Act
    participant_manager.remove_participant("user-123")

    # Assert
    active = participant_manager.get_active_participants()
    assert len(active) == 0  # Alice no longer active

    # Historical data preserved
    stats = participant_manager.get_participant_stats("user-123")
    assert stats is not None
    assert stats.is_active is False
    assert stats.leave_time is not None
    assert stats.message_count == 5  # Preserved
```

**Success Metrics**:
- ✅ Participant marked inactive immediately
- ✅ Leave timestamp recorded accurately
- ✅ Historical data preserved
- ✅ Active list updated correctly

### Scenario 4.3: Multi-Participant Tracking

**Given**:
- LiveKit room is active
- ParticipantManager is initialized

**When**:
- Alice joins at T+0s
- Bob joins at T+5s
- Charlie joins at T+10s
- Alice sends 3 messages
- Bob sends 2 messages
- Charlie sends 1 message

**Then**:
- get_active_participants() returns list of 3 participants
- Participants sorted by join_time: [Alice, Bob, Charlie]
- Alice stats: message_count=3, join_time=T+0s
- Bob stats: message_count=2, join_time=T+5s
- Charlie stats: message_count=1, join_time=T+10s
- Each participant's last_activity reflects their last message time

**Verification Method**:
```python
async def test_multi_participant():
    # Arrange
    participant_manager = ParticipantManager(context)

    # Act: Add participants sequentially
    participant_manager.add_participant("user-1", name="Alice")
    await asyncio.sleep(0.1)  # Ensure different timestamps
    participant_manager.add_participant("user-2", name="Bob")
    await asyncio.sleep(0.1)
    participant_manager.add_participant("user-3", name="Charlie")

    # Simulate messages
    for _ in range(3):
        participant_manager.update_activity("user-1")
    for _ in range(2):
        participant_manager.update_activity("user-2")
    participant_manager.update_activity("user-3")

    # Assert
    active = participant_manager.get_active_participants()
    assert len(active) == 3
    assert [p.name for p in active] == ["Alice", "Bob", "Charlie"]

    alice_stats = participant_manager.get_participant_stats("user-1")
    assert alice_stats.message_count == 3
```

**Success Metrics**:
- ✅ Multiple participants tracked independently
- ✅ Join order preserved
- ✅ Per-participant statistics accurate

---

## AC-005: LLM Integration and Response Generation

### Scenario 5.1: OpenAI API Integration

**Given**:
- LLMIntegration initialized with:
  - provider=LLMProvider.OPENAI
  - api_key="sk-test-key"
  - model="gpt-4"
  - temperature=0.7
  - max_tokens=150
- Conversation context contains 3 messages
- Conversation phase is ACTIVE

**When**:
- generate_response(context) is called
- OpenAI API returns successful response:
  - text: "The capital of France is **Paris**, a beautiful city."
  - usage.total_tokens: 85
  - finish_reason: "stop"

**Then**:
- System prompt for ACTIVE phase is included in API call
- All 3 context messages are sent to API in OpenAI format
- Response text is formatted for TTS: "The capital of France is Paris, a beautiful city." (markdown removed)
- LLMResponse object returned with:
  - text="The capital of France is Paris, a beautiful city."
  - tokens_used=85
  - latency_ms=450 (example)
  - model="gpt-4"
  - finish_reason="stop"
- Metrics logged with tokens, latency, model

**Verification Method**:
```python
async def test_openai_integration():
    # Arrange
    llm = LLMIntegration(
        provider=LLMProvider.OPENAI,
        api_key="sk-test-key",
        model="gpt-4",
    )
    context = ConversationContext()
    context.add_message("user", "What is the capital of France?", "user-123")
    context.set_phase(ConversationPhase.ACTIVE)

    # Mock OpenAI response
    mock_response = MockOpenAIResponse(
        text="The capital of France is **Paris**, a beautiful city.",
        total_tokens=85,
        finish_reason="stop",
    )
    with patch("openai.ChatCompletion.acreate", return_value=mock_response):
        # Act
        result = await llm.generate_response(context)

    # Assert
    assert result.text == "The capital of France is Paris, a beautiful city."
    assert result.tokens_used == 85
    assert result.model == "gpt-4"
    assert "**" not in result.text  # Markdown removed
```

**Success Metrics**:
- ✅ OpenAI client initialized successfully
- ✅ API called with correct format
- ✅ Markdown formatting removed
- ✅ Metrics captured accurately

### Scenario 5.2: Anthropic API Integration

**Given**:
- LLMIntegration initialized with:
  - provider=LLMProvider.ANTHROPIC
  - api_key="sk-ant-test-key"
  - model="claude-3-sonnet-20240229"
  - temperature=0.7
  - max_tokens=150
- Conversation context contains 2 messages
- Conversation phase is GREETING

**When**:
- generate_response(context) is called
- Anthropic API returns successful response:
  - text: "Hello! I'm Nora. How can I help you today?"
  - usage.input_tokens: 45
  - usage.output_tokens: 12
  - stop_reason: "end_turn"

**Then**:
- System prompt for GREETING phase is included
- Both context messages sent in Anthropic format
- Response text returned without modification (no markdown)
- LLMResponse object returned with:
  - text="Hello! I'm Nora. How can I help you today?"
  - tokens_used=57 (45 + 12)
  - model="claude-3-sonnet-20240229"
  - finish_reason="end_turn"

**Verification Method**:
```python
async def test_anthropic_integration():
    # Arrange
    llm = LLMIntegration(
        provider=LLMProvider.ANTHROPIC,
        api_key="sk-ant-test-key",
        model="claude-3-sonnet-20240229",
    )
    context = ConversationContext()
    context.add_message("user", "hello", "user-123")
    context.set_phase(ConversationPhase.GREETING)

    # Mock Anthropic response
    mock_response = MockAnthropicResponse(
        text="Hello! I'm Nora. How can I help you today?",
        input_tokens=45,
        output_tokens=12,
        stop_reason="end_turn",
    )
    with patch("anthropic.Anthropic.messages.create", return_value=mock_response):
        # Act
        result = await llm.generate_response(context)

    # Assert
    assert result.text == "Hello! I'm Nora. How can I help you today?"
    assert result.tokens_used == 57
    assert result.model == "claude-3-sonnet-20240229"
```

**Success Metrics**:
- ✅ Anthropic client initialized successfully
- ✅ API called with correct format
- ✅ Token usage calculated correctly
- ✅ Response quality comparable to OpenAI

### Scenario 5.3: TTS Formatting

**Given**:
- LLMIntegration is initialized
- LLM returns response with various markdown elements

**When**:
- LLM response text is: "Here are **three** key points:\n1. First point\n2. Second point\n3. Third point\n\nUse `this code`."

**Then**:
- _format_for_tts() is applied
- Markdown removed:
  - **bold** → bold
  - Numbered lists → plain text with commas
  - `code` → code
- Final text: "Here are three key points: First point, Second point, Third point. Use this code."
- Text is suitable for TTS without pronunciation issues

**Verification Method**:
```python
def test_tts_formatting():
    # Arrange
    llm = LLMIntegration(...)
    markdown_text = "Here are **three** key points:\n1. First point\n2. Second point\n3. Third point\n\nUse `this code`."

    # Act
    formatted = llm._format_for_tts(markdown_text)

    # Assert
    assert "**" not in formatted
    assert "`" not in formatted
    assert "1." not in formatted  # List markers removed
    # Should be natural speech text
    assert "three key points" in formatted.lower()
```

**Success Metrics**:
- ✅ All markdown syntax removed
- ✅ Text flows naturally for speech
- ✅ No pronunciation artifacts
- ✅ Cartesia TTS handles formatted text cleanly

---

## AC-006: Error Handling and Fallbacks

### Scenario 6.1: LLM API Rate Limit Retry

**Given**:
- LLMIntegration initialized with OpenAI provider
- Retry logic configured: max_attempts=3, backoff=[1s, 2s, 4s]

**When**:
- generate_response() is called
- OpenAI API returns 429 (rate limit) error on attempt 1
- Returns 429 on attempt 2
- Returns successful response on attempt 3

**Then**:
- Attempt 1 fails, wait 1 second, retry
- Attempt 2 fails, wait 2 seconds, retry
- Attempt 3 succeeds, return response
- Total retries: 2
- Total delay: 3 seconds (1s + 2s)
- Success logged with retry_count=2
- User receives response without knowing about retries

**Verification Method**:
```python
async def test_retry_logic():
    # Arrange
    llm = LLMIntegration(provider=LLMProvider.OPENAI, ...)
    context = ConversationContext()

    # Mock: Fail twice, succeed third time
    call_count = 0
    async def mock_api_call(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count <= 2:
            raise RateLimitError("429: Too many requests")
        return MockSuccessResponse()

    with patch("openai.ChatCompletion.acreate", side_effect=mock_api_call):
        # Act
        start_time = time.time()
        result = await llm.generate_response(context)
        elapsed = time.time() - start_time

    # Assert
    assert call_count == 3  # 1 initial + 2 retries
    assert elapsed >= 3.0  # 1s + 2s delays
    assert result.text is not None  # Success
```

**Success Metrics**:
- ✅ Retries with correct delays (1s, 2s, 4s)
- ✅ Successful recovery >99% of time
- ✅ User experience unaffected by transient errors

### Scenario 6.2: Permanent LLM API Failure

**Given**:
- LLMIntegration initialized with fallback_response="I'm having trouble right now. Please try again."
- Retry logic configured: max_attempts=3

**When**:
- generate_response() is called
- All 3 API attempts fail with 500 (server error)
- No successful response after retries

**Then**:
- Attempt 1 fails, wait 1s, retry
- Attempt 2 fails, wait 2s, retry
- Attempt 3 fails, retry exhausted
- fallback_response is returned: "I'm having trouble right now. Please try again."
- Error logged with severity=ERROR, retry_count=3
- User receives fallback response (not crash)

**Verification Method**:
```python
async def test_permanent_failure():
    # Arrange
    llm = LLMIntegration(
        provider=LLMProvider.OPENAI,
        fallback_response="I'm having trouble right now.",
    )
    context = ConversationContext()

    # Mock: All attempts fail
    with patch("openai.ChatCompletion.acreate", side_effect=ServerError("500")):
        # Act
        result = await llm.generate_response(context)

    # Assert
    assert result.text == "I'm having trouble right now."
    # Verify error was logged
    assert "LLM API failure" in captured_logs
    assert "retry_count=3" in captured_logs
```

**Success Metrics**:
- ✅ Fallback response returned
- ✅ No crash or exception propagated
- ✅ Error logged for monitoring
- ✅ User receives graceful degradation

### Scenario 6.3: Turn Detection Error Recovery

**Given**:
- TurnManager is running and processing audio
- Audio stream is active

**When**:
- Audio processing encounters codec error
- VAD plugin raises AudioProcessingError

**Then**:
- Error is caught by TurnManager
- Error logged with context: "Turn detection error: AudioProcessingError"
- TurnManager continues monitoring (does not crash)
- Next valid audio chunk is processed normally
- Conversation continues without user-facing failure

**Verification Method**:
```python
async def test_turn_detection_recovery():
    # Arrange
    turn_manager = TurnManager(...)
    audio_stream = create_faulty_audio_stream(
        error_at_chunk=5,  # Inject error at 5th chunk
    )

    # Act
    await turn_manager.start(audio_stream)
    # Wait for error to occur and recovery
    await asyncio.sleep(1.0)

    # Assert: Turn manager still running
    assert turn_manager._running is True
    # Verify error was logged
    assert "Turn detection error" in captured_logs
```

**Success Metrics**:
- ✅ Error caught and logged
- ✅ Turn detection continues
- ✅ No crash or conversation termination
- ✅ Resilient to transient audio issues

---

## AC-007: Conversation State Transitions

### Scenario 7.1: GREETING to ACTIVE Transition

**Given**:
- Conversation starts in GREETING phase
- Context contains 0 messages
- User sends first message: "hello"

**When**:
- First user message processed → Context has 2 messages (user + assistant)
- User sends second message: "What can you do?"
- Second user message processed → Context has 4 messages

**Then**:
- After first message: Phase remains GREETING
- After second message: Phase transitions to ACTIVE
- Subsequent LLM calls use ACTIVE system prompt
- System prompt changes from "The conversation is just starting..." to "Provide clear, concise answers..."
- Transition logged: "Conversation phase: GREETING → ACTIVE"

**Verification Method**:
```python
async def test_greeting_to_active():
    # Arrange
    engine = ConversationEngine(...)
    await engine.start()

    # Act: First message
    await engine.process_transcription("hello", "user-123")
    phase_after_first = engine.context._phase

    # Act: Second message triggers transition
    await engine.process_transcription("What can you do?", "user-123")
    phase_after_second = engine.context._phase

    # Assert
    assert phase_after_first == ConversationPhase.GREETING
    assert phase_after_second == ConversationPhase.ACTIVE
    assert "GREETING → ACTIVE" in captured_logs
```

**Success Metrics**:
- ✅ Transition occurs after 2nd user message
- ✅ System prompt updated correctly
- ✅ Transition logged
- ✅ Subsequent responses use ACTIVE behavior

### Scenario 7.2: ACTIVE to CLOSING Transition (Idle Timeout)

**Given**:
- Conversation is in ACTIVE phase
- Last message was 125 seconds ago
- idle_timeout_seconds=120 (2 minutes)

**When**:
- Idle timeout check runs
- Current time - last_activity > 120 seconds

**Then**:
- Conversation transitions to CLOSING phase
- Closing message generated: "It was nice talking to you. Have a great day!" (example)
- Transition logged: "Conversation phase: ACTIVE → CLOSING (idle timeout)"
- No new messages accepted after closing (optional behavior)

**Verification Method**:
```python
async def test_idle_timeout():
    # Arrange
    config = ConversationConfig(idle_timeout_seconds=5)  # 5s for testing
    engine = ConversationEngine(config, ...)
    await engine.start()
    await engine.process_transcription("hello", "user-123")
    await engine.process_transcription("how are you?", "user-123")
    # Now in ACTIVE phase

    # Act: Wait for timeout
    await asyncio.sleep(6)  # Exceed 5s timeout

    # Assert
    assert engine.context._phase == ConversationPhase.CLOSING
    assert "ACTIVE → CLOSING" in captured_logs
    assert "idle timeout" in captured_logs
```

**Success Metrics**:
- ✅ Timeout triggers CLOSING transition
- ✅ Closing message generated
- ✅ Idle time calculated accurately
- ✅ Transition logged with reason

### Scenario 7.3: Invalid Phase Transition Prevention

**Given**:
- Conversation is in ACTIVE phase
- ConversationPhase enum defines: GREETING → ACTIVE → CLOSING

**When**:
- Code attempts to transition ACTIVE → GREETING (invalid)

**Then**:
- set_phase(ConversationPhase.GREETING) raises ValueError
- Error message: "Invalid phase transition: ACTIVE → GREETING"
- Phase remains ACTIVE (unchanged)
- Error logged

**Verification Method**:
```python
def test_invalid_transition():
    # Arrange
    context = ConversationContext()
    context.set_phase(ConversationPhase.ACTIVE)

    # Act & Assert
    with pytest.raises(ValueError, match="Invalid phase transition"):
        context.set_phase(ConversationPhase.GREETING)

    # Verify phase unchanged
    assert context._phase == ConversationPhase.ACTIVE
```

**Success Metrics**:
- ✅ Invalid transitions rejected
- ✅ Clear error message
- ✅ State consistency maintained
- ✅ Error logged

---

## AC-008: Context Retention Across Turns

**Covered in AC-002 Scenario 2.2**

---

## AC-009: Performance Requirements

### Scenario 9.1: LLM Response Latency Benchmark

**Given**:
- 100 sample conversations with varying context sizes (1-20 messages)
- Each conversation represents typical user questions
- LLMIntegration configured with gpt-3.5-turbo (fast model)

**When**:
- process_transcription() is called for each sample
- Latency measured from call to return

**Then**:
- 50th percentile (median) latency: <500ms
- 95th percentile latency: <1000ms
- 99th percentile latency: <1500ms
- No outliers >3000ms

**Verification Method**:
```python
@pytest.mark.benchmark
async def test_llm_latency_benchmark():
    # Arrange
    samples = generate_sample_conversations(count=100)
    latencies = []

    # Act
    for sample in samples:
        start = time.time()
        await engine.process_transcription(sample.text, sample.participant_id)
        latency = (time.time() - start) * 1000  # ms
        latencies.append(latency)

    # Assert
    p50 = numpy.percentile(latencies, 50)
    p95 = numpy.percentile(latencies, 95)
    p99 = numpy.percentile(latencies, 99)

    assert p50 < 500
    assert p95 < 1000
    assert p99 < 1500
```

**Success Metrics**:
- ✅ P95 latency <1000ms
- ✅ Consistent performance across context sizes
- ✅ No degradation over time

### Scenario 9.2: Context Operation Performance

**Given**:
- ConversationContext with 20 messages (at max_history)
- Operations tested: add_message(), get_history(), format_for_llm()

**When**:
- Each operation executed 1000 times
- Execution time measured per operation

**Then**:
- add_message(): Mean <10ms, P95 <15ms
- get_history(): Mean <5ms, P95 <8ms
- format_for_llm(): Mean <5ms, P95 <8ms
- No blocking operations (all synchronous, fast)

**Verification Method**:
```python
@pytest.mark.benchmark
def test_context_operations():
    # Arrange
    context = ConversationContext(max_history=20)
    # Pre-fill to max
    for i in range(20):
        context.add_message("user", f"Message {i}", "user-123")

    # Benchmark add_message
    add_times = []
    for i in range(1000):
        start = time.perf_counter()
        context.add_message("user", f"New message {i}", "user-123")
        add_times.append((time.perf_counter() - start) * 1000)

    # Benchmark get_history
    get_times = []
    for _ in range(1000):
        start = time.perf_counter()
        _ = context.get_history()
        get_times.append((time.perf_counter() - start) * 1000)

    # Benchmark format_for_llm
    format_times = []
    for _ in range(1000):
        start = time.perf_counter()
        _ = context.format_for_llm()
        format_times.append((time.perf_counter() - start) * 1000)

    # Assert
    assert numpy.mean(add_times) < 10
    assert numpy.percentile(add_times, 95) < 15
    assert numpy.mean(get_times) < 5
    assert numpy.percentile(get_times, 95) < 8
    assert numpy.mean(format_times) < 5
    assert numpy.percentile(format_times, 95) < 8
```

**Success Metrics**:
- ✅ All operations <10ms mean
- ✅ P95 within targets
- ✅ No performance degradation at max_history

### Scenario 9.3: Memory Usage Benchmark

**Given**:
- Conversation runs for 1 hour
- 100 messages exchanged (20 retained at any time due to max_history)
- Memory profiled every 5 minutes

**When**:
- Conversation processes 100 turns over 60 minutes

**Then**:
- Initial memory: ~10MB (baseline)
- Memory at 30 minutes: <50MB
- Memory at 60 minutes: <55MB
- Memory growth: <10% over 1 hour
- No memory leaks detected

**Verification Method**:
```python
@pytest.mark.benchmark
@pytest.mark.slow
async def test_memory_usage():
    # Arrange
    engine = ConversationEngine(...)
    memory_samples = []

    # Act: Simulate 1-hour conversation
    for i in range(100):
        await engine.process_transcription(f"Message {i}", "user-123")
        if i % 20 == 0:  # Sample every 20 messages
            mem_usage = get_memory_usage_mb()
            memory_samples.append(mem_usage)
        await asyncio.sleep(0.5)  # Simulate time between messages

    # Assert
    initial_memory = memory_samples[0]
    final_memory = memory_samples[-1]
    growth_percent = ((final_memory - initial_memory) / initial_memory) * 100

    assert final_memory < 55  # <55MB
    assert growth_percent < 10  # <10% growth
```

**Success Metrics**:
- ✅ Memory usage <50MB
- ✅ Growth <10% over time
- ✅ No memory leaks
- ✅ Stable memory profile

---

## AC-010: Multi-Participant Scenarios

**Covered in AC-004 Scenario 4.3**

---

## Edge Case Scenarios

### EC-001: Empty User Input

**Given**:
- ConversationEngine is running

**When**:
- User sends empty message: ""
- process_transcription("", "user-123") is called

**Then**:
- Empty message is rejected
- No message added to context
- Returns fallback response: "I didn't hear you. Could you please repeat?"
- Error logged: "Empty user input received"

### EC-002: Very Long User Input

**Given**:
- ConversationEngine is running
- User sends 500-word message (exceeds typical limits)

**When**:
- process_transcription(very_long_text, "user-123") is called

**Then**:
- Message is truncated to max_input_length (e.g., 1000 characters)
- Warning logged: "User input truncated from 3000 to 1000 characters"
- Truncated message processed normally
- Response indicates input was long: "That's a lot of information. Let me focus on..."

### EC-003: Rapid Message Burst

**Given**:
- User sends 5 messages within 2 seconds

**When**:
- process_transcription() called 5 times rapidly

**Then**:
- All 5 messages processed sequentially (queue)
- No messages dropped
- Responses generated in order
- Last message processed within 5 seconds total

### EC-004: Unicode and Special Characters

**Given**:
- User sends message with emoji, accents, Chinese characters: "Hello! 你好 🎉"

**When**:
- process_transcription("Hello! 你好 🎉", "user-123") is called

**Then**:
- Message stored correctly in context (UTF-8)
- LLM receives message with proper encoding
- Response generated successfully
- TTS handles special characters appropriately

---

## Performance Benchmarks Summary

| Metric                          | Target         | Verification Method           | Priority |
|---------------------------------|----------------|-------------------------------|----------|
| LLM Response Latency (P95)      | <1000ms        | pytest-benchmark              | P0       |
| Context add_message() (Mean)    | <10ms          | pytest-benchmark              | P0       |
| Context get_history() (Mean)    | <5ms           | pytest-benchmark              | P0       |
| Context format_for_llm() (Mean) | <5ms           | pytest-benchmark              | P0       |
| Turn Detection Latency          | <100ms         | Synthetic audio tests         | P1       |
| Memory Usage (20 messages)      | <50MB          | Memory profiling              | P1       |
| Memory Growth (1 hour)          | <10%           | Extended session tests        | P2       |
| Turn Detection Accuracy         | >95%           | Synthetic audio ground truth  | P1       |

---

## Test Coverage Requirements

### Unit Tests (Target: 90%+ coverage)

- **ConversationContext**: 15 tests
- **LLMIntegration**: 20 tests (10 OpenAI, 10 Anthropic)
- **TurnManager**: 12 tests
- **ConversationEngine**: 18 tests
- **ParticipantManager**: 10 tests

**Total Unit Tests**: 75 tests

### Integration Tests (Target: 100% pass rate)

- **End-to-End Greeting Flow**: 3 tests
- **Multi-Turn Contextual Conversation**: 4 tests
- **Interruption Handling**: 3 tests
- **Conversation Lifecycle**: 4 tests
- **Multi-Participant Support**: 3 tests

**Total Integration Tests**: 17 tests

### Performance Tests (Target: All benchmarks within targets)

- **LLM Latency Benchmark**: 1 test (100 samples)
- **Context Operations Benchmark**: 3 tests (1000 iterations each)
- **Turn Detection Latency**: 1 test (100 samples)
- **Memory Usage Profiling**: 1 test (1-hour simulation)

**Total Performance Tests**: 6 tests

---

## Validation Checklist

**Before marking SPEC-LIVEKIT-003 as COMPLETE, verify**:

- ✅ All 10 acceptance criteria scenarios pass
- ✅ All 4 edge case scenarios pass
- ✅ Unit test coverage ≥90% for all conversation modules
- ✅ All 17 integration tests pass consistently (10 consecutive runs)
- ✅ All 6 performance benchmarks meet targets
- ✅ Mypy type checking: 0 errors
- ✅ Ruff linting: 0 errors
- ✅ No memory leaks detected in 1-hour test
- ✅ VoicePipeline integration tested end-to-end
- ✅ Documentation complete (CONVERSATION_ENGINE.md, CONVERSATION_API.md)

---

**END OF ACCEPTANCE CRITERIA**
