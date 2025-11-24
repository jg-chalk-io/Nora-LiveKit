---
id: SPEC-AGENT-001
version: 0.1.0
status: completed
created: 2025-11-24
updated: 2025-11-24
implemented: 2025-11-24
author: @user
priority: P0
test_coverage: 83%
final_status: Production Ready
---

# SPEC-AGENT-001: Multi-Provider LLM Agent System with Medical Triage Pattern

## HISTORY

| Version | Date       | Author | Changes               |
|---------|------------|--------|-----------------------|
| 0.1.0   | 2025-11-24 | @user  | Initial SPEC creation |

---

## OVERVIEW

This specification defines a multi-provider LLM agent system with automatic fallback capabilities, context-preserving agent transfers, and a medical triage pattern. The system supports OpenAI, Anthropic, Google, and Ollama providers, with LiveKit integration for voice-based interactions.

**Project**: Nora-LiveKit
**Mode**: Personal (GitHub Flow)
**TDD**: Enabled (90% coverage target)
**Language**: Python 3.11+
**Based On**: LiveKit medical office triage example

---

## EARS SPECIFICATION

### Environment (E)

**WHEN** the system operates:

1. **Runtime Environment**:
   - Python 3.11+ runtime with async/await support
   - LiveKit server for real-time voice communication
   - Access to LLM provider APIs (OpenAI, Anthropic, Google, Ollama)
   - YAML configuration files for prompts and settings

2. **Execution Modes**:
   - Console mode: Command-line interaction for development/testing
   - Room mode: LiveKit room-based voice interaction for production

3. **Network Conditions**:
   - Internet connectivity for cloud providers (OpenAI, Anthropic, Google)
   - Local network for Ollama provider
   - Variable latency and potential provider outages

4. **LiveKit Environment**:
   - LiveKit Agents SDK v1.0+
   - VoiceAssistant API integration
   - Real-time audio streaming capabilities

---

### Assumptions (A)

**ASSUMING THAT**:

1. **Provider Reliability**:
   - Any single LLM provider may experience temporary outages or rate limits
   - Fallback to alternative providers is acceptable and maintains user experience
   - Provider API contracts remain stable within major versions

2. **Context Preservation**:
   - Conversation context must be preserved across agent transfers
   - Context size fits within provider token limits (or can be summarized)
   - Context serialization/deserialization does not introduce significant latency

3. **Configuration Management**:
   - YAML-based configuration is sufficient for prompts and agent definitions
   - Configuration changes require system restart (no hot-reload required)
   - Pydantic validation ensures configuration integrity

4. **Testing Strategy**:
   - Mocked LLM providers provide sufficient test coverage
   - 90% test coverage is achievable with mocked providers only
   - Integration tests with real providers are handled separately (CI/CD)

5. **Medical Triage Pattern**:
   - Three-agent pattern (Greeter, Triage, Support) covers core use cases
   - Agent specialization improves response quality over single-agent approach
   - Transfer logic is deterministic and rule-based

---

### Requirements (R)

#### Functional Requirements

**FR1: Multi-Provider LLM Support**
- **WHEN** the system needs LLM inference
- **THE SYSTEM SHALL** support OpenAI, Anthropic, Google Gemini, and Ollama providers
- **VIA** a unified `BaseLLMClient` interface with provider-specific adapters
- **TAG**: `<FR1-multi-provider>`

**FR2: Automatic Fallback Chain**
- **WHEN** a primary LLM provider fails or is unavailable
- **THE SYSTEM SHALL** automatically attempt the next provider in the configured fallback chain
- **UNTIL** a successful response is received or all providers are exhausted
- **TAG**: `<FR2-fallback>`

**FR3: Agent Transfer with Context Preservation**
- **WHEN** an agent transfers the conversation to another agent
- **THE SYSTEM SHALL** preserve full conversation history and metadata
- **AND** make context available to the receiving agent
- **TAG**: `<FR3-transfer-context>`

**FR4: YAML-Based Configuration**
- **WHEN** the system initializes
- **THE SYSTEM SHALL** load agent prompts, provider settings, and fallback chains from YAML files
- **AND** validate configuration using Pydantic models
- **TAG**: `<FR4-yaml-config>`

**FR5: Dual Execution Modes**
- **WHEN** the system is launched
- **THE SYSTEM SHALL** support both console mode (CLI) and room mode (LiveKit)
- **AS** determined by command-line arguments
- **TAG**: `<FR5-exec-modes>`

**FR6: Medical Triage Agent Pattern**
- **WHEN** a user initiates contact
- **THE SYSTEM SHALL** implement three specialized agents:
  - **Greeter Agent**: Welcomes user and identifies initial needs
  - **Triage Agent**: Assesses urgency and routes to appropriate support
  - **Support Agent**: Handles specific medical office tasks
- **TAG**: `<FR6-medical-triage>`

**FR7: All Four Providers in Phase 1**
- **WHEN** Phase 1 implementation is complete
- **THE SYSTEM SHALL** include working adapters for OpenAI, Anthropic, Google, and Ollama
- **WITH** mocked tests for all four providers
- **TAG**: `<FR7-all-providers>`

---

#### Non-Functional Requirements

**NFR1: Fallback Performance**
- **WHEN** a provider fails
- **THE SYSTEM SHALL** complete fallback to the next provider within 5 seconds
- **INCLUDING** error detection, provider switch, and response generation
- **TAG**: `<NFR1-fallback-perf>`

**NFR2: Context Preservation Integrity**
- **WHEN** agent transfer occurs
- **THE SYSTEM SHALL** preserve 100% of conversation context
- **WITHOUT** data loss or corruption
- **TAG**: `<NFR2-context-integrity>`

**NFR3: Test Coverage**
- **WHEN** TDD implementation is complete
- **THE SYSTEM SHALL** achieve minimum 90% test coverage
- **USING** mocked LLM providers (no real API calls in CI)
- **TAG**: `<NFR3-coverage>`

**NFR4: Observability**
- **WHEN** provider failures or transfers occur
- **THE SYSTEM SHALL** log events with structured data
- **INCLUDING** provider name, error type, timestamp, and fallback success
- **TAG**: `<NFR4-logging>`

**NFR5: Async Performance**
- **WHEN** handling LLM requests
- **THE SYSTEM SHALL** use async/await patterns
- **TO** prevent blocking operations and optimize throughput
- **TAG**: `<NFR5-async>`

---

#### Interface Requirements

**IR1: BaseLLMClient Interface**
- **WHEN** implementing provider adapters
- **THE SYSTEM SHALL** define a standard `BaseLLMClient` abstract base class
- **WITH** methods: `generate()`, `stream()`, `health_check()`
- **TAG**: `<IR1-base-client>`

**IR2: LLMClientFactory Configuration**
- **WHEN** initializing the LLM client factory
- **THE SYSTEM SHALL** accept a list of providers in priority order
- **AND** configure retry logic, timeouts, and fallback behavior
- **TAG**: `<IR2-factory-config>`

**IR3: BaseAgent LiveKit Integration**
- **WHEN** implementing agent classes
- **THE SYSTEM SHALL** integrate with LiveKit VoiceAssistant API
- **USING** standard hooks: `on_message()`, `on_transfer()`, `on_end()`
- **TAG**: `<IR3-livekit-api>`

**IR4: Transfer Handler API**
- **WHEN** an agent initiates a transfer
- **THE SYSTEM SHALL** provide a `TransferHandler` interface
- **WITH** methods: `prepare_context()`, `execute_transfer()`, `verify_context()`
- **TAG**: `<IR4-transfer-api>`

---

### Specifications (S)

#### Architecture Design

**1. Model Abstraction Layer** (`src/models/`)
- **Pattern**: Adapter Pattern
- **Components**:
  - `BaseLLMClient` (ABC): Standard interface for all providers
  - `OpenAIClient`, `AnthropicClient`, `GoogleClient`, `OllamaClient`: Provider-specific adapters
  - `LLMClientFactory`: Factory with fallback chain logic
- **Responsibilities**:
  - Normalize provider APIs to unified interface
  - Handle provider-specific authentication and configuration
  - Implement retry logic and error handling

**2. Agent System** (`src/agents/`)
- **Pattern**: Strategy Pattern + Template Method
- **Components**:
  - `BaseAgent` (ABC): Core agent behavior and LiveKit integration
  - `GreeterAgent`: First-contact welcome agent
  - `TriageAgent`: Assessment and routing agent
  - `SupportAgent`: Task execution agent
  - `TransferHandler`: Context preservation logic
- **Responsibilities**:
  - Manage conversation state and context
  - Execute agent-specific prompts and logic
  - Coordinate agent transfers with context preservation

**3. Configuration Management** (`config/`)
- **Pattern**: Configuration as Code
- **Components**:
  - `prompts.yaml`: Agent prompts and system messages
  - `providers.yaml`: Provider settings and fallback chain
  - `Config` (Pydantic model): Configuration validation
- **Responsibilities**:
  - Centralize all configurable parameters
  - Validate configuration at startup
  - Provide type-safe configuration access

**4. Testing Framework** (`tests/`)
- **Pattern**: Mock-based Testing
- **Components**:
  - `MockLLMClient`: Deterministic LLM response simulator
  - `test_models/`: Provider adapter tests
  - `test_agents/`: Agent behavior and transfer tests
  - `test_integration/`: End-to-end workflow tests
- **Responsibilities**:
  - Achieve 90% coverage with mocked providers
  - Validate fallback logic and error handling
  - Verify context preservation across transfers

**5. Entry Point** (`src/main.py`)
- **Pattern**: Command Pattern
- **Components**:
  - CLI argument parsing (console vs. room mode)
  - Factory initialization (LLM clients, agents)
  - Mode-specific execution logic
- **Responsibilities**:
  - Bootstrap application based on mode
  - Initialize LiveKit connection (room mode)
  - Start console interaction loop (console mode)

---

#### Technology Stack

**Core Dependencies**:
```
livekit-agents>=1.0       # LiveKit Agents SDK
openai>=1.0               # OpenAI API client
anthropic>=0.25           # Anthropic API client
google-generativeai>=0.3  # Google Gemini API client
ollama>=0.1               # Ollama local LLM client
pydantic>=2.0             # Configuration validation
pyyaml>=6.0               # YAML parsing
```

**Testing Dependencies**:
```
pytest>=7.0               # Testing framework
pytest-asyncio>=0.21      # Async test support
pytest-cov>=4.0           # Coverage reporting
pytest-mock>=3.10         # Mock fixtures
```

---

#### Quality Gates

**TRUST 5 Compliance**:

1. **Test-first**: All features developed with TDD (RED-GREEN-REFACTOR)
2. **Readable**: Maximum 5 modules per layer, clear naming conventions
3. **Unified**: Consistent patterns (Adapter, Factory, Strategy)
4. **Secured**: Input validation, API key management, error boundaries
5. **Trackable**: Full test coverage with deterministic mocked providers

**Coverage Target**: 90% minimum across all modules

---

## TRACEABILITY

### Requirement Tag Index

| Tag                      | Requirement                        | Test Coverage Location       |
|--------------------------|-----------------------------------|------------------------------|
| `<FR1-multi-provider>`   | Multi-provider LLM support        | `tests/test_models/`         |
| `<FR2-fallback>`         | Automatic fallback chain          | `tests/test_factory.py`      |
| `<FR3-transfer-context>` | Agent transfer with context       | `tests/test_agents/`         |
| `<FR4-yaml-config>`      | YAML-based configuration          | `tests/test_config.py`       |
| `<FR5-exec-modes>`       | Console and room modes            | `tests/test_main.py`         |
| `<FR6-medical-triage>`   | Medical triage agent pattern      | `tests/test_integration.py`  |
| `<FR7-all-providers>`    | All 4 providers in Phase 1        | `tests/test_models/`         |
| `<NFR1-fallback-perf>`   | Fallback within 5 seconds         | `tests/test_performance.py`  |
| `<NFR2-context-integrity>` | Context preservation            | `tests/test_transfer.py`     |
| `<NFR3-coverage>`        | 90% test coverage                 | `pytest-cov` report          |
| `<NFR4-logging>`         | Structured logging                | `tests/test_logging.py`      |
| `<NFR5-async>`           | Async/await optimization          | All async test files         |
| `<IR1-base-client>`      | BaseLLMClient interface           | `tests/test_base_client.py`  |
| `<IR2-factory-config>`   | Factory configuration             | `tests/test_factory.py`      |
| `<IR3-livekit-api>`      | LiveKit VoiceAssistant API        | `tests/test_base_agent.py`   |
| `<IR4-transfer-api>`     | Transfer handler API              | `tests/test_transfer.py`     |

---

## DEPENDENCIES

### External Services
- **OpenAI API**: GPT-4/GPT-3.5 models
- **Anthropic API**: Claude models
- **Google API**: Gemini models
- **Ollama**: Local LLM runtime

### Internal Systems
- **LiveKit Server**: Real-time communication infrastructure

### Configuration Files
- `config/prompts.yaml`: Agent prompts
- `config/providers.yaml`: Provider settings and fallback chain
- `.env`: API keys and secrets (not committed to repo)

---

## CONSTRAINTS

### Technical Constraints
- Python 3.11+ required for async/await syntax
- LiveKit server must be accessible (room mode)
- At least one LLM provider must be available
- Provider token limits constrain context size

### Security Constraints
- API keys stored in environment variables only
- No sensitive data logged to console or files
- Input validation on all user messages
- Rate limiting per provider requirements

### Performance Constraints
- Fallback completion within 5 seconds
- Context serialization adds <100ms overhead
- Maximum 10 concurrent agent sessions (initial target)

---

## RISKS & MITIGATION

| Risk                          | Impact | Probability | Mitigation Strategy                          |
|-------------------------------|--------|-------------|----------------------------------------------|
| All providers fail            | High   | Low         | Graceful degradation message, queue requests |
| Context exceeds token limits  | Medium | Medium      | Context summarization or truncation          |
| Provider API changes          | High   | Medium      | Version pinning, adapter pattern isolation   |
| Fallback exhaustion           | High   | Low         | Clear error messages, fallback to Ollama     |
| Async complexity bugs         | Medium | Medium      | Comprehensive async testing, type hints      |

---

## ACCEPTANCE CRITERIA

See `acceptance.md` for detailed Given/When/Then scenarios and edge case testing.

**Minimum Acceptance**: All 3 core scenarios pass with 90% test coverage using mocked providers.

---

## NEXT STEPS

After SPEC approval:

1. Execute `/clear` to initialize token context
2. Run `/moai:2-run SPEC-AGENT-001` for TDD implementation
3. Follow 5-phase implementation plan (see `plan.md`)
4. Verify quality gates pass before `/moai:3-sync`

---

**END OF SPEC-AGENT-001**
