# SPEC-AGENT-001: Acceptance Criteria

**TAG**: `<ACCEPTANCE-AGENT-001>`

---

## OVERVIEW

This document defines the acceptance criteria for SPEC-AGENT-001 using Given/When/Then scenarios in 3-column format. All scenarios must pass with 90% test coverage using mocked LLM providers.

**Testing Approach**: Mocked providers only (fast, deterministic, no API costs)

**Success Criteria**: All core scenarios pass + edge cases handled gracefully

---

## CORE ACCEPTANCE SCENARIOS

### Scenario 1: Provider Fallback on Primary Failure

**Description**: When the primary LLM provider (OpenAI) is unavailable, the system automatically falls back to the next provider (Anthropic) and responds within the 5-second performance constraint.

| Given | When | Then |
|-------|------|------|
| Primary LLM provider (OpenAI) is unavailable due to network timeout | User sends message "Hello, I need to schedule an appointment" to Greeter agent | System detects OpenAI failure, falls back to Anthropic provider, and responds within 5 seconds with greeting message |

**Test Implementation**:
```python
async def test_provider_fallback_on_primary_failure():
    # Given: OpenAI provider configured to fail
    mock_openai = MockLLMClient(responses=[], failure_mode="timeout")
    mock_anthropic = MockLLMClient(responses=["Hello! I'm here to help..."])
    factory = LLMClientFactory(clients=[mock_openai, mock_anthropic])

    # When: User sends message
    start_time = time.time()
    response = await factory.generate("Hello, I need to schedule an appointment", [])
    elapsed = time.time() - start_time

    # Then: Anthropic responds within 5 seconds
    assert response == "Hello! I'm here to help..."
    assert elapsed < 5.0
    assert mock_anthropic.call_count == 1
```

**Tags Covered**: `<FR2-fallback>`, `<NFR1-fallback-perf>`

---

### Scenario 2: Agent Transfer with Context Preservation

**Description**: When the Greeter agent determines a transfer is needed, it passes the full conversation history to the Triage agent, ensuring no information is lost.

| Given | When | Then |
|-------|------|------|
| Greeter agent has 3-message conversation history with user about chest pain | Greeter agent detects "urgent" keyword and initiates transfer to Triage agent | Triage agent receives full conversation context (all 3 messages) and responds with urgency assessment |

**Test Implementation**:
```python
async def test_agent_transfer_with_context_preservation():
    # Given: Greeter has conversation history
    greeter = GreeterAgent(llm_client=mock_llm)
    context = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi! How can I help?"},
        {"role": "user", "content": "I have urgent chest pain"}
    ]

    # When: Transfer is initiated
    should_transfer, target_agent = await greeter.should_transfer(context)
    assert should_transfer is True
    assert target_agent == "triage"

    transferred_context = await greeter.prepare_transfer_context(context)
    triage = TriageAgent(llm_client=mock_llm)

    # Then: Triage receives full context
    response = await triage.on_message("", transferred_context)
    assert len(transferred_context) == 3
    assert "urgent" in transferred_context[-1]["content"]
    assert "chest pain" in response.lower()
```

**Tags Covered**: `<FR3-transfer-context>`, `<NFR2-context-integrity>`, `<IR4-transfer-api>`

---

### Scenario 3: Complete Medical Triage Workflow

**Description**: A user contacts the voice agent system with a medical concern and experiences the full medical triage workflow: Greeter welcomes, Triage assesses urgency, and Support handles the specific request with all context preserved across transfers.

| Given | When | Then |
|-------|------|------|
| User initiates voice call to medical office agent system | User describes "I need to refill my blood pressure medication" | 1. Greeter welcomes user<br>2. Greeter transfers to Triage with context<br>3. Triage assesses as non-urgent prescription refill<br>4. Triage transfers to Support with full context<br>5. Support provides prescription refill instructions |

**Test Implementation**:
```python
async def test_complete_medical_triage_workflow():
    # Given: User initiates contact
    mock_llm = MockLLMClient(responses=[
        "Hello! Welcome to our medical office. How can I help today?",  # Greeter
        "I understand you need a prescription refill. Let me assess...",  # Triage
        "I'll help you refill your blood pressure medication..."  # Support
    ])

    greeter = GreeterAgent(llm_client=mock_llm)
    triage = TriageAgent(llm_client=mock_llm)
    support = SupportAgent(llm_client=mock_llm)

    # When: User describes medication refill need
    context = []

    # Step 1: Greeter welcomes
    greeting = await greeter.on_message("Hello", context)
    assert "welcome" in greeting.lower()
    context.append({"role": "assistant", "content": greeting})

    # Step 2: User states need
    user_message = "I need to refill my blood pressure medication"
    context.append({"role": "user", "content": user_message})

    # Step 3: Greeter transfers to Triage
    should_transfer, target = await greeter.should_transfer(context)
    assert should_transfer is True
    assert target == "triage"

    transfer_context = await greeter.prepare_transfer_context(context)

    # Step 4: Triage assesses
    triage_response = await triage.on_message(user_message, transfer_context)
    assert "prescription" in triage_response.lower()
    transfer_context.append({"role": "assistant", "content": triage_response})

    # Step 5: Triage transfers to Support
    should_transfer, target = await triage.should_transfer(transfer_context)
    assert should_transfer is True
    assert target == "support"

    support_context = await triage.prepare_transfer_context(transfer_context)

    # Step 6: Support handles request
    support_response = await support.on_message("", support_context)
    assert "blood pressure" in support_response.lower()

    # Then: Full context preserved across all transfers
    assert len(support_context) >= 3  # At least greeting, user request, triage assessment
    assert any("blood pressure" in msg["content"].lower() for msg in support_context)
```

**Tags Covered**: `<FR6-medical-triage>`, `<FR3-transfer-context>`, `<NFR2-context-integrity>`

---

## EDGE CASE SCENARIOS

### Edge Case 1: All Providers Fail (Fallback Exhaustion)

| Given | When | Then |
|-------|------|------|
| All 4 LLM providers (OpenAI, Anthropic, Google, Ollama) are unavailable | User sends message to agent | System logs error, returns graceful degradation message "Our system is temporarily unavailable. Please try again in a few minutes." |

**Test Implementation**:
```python
async def test_all_providers_fail():
    # Given: All providers fail
    failing_clients = [
        MockLLMClient(responses=[], failure_mode="timeout"),
        MockLLMClient(responses=[], failure_mode="api_error"),
        MockLLMClient(responses=[], failure_mode="rate_limit"),
        MockLLMClient(responses=[], failure_mode="timeout")
    ]
    factory = LLMClientFactory(clients=failing_clients)

    # When: User sends message
    with pytest.raises(AllProvidersFailedError) as exc_info:
        await factory.generate("Hello", [])

    # Then: Graceful error message
    assert "temporarily unavailable" in str(exc_info.value).lower()
    assert all(client.call_count > 0 for client in failing_clients)  # All tried
```

**Tags Covered**: `<FR2-fallback>`

---

### Edge Case 2: Context Exceeds Token Limit

| Given | When | Then |
|-------|------|------|
| Conversation history contains 50+ messages approaching provider token limit | Agent attempts to send context to LLM provider | System truncates oldest messages (keeping most recent 30) and logs warning "Context truncated due to size limits" |

**Test Implementation**:
```python
async def test_context_exceeds_token_limit():
    # Given: Large conversation history
    large_context = [
        {"role": "user" if i % 2 == 0 else "assistant", "content": f"Message {i}"}
        for i in range(60)
    ]

    agent = GreeterAgent(llm_client=mock_llm, max_context_messages=30)

    # When: Agent prepares context
    truncated_context = await agent.prepare_context(large_context)

    # Then: Context truncated to 30 messages
    assert len(truncated_context) == 30
    assert truncated_context[0]["content"] == "Message 30"  # Oldest kept
    assert truncated_context[-1]["content"] == "Message 59"  # Most recent kept
```

**Tags Covered**: `<NFR2-context-integrity>`

---

### Edge Case 3: Concurrent Agent Transfers

| Given | When | Then |
|-------|------|------|
| Two users simultaneously trigger agent transfers (User A: Greeter→Triage, User B: Triage→Support) | Both transfers execute concurrently | Each transfer preserves correct context without cross-contamination, both complete within 5 seconds |

**Test Implementation**:
```python
async def test_concurrent_agent_transfers():
    # Given: Two users with separate contexts
    context_a = [{"role": "user", "content": "User A: urgent issue"}]
    context_b = [{"role": "user", "content": "User B: billing question"}]

    greeter = GreeterAgent(llm_client=mock_llm)
    triage = TriageAgent(llm_client=mock_llm)

    # When: Concurrent transfers
    start_time = time.time()
    transfer_a, transfer_b = await asyncio.gather(
        greeter.transfer_to("triage", context_a),
        triage.transfer_to("support", context_b)
    )
    elapsed = time.time() - start_time

    # Then: No cross-contamination, both complete fast
    assert "User A" in str(transfer_a.context)
    assert "User A" not in str(transfer_b.context)
    assert "User B" in str(transfer_b.context)
    assert "User B" not in str(transfer_a.context)
    assert elapsed < 5.0
```

**Tags Covered**: `<FR3-transfer-context>`, `<NFR5-async>`

---

### Edge Case 4: Invalid YAML Configuration

| Given | When | Then |
|-------|------|------|
| Configuration file `config/prompts.yaml` contains invalid syntax (missing colon) | System attempts to load configuration at startup | System raises `ConfigValidationError` with clear message "Invalid YAML syntax in prompts.yaml: line 15" and exits gracefully |

**Test Implementation**:
```python
def test_invalid_yaml_configuration(tmp_path):
    # Given: Invalid YAML file
    invalid_yaml = tmp_path / "prompts.yaml"
    invalid_yaml.write_text("""
    agents:
      greeter
        system_prompt: "Hello"  # Missing colon after 'greeter'
    """)

    # When: Loading configuration
    with pytest.raises(ConfigValidationError) as exc_info:
        config = Config.load_from_file(invalid_yaml)

    # Then: Clear error message
    assert "invalid yaml syntax" in str(exc_info.value).lower()
    assert "prompts.yaml" in str(exc_info.value)
```

**Tags Covered**: `<FR4-yaml-config>`

---

### Edge Case 5: Provider Health Check Failure

| Given | When | Then |
|-------|------|------|
| OpenAI provider passes initial health check but fails during conversation | Agent sends message mid-conversation | System falls back to next provider without losing conversation context, logs health check failure |

**Test Implementation**:
```python
async def test_provider_fails_mid_conversation():
    # Given: Provider healthy initially, then fails
    mock_openai = MockLLMClient(
        responses=["First response"],
        failure_mode=None
    )
    mock_openai.fail_after_calls = 1  # Fail on second call

    mock_anthropic = MockLLMClient(responses=["Fallback response"])
    factory = LLMClientFactory(clients=[mock_openai, mock_anthropic])

    context = []

    # When: First message succeeds
    response1 = await factory.generate("Hello", context)
    assert response1 == "First response"
    context.append({"role": "assistant", "content": response1})

    # When: Second message triggers failure and fallback
    response2 = await factory.generate("How are you?", context)

    # Then: Fallback succeeds with context preserved
    assert response2 == "Fallback response"
    assert len(context) == 1  # Context preserved
    assert mock_anthropic.last_context == context  # Context passed to fallback
```

**Tags Covered**: `<FR2-fallback>`, `<NFR2-context-integrity>`

---

## PERFORMANCE BENCHMARKS

### Benchmark 1: Fallback Latency

**Requirement**: Fallback must complete within 5 seconds (NFR1)

| Scenario | Max Allowed | Target | Measurement Method |
|----------|-------------|--------|-------------------|
| Single provider failure | 5.0s | 2.0s | `time.time()` difference |
| Two providers fail | 5.0s | 3.0s | `time.time()` difference |
| Three providers fail | 5.0s | 4.5s | `time.time()` difference |

**Test Implementation**:
```python
@pytest.mark.parametrize("num_failures", [1, 2, 3])
async def test_fallback_latency_benchmark(num_failures):
    clients = []
    for i in range(num_failures):
        clients.append(MockLLMClient(responses=[], failure_mode="timeout"))
    clients.append(MockLLMClient(responses=["Success"]))

    factory = LLMClientFactory(clients=clients)

    start_time = time.time()
    response = await factory.generate("Test", [])
    elapsed = time.time() - start_time

    assert elapsed < 5.0  # Hard requirement
    assert response == "Success"
```

---

### Benchmark 2: Context Serialization Overhead

**Requirement**: Context transfer adds <100ms overhead

| Context Size | Max Overhead | Target | Measurement Method |
|--------------|--------------|--------|-------------------|
| 10 messages | 100ms | 20ms | Transfer time vs. baseline |
| 30 messages | 100ms | 50ms | Transfer time vs. baseline |
| 50 messages | 100ms | 80ms | Transfer time vs. baseline |

**Test Implementation**:
```python
@pytest.mark.parametrize("context_size", [10, 30, 50])
async def test_context_serialization_overhead(context_size):
    context = [
        {"role": "user" if i % 2 == 0 else "assistant", "content": f"Message {i}"}
        for i in range(context_size)
    ]

    agent = GreeterAgent(llm_client=mock_llm)

    # Measure serialization time
    start_time = time.time()
    transferred_context = await agent.prepare_transfer_context(context)
    overhead = (time.time() - start_time) * 1000  # Convert to ms

    assert overhead < 100  # Hard requirement
    assert len(transferred_context) == context_size
```

---

## SUCCESS CRITERIA SUMMARY

### Functional Success Criteria

- ✅ All 4 LLM providers (OpenAI, Anthropic, Google, Ollama) have working adapters
- ✅ Automatic fallback chain operational (primary fail → secondary → tertiary → local)
- ✅ Agent transfer preserves 100% of conversation context
- ✅ YAML configuration loads and validates correctly
- ✅ Console mode and room mode both operational
- ✅ Medical triage pattern (Greeter → Triage → Support) functional

### Non-Functional Success Criteria

- ✅ Test coverage ≥90% across all modules
- ✅ All tests use mocked providers (zero API calls)
- ✅ Fallback completion within 5 seconds
- ✅ Context serialization overhead <100ms
- ✅ Structured logging for all failures and transfers
- ✅ Async/await patterns throughout codebase

### Quality Gate Criteria (TRUST 5)

1. **Test-first**: All features developed with TDD (RED-GREEN-REFACTOR)
2. **Readable**: Maximum 5 modules per layer, clear naming conventions
3. **Unified**: Consistent patterns (Adapter, Factory, Strategy)
4. **Secured**: API key management, input validation, error boundaries
5. **Trackable**: Full test coverage with deterministic results

---

## VALIDATION CHECKLIST

Before marking SPEC-AGENT-001 as complete, verify:

- [ ] All 3 core scenarios pass with mocked providers
- [ ] All 5 edge cases handled gracefully
- [ ] Performance benchmarks meet requirements (<5s fallback, <100ms context)
- [ ] Test coverage ≥90% (measured with `pytest-cov`)
- [ ] Console mode operational (manual testing)
- [ ] Room mode operational with LiveKit server (manual testing)
- [ ] YAML configuration validated with Pydantic
- [ ] All TRUST 5 criteria satisfied
- [ ] Code review complete (naming, patterns, documentation)
- [ ] Ready for `/moai:3-sync` documentation generation

---

## NEXT STEPS

After all acceptance criteria pass:

1. Execute `/clear` to reset token context
2. Run `/moai:3-sync SPEC-AGENT-001` to generate documentation
3. Verify documentation accuracy and completeness
4. Commit changes with message: "feat(agent): implement multi-provider LLM agent system with medical triage"
5. Consider production deployment (Docker container, environment variables, LiveKit server connection)

---

**END OF ACCEPTANCE CRITERIA**
