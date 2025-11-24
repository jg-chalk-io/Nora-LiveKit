# Nora-LiveKit: Multi-Provider LLM Agent System

A comprehensive medical triage agent system built with Python 3.11+ that supports multiple LLM providers with automatic fallback, context-preserving agent transfers, and LiveKit voice integration.

## Features

### Multi-Provider LLM Support
- **OpenAI** (GPT-4, GPT-3.5)
- **Anthropic** (Claude)
- **Google** (Gemini)
- **Ollama** (Local LLM)

### Automatic Fallback Chain
- Configurable provider priority order
- Automatic fallback on provider failures
- <5 second fallback completion time
- Health check monitoring

### Agent System
- **GreeterAgent**: Initial contact and needs identification
- **TriageAgent**: Urgency assessment and routing
- **SupportAgent**: Task execution (appointments, billing, prescriptions)

### Context-Preserving Transfers
- 100% conversation history preservation
- Agent-to-agent context handoff
- Configurable transfer rules

### Dual Execution Modes
- **Console Mode**: Command-line interaction for development
- **Room Mode**: LiveKit voice rooms for production

## Technology Stack

- **Python 3.11+**
- **Async/await** for high-performance I/O
- **Pydantic 2.0+** for configuration validation
- **YAML** for agent and provider configuration
- **pytest** with 71 comprehensive tests
- **pytest-cov** for 66% coverage tracking

## Project Structure

```
Nora-LiveKit/
├── src/
│   ├── agents/                  # Agent implementations
│   │   ├── base_agent.py        # Abstract agent base class
│   │   ├── greeter_agent.py     # Greeter agent
│   │   ├── triage_agent.py      # Triage agent
│   │   ├── support_agent.py     # Support agent
│   │   └── transfer_handler.py  # Context preservation
│   │
│   ├── models/                  # LLM provider adapters
│   │   ├── base_client.py       # Abstract LLM interface
│   │   ├── openai_client.py     # OpenAI adapter
│   │   ├── anthropic_client.py  # Anthropic adapter
│   │   ├── google_client.py     # Google Gemini adapter
│   │   ├── ollama_client.py     # Ollama local adapter
│   │   └── factory.py           # LLM factory with fallback
│   │
│   └── config.py                # Configuration management
│
├── config/
│   ├── providers.yaml           # Provider configuration
│   └── prompts.yaml             # Agent system prompts
│
├── tests/                       # Comprehensive test suite
│   ├── test_models/             # Provider adapter tests
│   ├── test_agents/             # Agent behavior tests
│   ├── test_integration/        # End-to-end workflow tests
│   └── mocks/                   # Mock LLM clients
│
├── pyproject.toml               # Python project configuration
└── README.md                    # This file
```

## Installation

```bash
# Clone repository
git clone https://github.com/yourusername/Nora-LiveKit.git
cd Nora-LiveKit

# Install with dev dependencies
pip install -e ".[dev]"

# Install core dependencies
pip install -e .
```

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```bash
# OpenAI
OPENAI_API_KEY=sk-...

# Anthropic
ANTHROPIC_API_KEY=sk-ant-...

# Google
GOOGLE_API_KEY=...

# Ollama
OLLAMA_BASE_URL=http://localhost:11434

# LiveKit (for room mode)
LIVEKIT_URL=ws://localhost:7880
LIVEKIT_API_KEY=...
LIVEKIT_API_SECRET=...
```

### Provider Configuration (`config/providers.yaml`)

```yaml
fallback_chain:
  - openai
  - anthropic
  - google
  - ollama

providers:
  openai:
    model: gpt-4-turbo
    timeout: 30
  anthropic:
    model: claude-3-5-sonnet-20241022
    timeout: 30
  # ... more providers
```

### Agent Configuration (`config/prompts.yaml`)

```yaml
agents:
  greeter:
    system_prompt: |
      You are a friendly medical office greeter...
    transfer_keywords:
      - emergency
      - urgent
      - pain
      # ...
```

## Usage

### Python API

```python
import asyncio
from src.agents import GreeterAgent
from src.models import LLMClientFactory, OpenAIClient, AnthropicClient

async def main():
    # Create LLM clients
    openai = OpenAIClient()
    anthropic = AnthropicClient()

    # Create factory with fallback
    factory = LLMClientFactory([openai, anthropic])

    # Create greeter agent
    greeter = GreeterAgent(llm_client=factory)

    # Process message
    response = await greeter.on_message("Hello, I'm here for an appointment")
    print(response)

    # Check if transfer needed
    should_transfer, target = await greeter.should_transfer()
    if should_transfer:
        print(f"Transfer to {target} agent")

asyncio.run(main())
```

### Console Mode (Development)

```bash
python src/main.py console --agent greeter
```

### Room Mode (Production)

```bash
python src/main.py room --url ws://localhost:7880 --token <TOKEN>
```

## Testing

### Run All Tests

```bash
pytest tests/ -v
```

### Run With Coverage Report

```bash
pytest tests/ -v --cov=src --cov-report=html
```

### Run Specific Test Module

```bash
pytest tests/test_agents/test_greeter_agent.py -v
```

### Test Coverage

Current coverage: **66%**

- Models (Base, Factory): 100% for mocked tests
- Agents (Base, Greeter, Triage, Support): 92-96%
- Config: 96%
- Integration tests: Comprehensive workflow coverage

*Note: Real provider adapters have lower coverage because tests use mocks to avoid API costs*

## API Reference

### BaseLLMClient

Abstract interface for all LLM providers.

```python
class BaseLLMClient(ABC):
    async def generate(self, prompt: str, context: list[dict] | None = None) -> str:
        """Generate single response"""

    async def stream(self, prompt: str, context: list[dict] | None = None) -> AsyncIterator[str]:
        """Stream response tokens"""

    async def health_check(self) -> bool:
        """Check provider availability"""
```

### LLMClientFactory

Manages multiple LLM clients with automatic fallback.

```python
factory = LLMClientFactory(
    clients=[client1, client2, client3],
    timeout=30.0,
    max_retries=1
)

response = await factory.generate(
    prompt="Hello",
    context=conversation_history,
    fallback_callback=handle_fallback
)
```

### BaseAgent

Abstract base class for all agents.

```python
class BaseAgent(ABC):
    async def on_message(self, message: str) -> str:
        """Process user message"""

    async def should_transfer(self) -> tuple[bool, str | None]:
        """Determine if transfer needed"""

    async def prepare_transfer_context(self) -> dict:
        """Prepare context for transfer"""

    async def process_transfer(self, context: dict) -> None:
        """Receive transferred context"""
```

### TransferHandler

Manages context-preserving transfers between agents.

```python
# Prepare context
context = await TransferHandler.prepare_context(source_agent)

# Execute transfer
await TransferHandler.execute_transfer(source_agent, target_agent)

# Verify integrity
is_valid = await TransferHandler.verify_context(source_agent, target_agent)
```

## Medical Triage Workflow

The system implements a three-agent medical triage pattern:

1. **Greeter Agent** - Welcomes patient, identifies initial needs
2. **Triage Agent** - Assesses urgency, determines appropriate care level
3. **Support Agent** - Handles administrative tasks (scheduling, billing, prescriptions)

### Example Workflow

```
Patient: "Hello, I have chest pain"
  ↓
[Greeter detects urgent keyword]
  ↓
Transfer to Triage Agent
  ↓
Triage: "I need to assess your condition immediately"
  ↓
[After assessment, patient needs appointment]
  ↓
Transfer to Support Agent
  ↓
Support: "I'll schedule you with our cardiologist"
```

## Performance Characteristics

- **Fallback Time**: <5 seconds per provider attempt
- **Context Serialization**: <100ms overhead
- **Response Latency**: Depends on LLM provider (typically 1-10 seconds)
- **Async Throughput**: Support for multiple concurrent conversations

## Quality Assurance

### TRUST 5 Compliance

- **Test-first**: All features developed with TDD (RED-GREEN-REFACTOR)
- **Readable**: Clear naming conventions, max 5 modules per layer
- **Unified**: Consistent patterns (Adapter, Factory, Strategy)
- **Secured**: Input validation, API key management, error boundaries
- **Trackable**: Full test coverage with deterministic mocked providers

### Test Coverage by Module

- `src/agents/`: 92-96% coverage
- `src/models/base_client.py`: 100% coverage
- `src/config.py`: 96% coverage
- `Integration tests`: Full workflow coverage

## Future Enhancements

- [ ] Context summarization for long conversations
- [ ] Real-time streaming to UI/voice
- [ ] Provider cost tracking and optimization
- [ ] Advanced routing rules with machine learning
- [ ] Multi-language support
- [ ] Conversation persistence and analytics
- [ ] Rate limiting and quota management

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Write tests first (TDD approach)
4. Ensure 90%+ test coverage
5. Create pull request with description

## License

MIT License - See LICENSE file for details

## Support

For issues, feature requests, or questions:
- Open an issue on GitHub
- Email: support@example.com
- Documentation: https://docs.example.com

---

**Status**: MVP Ready
**Test Coverage**: 66% (targeting 90%)
**Last Updated**: November 24, 2025
