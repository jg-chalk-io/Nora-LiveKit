# Architecture Overview

Comprehensive architecture documentation for the Nora-LiveKit multi-provider LLM agent system.

**Last Updated**: November 24, 2025
**Status**: Production Ready
**Test Coverage**: 83%

---

## Table of Contents

1. [System Overview](#system-overview)
2. [5-Layer Architecture](#5-layer-architecture)
3. [Design Patterns](#design-patterns)
4. [Data Flow](#data-flow)
5. [Module Responsibilities](#module-responsibilities)
6. [Component Interactions](#component-interactions)

---

## System Overview

Nora-LiveKit is a medical office triage system that combines:

- **Multi-provider LLM support** with automatic fallback chains
- **Specialized agent system** with context-preserving transfers
- **Dual execution modes** for development and production
- **LiveKit integration** for voice-based interactions

### Architecture Goals

1. **Flexibility**: Support multiple LLM providers interchangeably
2. **Reliability**: Automatic fallback when providers fail
3. **Modularity**: Clear separation of concerns across layers
4. **Extensibility**: Add new providers or agents without core changes
5. **Observability**: Structured logging for debugging and monitoring

---

## 5-Layer Architecture

```
┌────────────────────────────────────────────────────┐
│ 5. ENTRY LAYER                                     │
│ (main.py)                                          │
│ - CLI argument parsing                             │
│ - Mode selection (console vs. room)                │
│ - Factory initialization                           │
└────────────────────────────────────────────────────┘
                          ↓
┌────────────────────────────────────────────────────┐
│ 4. CONFIGURATION LAYER                             │
│ (config.py, YAML files)                            │
│ - Provider settings & fallback chain               │
│ - Agent system prompts                             │
│ - Environment variable binding                     │
└────────────────────────────────────────────────────┘
                          ↓
┌────────────────────────────────────────────────────┐
│ 3. AGENT LAYER                                     │
│ (agents/)                                          │
│ - BaseAgent (ABC)                                  │
│ - GreeterAgent, TriageAgent, SupportAgent          │
│ - TransferHandler (context preservation)           │
└────────────────────────────────────────────────────┘
                          ↓
┌────────────────────────────────────────────────────┐
│ 2. FACTORY LAYER                                   │
│ (models/factory.py)                                │
│ - LLMClientFactory with fallback chain logic       │
│ - Health check aggregation                         │
└────────────────────────────────────────────────────┘
                          ↓
┌────────────────────────────────────────────────────┐
│ 1. MODELS LAYER                                    │
│ (models/)                                          │
│ - BaseLLMClient (ABC)                              │
│ - Provider adapters (OpenAI, Anthropic, etc.)      │
│ - Provider-specific implementations                │
└────────────────────────────────────────────────────┘
```

### Layer Descriptions

#### Layer 1: Models Layer (`src/models/`)

**Responsibility**: Normalize provider APIs to unified interface

**Components**:
- `BaseLLMClient` (abstract base class)
  - Defines standard interface for all providers
  - Methods: `generate()`, `stream()`, `health_check()`
  - Properties: `name`, `model`

- Provider Adapters:
  - `OpenAIClient`: GPT-4/GPT-3.5 support
  - `AnthropicClient`: Claude models
  - `GoogleClient`: Gemini API
  - `OllamaClient`: Local LLM support

**Design Pattern**: Adapter Pattern
- Converts provider-specific APIs to unified `BaseLLMClient` interface
- Hides implementation details from higher layers
- Enables provider swapping without affecting upper layers

**Key Features**:
- Async/await throughout for non-blocking I/O
- Timeout handling per provider
- API key management from environment variables
- Error logging and structured data

#### Layer 2: Factory Layer (`src/models/factory.py`)

**Responsibility**: Manage fallback chain and provider selection

**Component**: `LLMClientFactory`
- Accepts list of clients in priority order
- Implements fallback logic: try each client until success
- Provides health check aggregation
- Optional fallback callbacks for observability

**Design Pattern**: Factory Pattern + Chain of Responsibility
- Centralizes client management
- Encapsulates fallback selection logic
- Delegates to adapters for actual work

**Key Features**:
- Configurable timeout per request
- Configurable max retries per client
- Fallback callbacks for monitoring
- Health status tracking per provider

**Fallback Algorithm**:
```python
for client in clients:
    try:
        result = await client.generate(prompt)
        return result
    except Exception:
        log_fallback(client.name)
        continue
raise RuntimeError("All clients failed")
```

#### Layer 3: Agent Layer (`src/agents/`)

**Responsibility**: Implement specialized conversation agents with context preservation

**Components**:
- `BaseAgent` (abstract base class)
  - Core agent lifecycle: `on_message()`, `should_transfer()`
  - Context management: conversation history, system prompt
  - Transfer protocol: `prepare_transfer_context()`, `process_transfer()`

- Specialized Agents:
  - `GreeterAgent`: First contact, needs identification
  - `TriageAgent`: Urgency assessment and routing
  - `SupportAgent`: Task execution (scheduling, billing, prescriptions)

- `TransferHandler`: Context-preserving transfer orchestration
  - Prepares context from source agent
  - Executes transfer to target agent
  - Verifies context integrity

**Design Pattern**: Strategy Pattern + Template Method
- Each agent implements different conversation strategy
- `BaseAgent` defines template for agent lifecycle
- Concrete agents override specific behavior

**Transfer Flow**:
```
User Message
    ↓
[GreeterAgent.on_message()]
    ↓
[Check should_transfer() → urgent?]
    ↓
YES: [TransferHandler.execute_transfer(greeter → triage)]
     ↓
     [Triage.process_transfer(context)] ← Full history preserved!
     ↓
     [Triage.on_message()]
    ↓
NO:  [Continue with Greeter]
```

**Context Preservation**:
- Conversation history is serialized/copied on transfer
- Each agent maintains independent history
- Transferred context includes: agent name, messages, system prompt
- Verification ensures no message loss

#### Layer 4: Configuration Layer

**Responsibility**: Centralize all configurable parameters

**Files**:
- `src/config.py`: Pydantic models for type-safe config
- `config/providers.yaml`: Provider settings and fallback chain
- `config/prompts.yaml`: Agent system prompts and keywords
- `.env`: Secrets (API keys, URLs)

**Design Pattern**: Configuration as Code + Dependency Injection
- YAML for human-readable config
- Pydantic for type validation at startup
- Environment variables for secrets

**Key Config Parameters**:
```yaml
# Fallback chain priority
fallback_chain: [openai, anthropic, google, ollama]

# Provider settings
providers:
  openai:
    model: gpt-4-turbo
    timeout: 30

# Agent prompts
agents:
  greeter:
    system_prompt: "You are a friendly medical office greeter..."
    transfer_keywords: [emergency, urgent, pain, ...]
```

#### Layer 5: Entry Layer (`src/main.py`)

**Responsibility**: Initialize system and coordinate execution modes

**Features**:
- CLI argument parsing for mode selection
- Provider/agent factory initialization
- Mode-specific execution:
  - Console mode: Simple REPL loop
  - Room mode: LiveKit VoiceAssistant integration

**Design Pattern**: Command Pattern
- Each execution mode is a separate command
- Factory initializes shared components
- Mode handler encapsulates specific logic

---

## Design Patterns

### 1. Adapter Pattern (Models Layer)

**Problem**: Different LLM providers have different APIs

**Solution**: Create adapters that normalize APIs to `BaseLLMClient` interface

```
OpenAI API          Anthropic API       Google API
     ↓                   ↓                  ↓
[OpenAIClient]  [AnthropicClient]  [GoogleClient]
     ↓                   ↓                  ↓
     └─────────[BaseLLMClient]─────────┘
                       ↓
                 [Unified Interface]
```

**Benefits**:
- Swap providers without changing agent code
- Easy to add new providers
- Provider details isolated

### 2. Factory Pattern (Factory Layer)

**Problem**: Need to manage fallback chain and select clients

**Solution**: Factory encapsulates client selection logic

```
LLMClientFactory
├── clients: [OpenAIClient, AnthropicClient, GoogleClient]
├── timeout: 30
└── fallback_callback: optional_callback

Methods:
├── generate(prompt) → tries clients in order
├── stream(prompt) → tries clients in order
└── health_check() → checks all clients
```

**Benefits**:
- Centralized client management
- Encapsulated fallback logic
- Easy to modify fallback strategy

### 3. Strategy Pattern (Agent Layer)

**Problem**: Different conversation strategies (greeter vs. triage vs. support)

**Solution**: Each agent implements different `should_transfer()` logic

```
BaseAgent
├── GreeterAgent.should_transfer() → checks urgent keywords
├── TriageAgent.should_transfer() → checks task keywords
└── SupportAgent.should_transfer() → checks medical keywords
```

**Benefits**:
- Each agent has distinct responsibility
- Easy to add new agent types
- Transfer logic is agent-specific

### 4. Template Method Pattern (Agent Layer)

**Problem**: Agents have common lifecycle but different implementations

**Solution**: `BaseAgent` defines template, agents override specific steps

```python
# Template in BaseAgent
async def on_message(self, message: str) -> str:
    self.add_message_to_history("user", message)
    response = await self._llm_client.generate(message, context)
    self.add_message_to_history("assistant", response)
    return response

# Each agent can override should_transfer() with specific logic
```

**Benefits**:
- Consistent agent lifecycle
- Common context management
- Specific transfer logic per agent

### 5. Chain of Responsibility (Factory Layer)

**Problem**: Try multiple providers until one succeeds

**Solution**: Factory iterates through client chain

```python
for client in clients:
    try:
        return await client.generate(prompt)
    except:
        continue
```

**Benefits**:
- Clean fallback logic
- Extensible to new providers
- Handles failures gracefully

---

## Data Flow

### Flow 1: Simple Message Processing

```
User Input
    ↓
[Agent.on_message(message)]
    ↓
[Add to conversation history]
    ↓
[Prepare context with system prompt + history]
    ↓
[LLMClientFactory.generate(prompt, context)]
    ↓
[Try OpenAIClient]
    ↓ (if fails)
[Try AnthropicClient]
    ↓ (if fails)
[Try GoogleClient]
    ↓ (if succeeds)
[Return response]
    ↓
[Agent adds response to history]
    ↓
Agent Response
```

**Context Construction**:
```python
context = [
    {"role": "system", "content": agent.system_prompt},
    {"role": "user", "content": "Previous message 1"},
    {"role": "assistant", "content": "Response 1"},
    ...
]
```

### Flow 2: Agent Transfer

```
User: "I have chest pain"
    ↓
[GreeterAgent.on_message()]
    ↓ (LLM generates greeting)
    ↓
[GreeterAgent.should_transfer()]
    ↓ (checks for urgent keywords)
    ↓ (finds "pain" in message)
    ↓ (returns True, "triage")
    ↓
[TransferHandler.execute_transfer(greeter, triage)]
    ├── Prepare context from greeter
    │   └── context = {
    │       "agent_name": "greeter",
    │       "conversation_history": [...],
    │       "system_prompt": "..."
    │   }
    ├── Call triage.process_transfer(context)
    │   └── triage._conversation_history = greeter's history
    └── Return
    ↓
[TriageAgent.on_message("Continue with assessment")]
    ↓ (has full context from greeter)
    ↓ (responds with triage perspective)
    ↓
Triage Response
```

**Key Property**: 100% context preservation across transfer

### Flow 3: Health Check

```
[Factory.health_check()]
    ├── Check OpenAIClient.health_check()
    │   └── Send minimal prompt, await response, return True/False
    ├── Check AnthropicClient.health_check()
    │   └── Send minimal prompt, await response, return True/False
    ├── Check GoogleClient.health_check()
    │   └── Send minimal prompt, await response, return True/False
    └── Check OllamaClient.health_check()
        └── Send minimal prompt, await response, return True/False
    ↓
Return {
    'openai': True,
    'anthropic': True,
    'google': False,
    'ollama': True
}
```

---

## Module Responsibilities

### `src/models/base_client.py`
- **Responsibility**: Define unified LLM interface
- **Exports**: `BaseLLMClient` abstract class
- **Methods**: `generate()`, `stream()`, `health_check()`
- **Test Coverage**: 100%

### `src/models/openai_client.py`
- **Responsibility**: OpenAI GPT API adapter
- **Exports**: `OpenAIClient` class
- **Supports**: GPT-4, GPT-3.5 models
- **Test Coverage**: 100%

### `src/models/anthropic_client.py`
- **Responsibility**: Anthropic Claude API adapter
- **Exports**: `AnthropicClient` class
- **Supports**: Claude 3 family models
- **Test Coverage**: 98%

### `src/models/google_client.py`
- **Responsibility**: Google Gemini API adapter
- **Exports**: `GoogleClient` class
- **Supports**: Gemini Pro, Gemini Pro Vision
- **Test Coverage**: 38% (streaming not mocked)

### `src/models/ollama_client.py`
- **Responsibility**: Ollama local LLM adapter
- **Exports**: `OllamaClient` class
- **Supports**: Any Ollama-compatible model
- **Test Coverage**: 38% (streaming not mocked)

### `src/models/factory.py`
- **Responsibility**: Manage fallback chain and client selection
- **Exports**: `LLMClientFactory` class
- **Key Features**: Fallback logic, health check aggregation
- **Test Coverage**: 84%

### `src/agents/base_agent.py`
- **Responsibility**: Define agent lifecycle and context management
- **Exports**: `BaseAgent` abstract class
- **Methods**: `on_message()`, `should_transfer()`, `process_transfer()`
- **Test Coverage**: 100%

### `src/agents/greeter_agent.py`
- **Responsibility**: First-contact agent with urgency detection
- **Exports**: `GreeterAgent` class
- **Transfer Trigger**: Detects urgent keywords (emergency, pain, bleeding, etc.)
- **Test Coverage**: 96%

### `src/agents/triage_agent.py`
- **Responsibility**: Medical assessment and task routing
- **Exports**: `TriageAgent` class
- **Transfer Trigger**: Detects task keywords (schedule, billing, prescription, etc.)
- **Test Coverage**: 96%

### `src/agents/support_agent.py`
- **Responsibility**: Task execution (appointments, billing, prescriptions)
- **Exports**: `SupportAgent` class
- **Transfer Trigger**: Detects medical keywords (symptom, diagnosis, medication, etc.)
- **Test Coverage**: 96%

### `src/agents/transfer_handler.py`
- **Responsibility**: Context-preserving agent transfers
- **Exports**: `TransferHandler` class
- **Methods**: `prepare_context()`, `execute_transfer()`, `verify_context()`
- **Test Coverage**: 93%

### `src/config.py`
- **Responsibility**: Configuration management with Pydantic validation
- **Exports**: Config classes for providers and agents
- **Features**: Environment variable binding, YAML loading
- **Test Coverage**: 96%

---

## Component Interactions

### Initialization Sequence

```
1. Application Start (main.py)
   ├── Parse command-line arguments
   └── Load configuration (config.py)

2. Factory Initialization
   ├── Create OpenAIClient with API key
   ├── Create AnthropicClient with API key
   ├── Create GoogleClient with API key
   ├── Create OllamaClient with base URL
   └── Create LLMClientFactory([openai, anthropic, google, ollama])

3. Agent Initialization
   ├── Load system prompts from config/prompts.yaml
   ├── Create GreeterAgent(factory, system_prompt)
   ├── Create TriageAgent(factory, system_prompt)
   └── Create SupportAgent(factory, system_prompt)

4. Mode Execution
   ├── Console Mode: Start REPL loop with GreeterAgent
   └── Room Mode: Initialize LiveKit room and start VoiceAssistant
```

### Request Processing Sequence

```
1. User Message → Agent
   agent.on_message("Hello, I have chest pain")

2. Agent → Factory
   factory.generate(prompt, context)

3. Factory → Provider Chain
   Try each client in fallback order:
   - OpenAIClient.generate()
   - AnthropicClient.generate()
   - GoogleClient.generate()
   - OllamaClient.generate()

4. Provider → Response
   Returns generated text

5. Agent → History
   Adds response to conversation_history

6. Agent → Check Transfer
   should_transfer() → (True, "triage")

7. Transfer Handler → Triage Agent
   TransferHandler.execute_transfer(greeter, triage)

8. Triage Agent → Ready
   Inherits full context, ready for next message
```

### Error Handling Strategy

```
Provider Error Handling:
├── Timeout (5s per provider)
│   └── Move to next in fallback chain
├── API Error (auth, rate limit, etc.)
│   └── Move to next in fallback chain
├── Network Error
│   └── Move to next in fallback chain
└── All Providers Failed
    └── Raise RuntimeError("All LLM clients failed")

Agent Error Handling:
├── LLM generation fails
│   └── Log error, raise exception
└── Transfer fails
    └── Log error, continue with current agent
```

---

## Technology Stack

| Layer | Component | Technology | Purpose |
|-------|-----------|-----------|---------|
| Models | OpenAI API | `openai` library | GPT-4/GPT-3.5 inference |
| Models | Anthropic API | `anthropic` library | Claude inference |
| Models | Google API | `google-generativeai` library | Gemini inference |
| Models | Ollama | HTTP REST API | Local LLM inference |
| Factory | Async Management | Python `asyncio` | Non-blocking I/O |
| Agents | Async Processing | Python `asyncio` | Concurrent conversations |
| Config | Validation | Pydantic 2.0+ | Type-safe config |
| Config | File Format | YAML 6.0+ | Human-readable config |
| Testing | Framework | pytest 7.0+ | Test execution |
| Testing | Coverage | pytest-cov 4.0+ | Coverage reporting |
| Testing | Async Tests | pytest-asyncio 0.21+ | Async test support |
| LiveKit | Voice | LiveKit Agents SDK | Real-time voice integration |

---

## Performance Characteristics

| Metric | Target | Achieved |
|--------|--------|----------|
| Fallback completion | <5 seconds | Yes (async) |
| Context overhead | <100ms | Yes |
| Response latency | 1-10 seconds | Depends on LLM |
| Concurrent agents | 10+ | Limited by LLM API |
| Context preservation | 100% | Yes |
| Test coverage | 90% | 83% |

---

## Security Considerations

1. **API Key Management**
   - Keys stored in environment variables only
   - Never logged or exposed in errors
   - Different keys per provider

2. **Input Validation**
   - All user messages validated
   - Prompt injection prevention
   - Context size limits

3. **Error Boundaries**
   - Provider errors don't expose sensitive data
   - Fallback prevents service outage
   - Structured logging for debugging

4. **Configuration**
   - YAML parsed safely
   - Pydantic validates schema
   - Type checking prevents misuse

---

**END OF ARCHITECTURE DOCUMENTATION**
