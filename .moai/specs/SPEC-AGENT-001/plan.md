# SPEC-AGENT-001: Implementation Plan

**TAG**: `<PLAN-AGENT-001>`

---

## OVERVIEW

This implementation plan details the development of a multi-provider LLM agent system with medical triage pattern, automatic fallback, and context-preserving agent transfers. The system follows TDD methodology with 90% coverage target using mocked providers.

**Approach**: Incremental development across 5 phases, following RED-GREEN-REFACTOR cycle for each module.

---

## MODULE BREAKDOWN

### Module 1: Model Abstraction Layer (`src/models/`)

**Purpose**: Provide unified interface for multiple LLM providers with fallback support

**Components**:
- `base_client.py`: `BaseLLMClient` abstract base class
- `openai_client.py`: OpenAI API adapter
- `anthropic_client.py`: Anthropic API adapter
- `google_client.py`: Google Gemini API adapter
- `ollama_client.py`: Ollama local LLM adapter
- `factory.py`: `LLMClientFactory` with fallback chain logic

**Key Interfaces**:
```python
class BaseLLMClient(ABC):
    @abstractmethod
    async def generate(self, prompt: str, context: list[dict]) -> str:
        """Generate single response"""
        pass

    @abstractmethod
    async def stream(self, prompt: str, context: list[dict]) -> AsyncIterator[str]:
        """Stream response tokens"""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Verify provider availability"""
        pass
```

**Testing Focus**:
- Mock API responses for all providers
- Validate error handling and retries
- Test fallback chain execution

---

### Module 2: Agent System (`src/agents/`)

**Purpose**: Implement specialized medical triage agents with LiveKit integration

**Components**:
- `base_agent.py`: `BaseAgent` abstract class with LiveKit VoiceAssistant integration
- `greeter_agent.py`: `GreeterAgent` (welcomes, identifies needs)
- `triage_agent.py`: `TriageAgent` (assesses urgency, routes)
- `support_agent.py`: `SupportAgent` (handles tasks)
- `transfer_handler.py`: `TransferHandler` for context preservation

**Key Interfaces**:
```python
class BaseAgent(ABC):
    @abstractmethod
    async def on_message(self, message: str, context: dict) -> str:
        """Process incoming message"""
        pass

    @abstractmethod
    async def should_transfer(self, context: dict) -> tuple[bool, str | None]:
        """Determine if transfer is needed"""
        pass

    async def transfer_to(self, agent_name: str, context: dict) -> None:
        """Transfer conversation to another agent"""
        pass
```

**Testing Focus**:
- Mock LiveKit VoiceAssistant interactions
- Validate agent-specific response logic
- Test transfer decision-making

---

### Module 3: Configuration Management (`config/` & `src/config.py`)

**Purpose**: Centralized YAML-based configuration with validation

**Components**:
- `config/prompts.yaml`: Agent system prompts and instructions
- `config/providers.yaml`: Provider settings and fallback order
- `src/config.py`: Pydantic models for configuration validation

**Configuration Structure**:
```yaml
# prompts.yaml
agents:
  greeter:
    system_prompt: "You are a friendly medical office greeter..."
    transfer_keywords: ["urgent", "emergency", "appointment"]

  triage:
    system_prompt: "You assess patient needs..."
    transfer_keywords: ["schedule", "billing", "prescription"]

# providers.yaml
fallback_chain:
  - openai
  - anthropic
  - google
  - ollama

providers:
  openai:
    model: "gpt-4-turbo"
    timeout: 30
  anthropic:
    model: "claude-3-5-sonnet-20241022"
    timeout: 30
```

**Testing Focus**:
- Validate Pydantic schema enforcement
- Test invalid configuration rejection
- Verify YAML parsing error handling

---

### Module 4: Testing Framework (`tests/`)

**Purpose**: Achieve 90% coverage with mocked providers and deterministic tests

**Components**:
- `tests/mocks/mock_llm_client.py`: Deterministic LLM mock
- `tests/mocks/mock_livekit.py`: LiveKit VoiceAssistant mock
- `tests/test_models/`: Provider adapter tests
- `tests/test_agents/`: Agent behavior tests
- `tests/test_integration/`: End-to-end workflow tests
- `tests/test_performance.py`: Fallback timing validation

**Mock Strategy**:
```python
class MockLLMClient(BaseLLMClient):
    def __init__(self, responses: list[str], failure_mode: str | None = None):
        self.responses = responses
        self.failure_mode = failure_mode  # "timeout", "api_error", None

    async def generate(self, prompt: str, context: list[dict]) -> str:
        if self.failure_mode:
            raise self._simulate_error()
        return self.responses.pop(0)
```

**Testing Focus**:
- Fast, deterministic test execution
- No real API calls in CI pipeline
- Coverage of all error paths and edge cases

---

### Module 5: Entry Point (`src/main.py`)

**Purpose**: Bootstrap application in console or room mode

**Components**:
- `main.py`: CLI argument parsing and mode selection
- `console_runner.py`: Console interaction loop
- `room_runner.py`: LiveKit room connection and management

**CLI Interface**:
```bash
# Console mode (development/testing)
python src/main.py console --agent greeter

# Room mode (production)
python src/main.py room --url ws://localhost:7880 --token <TOKEN>
```

**Testing Focus**:
- Mock console input/output
- Mock LiveKit connection
- Validate mode selection logic

---

## IMPLEMENTATION PHASES

### Phase 1: Model Abstraction & Fallback (Weeks 1-2)

**Goal**: Unified LLM interface with automatic fallback for all 4 providers

**Tasks**:
1. **TDD Cycle 1**: `BaseLLMClient` interface
   - RED: Write tests for abstract interface contract
   - GREEN: Implement abstract base class
   - REFACTOR: Add type hints and documentation

2. **TDD Cycle 2**: OpenAI adapter
   - RED: Write tests with mocked OpenAI responses
   - GREEN: Implement `OpenAIClient`
   - REFACTOR: Error handling and retry logic

3. **TDD Cycle 3**: Anthropic adapter
   - RED: Write tests with mocked Anthropic responses
   - GREEN: Implement `AnthropicClient`
   - REFACTOR: Normalize response format

4. **TDD Cycle 4**: Google adapter
   - RED: Write tests with mocked Google Gemini responses
   - GREEN: Implement `GoogleClient`
   - REFACTOR: Handle API quirks

5. **TDD Cycle 5**: Ollama adapter
   - RED: Write tests with mocked Ollama responses
   - GREEN: Implement `OllamaClient`
   - REFACTOR: Local connection handling

6. **TDD Cycle 6**: Factory with fallback chain
   - RED: Write tests for fallback logic (primary fail → secondary success)
   - GREEN: Implement `LLMClientFactory` with chain traversal
   - REFACTOR: Configurable retry and timeout logic

**Deliverables**:
- All 4 provider adapters functional
- Factory fallback chain operational
- Test coverage ≥90% for `src/models/`

**Tags Covered**: `<FR1-multi-provider>`, `<FR2-fallback>`, `<FR7-all-providers>`, `<IR1-base-client>`, `<IR2-factory-config>`

---

### Phase 2: BaseAgent Implementation (Week 3)

**Goal**: Core agent framework with LiveKit integration

**Tasks**:
1. **TDD Cycle 1**: `BaseAgent` abstract class
   - RED: Write tests for agent lifecycle (init, message, transfer)
   - GREEN: Implement `BaseAgent` with LiveKit hooks
   - REFACTOR: Context management utilities

2. **TDD Cycle 2**: LiveKit VoiceAssistant integration
   - RED: Write tests with mocked VoiceAssistant
   - GREEN: Implement LiveKit connection and event handlers
   - REFACTOR: Error recovery and reconnection logic

3. **TDD Cycle 3**: Context preservation mechanism
   - RED: Write tests for context serialization/deserialization
   - GREEN: Implement `TransferHandler`
   - REFACTOR: Optimize context size and format

**Deliverables**:
- `BaseAgent` abstract class complete
- LiveKit integration functional
- Context preservation verified

**Tags Covered**: `<IR3-livekit-api>`, `<IR4-transfer-api>`, `<NFR2-context-integrity>`

---

### Phase 3: Specialized Agents & Transfers (Week 4)

**Goal**: Medical triage pattern with three specialized agents

**Tasks**:
1. **TDD Cycle 1**: `GreeterAgent`
   - RED: Write tests for greeting logic and transfer triggers
   - GREEN: Implement `GreeterAgent` with keyword detection
   - REFACTOR: Prompt engineering for natural greetings

2. **TDD Cycle 2**: `TriageAgent`
   - RED: Write tests for urgency assessment and routing
   - GREEN: Implement `TriageAgent` with multi-path routing
   - REFACTOR: Rule-based decision tree

3. **TDD Cycle 3**: `SupportAgent`
   - RED: Write tests for task execution (appointments, billing, etc.)
   - GREEN: Implement `SupportAgent` with task handlers
   - REFACTOR: Extensible task plugin system

4. **TDD Cycle 4**: Agent transfer workflow
   - RED: Write tests for full Greeter→Triage→Support flow
   - GREEN: Implement transfer coordination and context handoff
   - REFACTOR: Transfer logging and debugging

**Deliverables**:
- All 3 specialized agents operational
- Agent transfer with context preservation verified
- Medical triage workflow validated

**Tags Covered**: `<FR3-transfer-context>`, `<FR6-medical-triage>`, `<NFR2-context-integrity>`

---

### Phase 4: Configuration & Testing (Week 5)

**Goal**: YAML configuration and 90% test coverage with mocked providers

**Tasks**:
1. **TDD Cycle 1**: Configuration schema
   - RED: Write tests for Pydantic validation
   - GREEN: Implement `Config` models for prompts and providers
   - REFACTOR: Default values and environment variable overrides

2. **TDD Cycle 2**: YAML parsing
   - RED: Write tests for YAML loading and error handling
   - GREEN: Implement YAML loaders with schema validation
   - REFACTOR: Helpful error messages for invalid config

3. **TDD Cycle 3**: Mocked provider tests
   - RED: Write comprehensive tests with `MockLLMClient`
   - GREEN: Expand test coverage to 90% across all modules
   - REFACTOR: Test fixtures and helper utilities

4. **TDD Cycle 4**: Performance validation
   - RED: Write tests for fallback timing (<5 seconds)
   - GREEN: Optimize fallback chain execution
   - REFACTOR: Async optimization and concurrency

**Deliverables**:
- YAML configuration system operational
- Test coverage ≥90% achieved
- Performance benchmarks validated

**Tags Covered**: `<FR4-yaml-config>`, `<NFR1-fallback-perf>`, `<NFR3-coverage>`, `<NFR5-async>`

---

### Phase 5: Integration & Validation (Week 6)

**Goal**: Console and room modes operational, full system validation

**Tasks**:
1. **TDD Cycle 1**: Console mode
   - RED: Write tests for console interaction loop
   - GREEN: Implement `console_runner.py` with CLI interface
   - REFACTOR: User-friendly prompts and formatting

2. **TDD Cycle 2**: Room mode
   - RED: Write tests for LiveKit room connection
   - GREEN: Implement `room_runner.py` with LiveKit server
   - REFACTOR: Connection pooling and error recovery

3. **TDD Cycle 3**: End-to-end integration
   - RED: Write tests for complete medical triage workflow
   - GREEN: Validate all scenarios from `acceptance.md`
   - REFACTOR: Logging, observability, and debugging tools

4. **TDD Cycle 4**: Documentation and deployment
   - Add docstrings and type hints across all modules
   - Create README with setup and usage instructions
   - Prepare deployment configuration (Docker, environment variables)

**Deliverables**:
- Console and room modes fully operational
- All acceptance criteria validated
- System ready for production deployment

**Tags Covered**: `<FR5-exec-modes>`, `<NFR4-logging>`, all integration scenarios

---

## TECHNICAL DEPENDENCIES

### Python Packages

**Core Runtime**:
```
livekit-agents>=1.0       # LiveKit Agents SDK for voice interaction
openai>=1.0               # OpenAI GPT-4/3.5 API client
anthropic>=0.25           # Anthropic Claude API client
google-generativeai>=0.3  # Google Gemini API client
ollama>=0.1               # Ollama local LLM client
pydantic>=2.0             # Configuration validation and type safety
pyyaml>=6.0               # YAML configuration parsing
python-dotenv>=1.0        # Environment variable management
```

**Testing & Development**:
```
pytest>=7.0               # Testing framework
pytest-asyncio>=0.21      # Async/await test support
pytest-cov>=4.0           # Code coverage reporting
pytest-mock>=3.10         # Advanced mocking fixtures
black>=23.0               # Code formatting
mypy>=1.0                 # Static type checking
ruff>=0.1.0               # Fast Python linter
```

**DevOps**:
```
docker>=24.0              # Containerization
docker-compose>=2.20      # Multi-container orchestration
```

---

## ARCHITECTURE DECISIONS

### Decision 1: Adapter Pattern for Providers

**Context**: Multiple LLM providers with different APIs

**Decision**: Use Adapter Pattern with `BaseLLMClient` interface

**Rationale**:
- Isolates provider-specific code
- Enables easy addition of new providers
- Simplifies testing with mock adapters

**Alternatives Considered**: Direct API calls (rejected: tight coupling), Plugin system (rejected: over-engineering)

---

### Decision 2: Mocked Testing Strategy

**Context**: Real LLM API calls are expensive, slow, and non-deterministic

**Decision**: Use mocked providers for all CI tests, optional real provider tests locally

**Rationale**:
- Fast test execution (<10 seconds for full suite)
- Deterministic results (no API flakiness)
- Zero API costs in CI pipeline
- Enables comprehensive edge case testing

**Alternatives Considered**: Real API integration tests (rejected: cost/speed), Recorded responses (rejected: maintenance burden)

---

### Decision 3: YAML Configuration

**Context**: Agent prompts and provider settings need easy modification

**Decision**: Use YAML files with Pydantic validation

**Rationale**:
- Human-readable and editable without code changes
- Pydantic ensures type safety and validation
- Supports environment variable overrides
- Easy to version control and review

**Alternatives Considered**: JSON (rejected: less readable), Python files (rejected: requires code restart), Database (rejected: over-engineering)

---

### Decision 4: Medical Triage Pattern

**Context**: Need to demonstrate multi-agent coordination

**Decision**: Implement three specialized agents (Greeter, Triage, Support)

**Rationale**:
- Clear separation of concerns
- Demonstrates context preservation across transfers
- Realistic use case for voice agents
- Based on proven LiveKit example

**Alternatives Considered**: Single general-purpose agent (rejected: less interesting), More agents (rejected: scope creep)

---

## RISKS & MITIGATION

### Risk 1: Provider API Changes

**Impact**: HIGH | **Probability**: MEDIUM

**Description**: Provider APIs may introduce breaking changes

**Mitigation**:
- Pin dependency versions in `requirements.txt`
- Isolate provider logic in adapters (easy to update)
- Monitor provider changelogs and deprecation notices
- Maintain test coverage for adapter interfaces

---

### Risk 2: Fallback Chain Exhaustion

**Impact**: HIGH | **Probability**: LOW

**Description**: All providers in chain may fail simultaneously

**Mitigation**:
- Include Ollama as local fallback (no network dependency)
- Implement graceful degradation message to user
- Log exhaustion events for monitoring and alerting
- Consider request queuing for temporary outages

---

### Risk 3: Context Size Exceeds Token Limits

**Impact**: MEDIUM | **Probability**: MEDIUM

**Description**: Long conversations may exceed provider context windows

**Mitigation**:
- Implement context summarization for long conversations
- Truncate oldest messages when nearing limits
- Monitor context size in logs and alerts
- Document context limits in user guide

---

### Risk 4: Async Complexity Bugs

**Impact**: MEDIUM | **Probability**: MEDIUM

**Description**: Async/await code may introduce race conditions or deadlocks

**Mitigation**:
- Use type hints and mypy for static analysis
- Comprehensive async testing with pytest-asyncio
- Follow async best practices (avoid blocking calls)
- Code review focus on async patterns

---

### Risk 5: LiveKit Integration Issues

**Impact**: MEDIUM | **Probability**: LOW

**Description**: LiveKit SDK updates may break voice integration

**Mitigation**:
- Pin LiveKit SDK version initially
- Mock LiveKit in tests (reduce dependency on SDK behavior)
- Follow LiveKit SDK migration guides
- Test room mode thoroughly before production deployment

---

## TESTING STRATEGY

### Coverage Targets

| Module           | Minimum Coverage | Focus Areas                           |
|------------------|------------------|---------------------------------------|
| `src/models/`    | 95%              | Fallback logic, error handling        |
| `src/agents/`    | 90%              | Transfer logic, agent decision-making |
| `src/config.py`  | 90%              | Validation, parsing errors            |
| `src/main.py`    | 85%              | Mode selection, initialization        |
| **Overall**      | **90%**          | All modules combined                  |

### Test Categories

1. **Unit Tests** (70% of tests):
   - Individual class methods and functions
   - Mocked dependencies
   - Fast execution (<5 seconds total)

2. **Integration Tests** (25% of tests):
   - Multi-module workflows
   - Agent transfer scenarios
   - Fallback chain validation

3. **Performance Tests** (5% of tests):
   - Fallback timing benchmarks
   - Context serialization overhead
   - Concurrent request handling

---

## NEXT STEPS

After SPEC approval and plan review:

1. **Execute `/clear`** to reset token context (saves 45-50K tokens)
2. **Run `/moai:2-run SPEC-AGENT-001`** to begin TDD implementation
3. **Follow Phase 1** (Model Abstraction & Fallback) first
4. **Verify quality gates** after each phase (test coverage, TRUST 5)
5. **Complete all 5 phases** before `/moai:3-sync` documentation generation

---

**Estimated Implementation**: 6 weeks (following TDD methodology)

**Quality Gate**: 90% test coverage, all acceptance scenarios pass

**Deployment Target**: Personal mode (GitHub Flow), console + room modes operational

---

**END OF IMPLEMENTATION PLAN**
