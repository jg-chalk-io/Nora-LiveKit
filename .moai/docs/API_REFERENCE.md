# API Reference

Complete API documentation for the Nora-LiveKit multi-provider LLM agent system.

**Last Updated**: November 24, 2025
**Coverage**: 83% (152 tests passing)

---

## Table of Contents

1. [LLM Client Interfaces](#llm-client-interfaces)
2. [Provider Adapters](#provider-adapters)
3. [Factory Pattern](#factory-pattern)
4. [Agent System](#agent-system)
5. [Transfer Handler](#transfer-handler)
6. [Configuration](#configuration)

---

## LLM Client Interfaces

### BaseLLMClient (Abstract Base Class)

Abstract interface for all LLM provider implementations.

**Location**: `src/models/base_client.py`

```python
class BaseLLMClient(ABC):
    """Abstract interface for LLM providers."""

    @abstractmethod
    async def generate(self, prompt: str, context: list[dict] | None = None) -> str:
        """Generate a single response from the LLM.

        Args:
            prompt: The user prompt/message
            context: Optional conversation history as list of dicts with 'role' and 'content'

        Returns:
            Generated response string

        Raises:
            Exception: If LLM generation fails
        """
        pass

    @abstractmethod
    async def stream(
        self, prompt: str, context: list[dict] | None = None
    ) -> AsyncIterator[str]:
        """Stream response tokens from the LLM.

        Args:
            prompt: The user prompt/message
            context: Optional conversation history

        Yields:
            Response tokens as strings

        Raises:
            Exception: If streaming fails
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Verify provider availability.

        Returns:
            True if provider is available, False otherwise
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the provider name (e.g., 'openai', 'anthropic')."""
        pass

    @property
    @abstractmethod
    def model(self) -> str:
        """Return the model identifier (e.g., 'gpt-4', 'claude-3')."""
        pass
```

**Example Usage**:

```python
from src.models import OpenAIClient

# Create a client
client = OpenAIClient(api_key="sk-...", model="gpt-4-turbo")

# Generate a response
response = await client.generate("Hello, how are you?")

# Stream tokens
async for token in await client.stream("Hello"):
    print(token, end="")

# Check health
is_available = await client.health_check()
```

---

## Provider Adapters

### OpenAIClient

OpenAI API adapter implementing ChatCompletion models (GPT-4, GPT-3.5).

**Location**: `src/models/openai_client.py`

```python
class OpenAIClient(BaseLLMClient):
    """OpenAI GPT-4 and GPT-3.5 adapter."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "gpt-4-turbo",
        timeout: float = 30.0
    ):
        """Initialize OpenAI client.

        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            model: Model name (default: gpt-4-turbo)
            timeout: Request timeout in seconds
        """
        pass
```

**Supported Models**:
- `gpt-4-turbo` (Latest GPT-4 turbo model)
- `gpt-3.5-turbo` (Faster, cost-effective)
- Any other OpenAI model via custom `model` parameter

**Test Coverage**: 100% (mocked tests)

### AnthropicClient

Anthropic API adapter implementing Claude models.

**Location**: `src/models/anthropic_client.py`

```python
class AnthropicClient(BaseLLMClient):
    """Anthropic Claude adapter."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "claude-3-5-sonnet-20241022",
        timeout: float = 30.0
    ):
        """Initialize Anthropic client.

        Args:
            api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env var)
            model: Model name (default: claude-3-5-sonnet)
            timeout: Request timeout in seconds
        """
        pass
```

**Supported Models**:
- `claude-3-5-sonnet-20241022` (Latest Sonnet)
- `claude-3-opus-20240229` (Most capable)
- `claude-3-haiku-20240307` (Fast, compact)

**Test Coverage**: 98% (mocked tests)

### GoogleClient

Google Gemini API adapter.

**Location**: `src/models/google_client.py`

```python
class GoogleClient(BaseLLMClient):
    """Google Gemini API adapter."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "gemini-pro",
        timeout: float = 30.0
    ):
        """Initialize Google Gemini client.

        Args:
            api_key: Google API key (defaults to GOOGLE_API_KEY env var)
            model: Model name (default: gemini-pro)
            timeout: Request timeout in seconds
        """
        pass
```

**Supported Models**:
- `gemini-pro` (Text generation)
- `gemini-pro-vision` (Multimodal)

**Test Coverage**: 38% (streaming not mocked)

### OllamaClient

Local Ollama LLM adapter for offline inference.

**Location**: `src/models/ollama_client.py`

```python
class OllamaClient(BaseLLMClient):
    """Ollama local LLM adapter."""

    def __init__(
        self,
        base_url: str | None = None,
        model: str = "llama2",
        timeout: float = 30.0
    ):
        """Initialize Ollama client.

        Args:
            base_url: Ollama server URL (defaults to OLLAMA_BASE_URL env var or http://localhost:11434)
            model: Model name (default: llama2)
            timeout: Request timeout in seconds
        """
        pass
```

**Supported Models**:
- `llama2` (Meta Llama 2)
- `mistral` (Mistral)
- Any local model installed in Ollama

**Test Coverage**: 38% (streaming not mocked)

---

## Factory Pattern

### LLMClientFactory

Factory class managing multiple LLM clients with automatic fallback chain.

**Location**: `src/models/factory.py`

```python
class LLMClientFactory:
    """Factory for managing LLM clients with automatic fallback."""

    def __init__(
        self,
        clients: list[BaseLLMClient],
        timeout: float = 30.0,
        max_retries: int = 1
    ):
        """Initialize LLM client factory with fallback chain.

        Args:
            clients: List of LLM clients in fallback priority order
            timeout: Timeout per client request in seconds
            max_retries: Maximum retries per client before fallback

        Raises:
            ValueError: If clients list is empty
        """
        pass

    async def generate(
        self,
        prompt: str,
        context: list[dict] | None = None,
        fallback_callback: Callable[[str, Exception], None] | None = None
    ) -> str:
        """Generate response with automatic fallback.

        Attempts generation with each client in order until success.

        Args:
            prompt: User prompt
            context: Optional conversation history as list of {'role', 'content'} dicts
            fallback_callback: Optional callback(provider_name, error) on fallback

        Returns:
            Generated response from first successful provider

        Raises:
            RuntimeError: If all clients in fallback chain fail
        """
        pass

    async def stream(
        self,
        prompt: str,
        context: list[dict] | None = None,
        fallback_callback: Callable[[str, Exception], None] | None = None
    ):
        """Stream response tokens with automatic fallback.

        Attempts streaming with each client in order until success.

        Args:
            prompt: User prompt
            context: Optional conversation history
            fallback_callback: Optional callback on fallback

        Yields:
            Response tokens from first successful provider

        Raises:
            RuntimeError: If all clients fail
        """
        pass

    async def health_check(self) -> dict[str, bool]:
        """Check health of all clients in fallback chain.

        Returns:
            Dictionary mapping client names to health status
            Example: {'openai': True, 'anthropic': False, 'google': True}
        """
        pass

    def get_fallback_chain(self) -> list[str]:
        """Get the fallback chain order.

        Returns:
            List of provider names in priority order
        """
        pass

    def add_client(self, client: BaseLLMClient) -> None:
        """Add a client to the end of the fallback chain.

        Args:
            client: LLM client to add
        """
        pass
```

**Example Usage**:

```python
from src.models import LLMClientFactory, OpenAIClient, AnthropicClient, OllamaClient

# Create clients
openai = OpenAIClient()
anthropic = AnthropicClient()
ollama = OllamaClient()

# Create factory with fallback chain
factory = LLMClientFactory([openai, anthropic, ollama])

# Generate with automatic fallback
def on_fallback(provider: str, error: Exception):
    print(f"Fallback from {provider}: {error}")

response = await factory.generate(
    "Hello",
    context=[{"role": "user", "content": "Hi"}],
    fallback_callback=on_fallback
)

# Check all provider health
health = await factory.health_check()
# {'openai': True, 'anthropic': True, 'google': False, 'ollama': True}
```

---

## Agent System

### BaseAgent (Abstract Base Class)

Abstract base class for all agent implementations.

**Location**: `src/agents/base_agent.py`

```python
class BaseAgent(ABC):
    """Abstract base class for all agents."""

    def __init__(
        self,
        name: str,
        llm_client: BaseLLMClient,
        system_prompt: str
    ):
        """Initialize base agent.

        Args:
            name: Agent identifier (e.g., 'greeter', 'triage', 'support')
            llm_client: LLM client for generation
            system_prompt: System prompt defining agent behavior
        """
        pass

    @property
    def name(self) -> str:
        """Return agent name."""
        pass

    @property
    def system_prompt(self) -> str:
        """Return system prompt."""
        pass

    def add_message_to_history(self, role: str, content: str) -> None:
        """Add message to conversation history.

        Args:
            role: Message role ('user' or 'assistant')
            content: Message content
        """
        pass

    def get_conversation_history(self) -> list[dict]:
        """Get full conversation history.

        Returns:
            List of message dicts with 'role' and 'content' keys
        """
        pass

    def clear_history(self) -> None:
        """Clear conversation history."""
        pass

    async def on_message(self, message: str) -> str:
        """Process incoming message and generate response.

        Args:
            message: User message

        Returns:
            Agent response

        Raises:
            Exception: If LLM generation fails
        """
        pass

    async def should_transfer(self) -> tuple[bool, str | None]:
        """Determine if conversation should be transferred.

        Returns:
            Tuple of (should_transfer, target_agent_name) where target is None if no transfer
        """
        pass

    @abstractmethod
    async def process_transfer(self, context: dict) -> None:
        """Handle receiving a transfer from another agent.

        Args:
            context: Transferred context dict with 'agent_name', 'conversation_history', 'system_prompt'
        """
        pass

    async def prepare_transfer_context(self) -> dict:
        """Prepare context for transfer to another agent.

        Returns:
            Context dict ready for transfer
        """
        pass
```

### GreeterAgent

First-contact agent that welcomes users and identifies initial needs.

**Location**: `src/agents/greeter_agent.py`

```python
class GreeterAgent(BaseAgent):
    """Agent for greeting and initial needs assessment."""

    def __init__(
        self,
        llm_client: BaseLLMClient,
        system_prompt: str | None = None
    ):
        """Initialize greeter agent.

        Args:
            llm_client: LLM client for generation
            system_prompt: Optional custom system prompt (defaults to professional greeting)
        """
        pass

    async def should_transfer(self) -> tuple[bool, str | None]:
        """Check for urgent keywords indicating triage transfer needed.

        Detects keywords: emergency, urgent, pain, bleeding, difficulty breathing,
        chest pain, severe, critical, serious

        Returns:
            (True, 'triage') if urgent keyword detected, else (False, None)
        """
        pass
```

**Default System Prompt**:

```
You are a friendly and professional medical office greeter.
Your role is to:
1. Welcome the caller warmly
2. Identify their initial needs (appointment, urgent issue, general inquiry, etc.)
3. Determine if they need to be transferred to the triage agent for urgent matters
4. Keep responses brief and professional

Transfer to triage agent if the caller mentions: emergency, urgent, pain, bleeding,
difficulty breathing, chest pain, or other critical health issues.
Otherwise, gather their basic information and needs.
```

**Test Coverage**: 96%

### TriageAgent

Assessment and routing agent that evaluates patient urgency.

**Location**: `src/agents/triage_agent.py`

```python
class TriageAgent(BaseAgent):
    """Agent for medical triage and routing."""

    def __init__(
        self,
        llm_client: BaseLLMClient,
        system_prompt: str | None = None
    ):
        """Initialize triage agent.

        Args:
            llm_client: LLM client for generation
            system_prompt: Optional custom system prompt
        """
        pass

    async def should_transfer(self) -> tuple[bool, str | None]:
        """Check for support/task keywords indicating support agent transfer.

        Detects keywords: schedule, appointment, billing, prescription, refill

        Returns:
            (True, 'support') if task keyword detected, else (False, None)
        """
        pass
```

**Default System Prompt**:

```
You are a medical triage specialist at a healthcare facility.
Your role is to:
1. Assess the urgency and nature of the patient's condition
2. Determine if they need immediate emergency care or can be scheduled
3. Identify the appropriate department or specialist needed
4. Route to support agent for appointment scheduling, billing, or prescriptions
5. Ask clarifying questions to better understand the situation

Assess urgency level: Critical (immediate ER), High (same day), Medium (this week), Low (next week+)

Route to support agent if: caller needs appointment scheduling, billing information, or prescription refills.
```

**Test Coverage**: 96%

### SupportAgent

Task execution agent handling appointments, billing, and prescriptions.

**Location**: `src/agents/support_agent.py`

```python
class SupportAgent(BaseAgent):
    """Agent for handling specific tasks (scheduling, billing, etc.)."""

    def __init__(
        self,
        llm_client: BaseLLMClient,
        system_prompt: str | None = None
    ):
        """Initialize support agent.

        Args:
            llm_client: LLM client for generation
            system_prompt: Optional custom system prompt
        """
        pass

    async def should_transfer(self) -> tuple[bool, str | None]:
        """Check for medical keywords indicating triage escalation.

        Detects keywords: symptom, diagnosis, treatment, medication, pain

        Returns:
            (True, 'triage') if medical keyword detected, else (False, None)
        """
        pass
```

**Default System Prompt**:

```
You are a medical office support specialist.
Your role is to:
1. Schedule appointments for patients
2. Answer billing and insurance questions
3. Process prescription refill requests
4. Provide general office information
5. Redirect back to triage if medical questions arise

Be helpful, professional, and efficient.
For complex medical questions, recommend re-connecting with the triage agent.
```

**Available Services**:
- `appointment_scheduling`
- `billing_inquiry`
- `prescription_refill`
- `office_information`

**Test Coverage**: 96%

---

## Transfer Handler

### TransferHandler

Utility class for managing context-preserving agent transfers.

**Location**: `src/agents/transfer_handler.py`

```python
class TransferHandler:
    """Handles agent-to-agent transfers with context preservation."""

    @staticmethod
    async def prepare_context(agent: BaseAgent) -> dict:
        """Prepare context for agent transfer.

        Args:
            agent: Agent to transfer from

        Returns:
            Context dict with structure:
            {
                'agent_name': str,
                'conversation_history': list[dict],
                'system_prompt': str
            }
        """
        pass

    @staticmethod
    async def execute_transfer(
        source_agent: BaseAgent,
        target_agent: BaseAgent
    ) -> None:
        """Execute transfer between agents.

        Prepares context from source and passes to target's process_transfer method.

        Args:
            source_agent: Agent initiating transfer
            target_agent: Agent receiving transfer
        """
        pass

    @staticmethod
    async def verify_context(
        source_agent: BaseAgent,
        target_agent: BaseAgent
    ) -> bool:
        """Verify context integrity after transfer.

        Checks that target agent has received and retained all source history.

        Args:
            source_agent: Original agent
            target_agent: Target agent

        Returns:
            True if context preserved correctly, False if mismatch detected
        """
        pass
```

**Example Usage**:

```python
from src.agents import GreeterAgent, TriageAgent, TransferHandler

# Create agents with same LLM client
greeter = GreeterAgent(llm_client=factory)
triage = TriageAgent(llm_client=factory)

# Process user message
response = await greeter.on_message("I have chest pain")

# Check if transfer needed
should_transfer, target = await greeter.should_transfer()

# Execute transfer with full context preservation
if should_transfer:
    await TransferHandler.execute_transfer(greeter, triage)

    # Verify integrity
    is_valid = await TransferHandler.verify_context(greeter, triage)

    # Continue conversation with triage agent
    response = await triage.on_message("I need an assessment")
```

---

## Configuration

### Environment Variables

```bash
# OpenAI
OPENAI_API_KEY=sk-...

# Anthropic
ANTHROPIC_API_KEY=sk-ant-...

# Google Gemini
GOOGLE_API_KEY=...

# Ollama
OLLAMA_BASE_URL=http://localhost:11434

# LiveKit (for room mode)
LIVEKIT_URL=ws://localhost:7880
LIVEKIT_API_KEY=...
LIVEKIT_API_SECRET=...
```

### Configuration Files

**config/providers.yaml**:

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

  google:
    model: gemini-pro
    timeout: 30

  ollama:
    model: llama2
    timeout: 30
    base_url: http://localhost:11434
```

**config/prompts.yaml**:

```yaml
agents:
  greeter:
    system_prompt: |
      You are a friendly and professional medical office greeter...
    transfer_keywords:
      - emergency
      - urgent
      - pain
      - bleeding
      - difficulty breathing
      - chest pain

  triage:
    system_prompt: |
      You are a medical triage specialist...
    transfer_keywords:
      - schedule
      - appointment
      - billing
      - prescription
      - refill

  support:
    system_prompt: |
      You are a medical office support specialist...
    services:
      - appointment_scheduling
      - billing_inquiry
      - prescription_refill
      - office_information
```

---

## Performance Characteristics

| Metric | Target | Actual |
|--------|--------|--------|
| Fallback time | <5 seconds | Achieved (async implementation) |
| Context serialization overhead | <100ms | Achieved |
| Response latency | 1-10 seconds | Depends on LLM provider |
| Test coverage | 90% | 83% (152 tests passing) |
| Provider adapters | 4 | 4 (OpenAI, Anthropic, Google, Ollama) |

---

## Error Handling

All methods use standard Python exception handling:

```python
try:
    response = await client.generate("prompt")
except asyncio.TimeoutError:
    # Provider request timed out
    print("Request timed out")
except Exception as e:
    # Provider API error or network issue
    print(f"Generation failed: {e}")
```

Factory automatically handles and retries errors per the fallback chain.

---

**END OF API REFERENCE**
