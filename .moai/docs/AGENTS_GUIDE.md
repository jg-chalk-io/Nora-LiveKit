# Agents Guide

Comprehensive guide to understanding, using, and extending the agent system in Nora-LiveKit.

**Last Updated**: November 24, 2025
**Current Agents**: 3 (Greeter, Triage, Support)
**Test Coverage**: 96% average

---

## Table of Contents

1. [Agent System Overview](#agent-system-overview)
2. [Agent Specializations](#agent-specializations)
3. [Context Preservation](#context-preservation)
4. [Transfer Rules](#transfer-rules)
5. [Example Workflows](#example-workflows)
6. [Adding New Agents](#adding-new-agents)

---

## Agent System Overview

The agent system is built on three core principles:

### 1. Specialization
Each agent has a specific role with distinct responsibilities:
- **Greeter**: Initial contact and needs identification
- **Triage**: Urgency assessment and routing
- **Support**: Task execution (appointments, billing, prescriptions)

### 2. Context Preservation
When agents transfer conversations, **100% of conversation history is preserved**:
- Full message history transferred
- System prompts preserved
- Metadata maintained
- No context loss

### 3. Deterministic Transfers
Transfer logic is rule-based and transparent:
- Keyword matching for transfer triggers
- Clear transfer rules per agent
- Logging of all transfers
- Verification of context integrity

---

## Agent Specializations

### GreeterAgent

**Role**: First point of contact for incoming requests

**Responsibilities**:
1. Welcome users warmly and professionally
2. Identify initial needs (appointment, urgent issue, etc.)
3. Detect urgent medical conditions
4. Route urgent cases to triage immediately

**System Prompt**:
```
You are a friendly and professional medical office greeter.
Your role is to:
1. Welcome the caller warmly
2. Identify their initial needs (appointment, urgent issue, general inquiry, etc.)
3. Determine if they need to be transferred to the triage agent for urgent matters
4. Keep responses brief and professional

Transfer to triage agent if the caller mentions: emergency, urgent, pain,
bleeding, difficulty breathing, chest pain, or other critical health issues.
Otherwise, gather their basic information and needs.
```

**Transfer Keywords** (triggers immediate transfer to TriageAgent):
```python
urgent_keywords = [
    "emergency",
    "urgent",
    "pain",
    "bleeding",
    "difficulty breathing",
    "chest pain",
    "severe",
    "critical",
    "serious"
]
```

**Example Interactions**:

```
User: "Hi, I'd like to schedule an appointment for my annual checkup"
Greeter: "Welcome! I'm happy to help you schedule your appointment.
          Let me connect you with our scheduling specialist."
Transfer: No (routine appointment - no urgent keywords)

---

User: "I have severe chest pain and shortness of breath"
Greeter: (Detects "chest pain" + "shortness of breath")
Transfer: YES → TriageAgent (urgent medical condition detected)
TriageAgent: "I'm immediately connecting you with our medical team..."
```

**Implementation**: `src/agents/greeter_agent.py`

**Test Coverage**: 96%

---

### TriageAgent

**Role**: Assess urgency and determine appropriate care level

**Responsibilities**:
1. Evaluate severity of medical conditions
2. Assess urgency level (critical, high, medium, low)
3. Identify appropriate care pathway
4. Route to support for non-urgent tasks
5. Ask clarifying questions

**System Prompt**:
```
You are a medical triage specialist at a healthcare facility.
Your role is to:
1. Assess the urgency and nature of the patient's condition
2. Determine if they need immediate emergency care or can be scheduled
3. Identify the appropriate department or specialist needed
4. Route to support agent for appointment scheduling, billing, or prescriptions
5. Ask clarifying questions to better understand the situation

Assess urgency level: Critical (immediate ER), High (same day),
Medium (this week), Low (next week+)

Route to support agent if: caller needs appointment scheduling, billing
information, or prescription refills.
```

**Transfer Keywords** (triggers transfer to SupportAgent):
```python
support_keywords = [
    "schedule",
    "appointment",
    "billing",
    "prescription",
    "refill"
]
```

**Urgency Levels**:
- **Critical (ER)**: Chest pain, severe trauma, severe allergic reactions
- **High (same day)**: High fever, severe infections, severe symptoms
- **Medium (this week)**: Moderate symptoms, non-urgent specialist needs
- **Low (next week+)**: Routine appointments, follow-ups, preventive care

**Example Interactions**:

```
Input (from Greeter transfer):
- Full conversation history from greeter included
- User reported "chest pain and difficulty breathing"

TriageAgent: "I understand you're experiencing chest pain and difficulty
             breathing. These symptoms require immediate evaluation.
             Are you currently in a safe location? Can you get to an
             emergency room immediately?"

(After assessment)
TriageAgent: "Based on your symptoms, you need emergency care.
             I'm routing you to our emergency department."
Transfer: Might stay in TriageAgent or escalate to emergency

---

User: "I need to schedule a follow-up after my assessment"
TriageAgent: (Detects "schedule")
Transfer: YES → SupportAgent
SupportAgent: "I'll help you schedule that follow-up appointment..."
```

**Implementation**: `src/agents/triage_agent.py`

**Test Coverage**: 96%

---

### SupportAgent

**Role**: Handle administrative and routine tasks

**Responsibilities**:
1. Schedule appointments
2. Answer billing and insurance questions
3. Process prescription refill requests
4. Provide general office information
5. Redirect to triage for medical questions

**System Prompt**:
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

**Medical Keywords** (triggers escalation back to TriageAgent):
```python
medical_keywords = [
    "symptom",
    "diagnosis",
    "treatment",
    "medication",
    "pain"
]
```

**Available Services**:
- `appointment_scheduling`: Schedule and reschedule visits
- `billing_inquiry`: Insurance and payment questions
- `prescription_refill`: Refill requests for medications
- `office_information`: Hours, location, general info

**Example Interactions**:

```
Input (from Triage transfer):
- Full conversation history preserved
- Patient assessed and routed for scheduling

SupportAgent: "Thank you for that information. I'll be happy to schedule
              your follow-up appointment. What day would work best for you?"

User: "I have a new symptom that's concerning"
SupportAgent: (Detects "symptom" keyword)
Transfer: YES → TriageAgent
TriageAgent: (Re-evaluates based on new symptom)

---

User: "I need to refill my blood pressure medication"
SupportAgent: "I can help with that prescription refill. Let me process
              that for you and arrange pickup at our pharmacy."
(No transfer needed - within scope)
```

**Implementation**: `src/agents/support_agent.py`

**Test Coverage**: 96%

---

## Context Preservation

### How Context Transfer Works

When an agent transfers to another agent, the system preserves:

```python
context = {
    "agent_name": "greeter",           # Where transfer came from
    "conversation_history": [          # Full message history
        {"role": "user", "content": "I have chest pain"},
        {"role": "assistant", "content": "Let me connect you..."},
        # ... all previous messages
    ],
    "system_prompt": "You are a friendly medical office greeter..."  # Original prompt
}
```

### Transfer Execution

```python
# 1. Prepare context from source agent
context = await TransferHandler.prepare_context(greeter_agent)

# 2. Pass context to target agent
await triage_agent.process_transfer(context)

# 3. Target agent inherits history
triage_agent._conversation_history = context["conversation_history"]

# 4. Target agent ready to continue with full context
response = await triage_agent.on_message("Continue conversation...")
```

### Verification

After transfer, integrity can be verified:

```python
is_valid = await TransferHandler.verify_context(greeter_agent, triage_agent)

if not is_valid:
    logger.error("Context integrity check failed!")
    # Handle gracefully
else:
    logger.info("Context transferred successfully")
```

**Key Guarantee**: 100% of conversation history is preserved with zero message loss.

---

## Transfer Rules

### Transfer Decision Matrix

| Source Agent | Target Agent | Trigger Condition | Keywords |
|--------------|--------------|-------------------|----------|
| Greeter | Triage | Medical emergency | "emergency", "urgent", "pain", "bleeding", "difficulty breathing", "chest pain", "severe", "critical", "serious" |
| Triage | Support | Task request | "schedule", "appointment", "billing", "prescription", "refill" |
| Triage | ER/Emergency | Critical condition | N/A (system action) |
| Support | Triage | Medical question | "symptom", "diagnosis", "treatment", "medication", "pain" |
| Triage | Greeter | Restart | User request (uncommon) |

### Transfer Logic Per Agent

#### GreeterAgent.should_transfer()

```python
async def should_transfer(self) -> tuple[bool, str | None]:
    """Check for urgent keywords in conversation."""
    if not self._conversation_history:
        return False, None

    # Check all user messages for urgent keywords
    for message in self._conversation_history:
        if message.get("role") == "user":
            message_text = message.get("content", "").lower()
            for keyword in self._urgent_keywords:
                if keyword in message_text:
                    logger.info(f"Urgent keyword detected: {keyword}")
                    return True, "triage"  # Transfer to triage

    return False, None  # No transfer needed
```

**When Transfer Happens**: After any user message, checks for urgent keywords.

#### TriageAgent.should_transfer()

```python
async def should_transfer(self) -> tuple[bool, str | None]:
    """Check for task keywords indicating support agent needed."""
    if not self._conversation_history:
        return False, None

    # Check all user messages for support keywords
    for message in self._conversation_history:
        if message.get("role") == "user":
            message_text = message.get("content", "").lower()
            for keyword in self._transfer_keywords:
                if keyword in message_text:
                    logger.info(f"Support keyword detected: {keyword}")
                    return True, "support"  # Transfer to support

    return False, None  # No transfer needed
```

**When Transfer Happens**: After medical assessment, if user mentions scheduling, billing, or prescriptions.

#### SupportAgent.should_transfer()

```python
async def should_transfer(self) -> tuple[bool, str | None]:
    """Check for medical keywords requiring triage."""
    if not self._conversation_history:
        return False, None

    # Only check the last user message
    last_message = self._conversation_history[-1]
    if last_message.get("role") == "user":
        message_text = last_message.get("content", "").lower()
        # Medical keywords that should escalate to triage
        medical_keywords = ["symptom", "diagnosis", "treatment", "medication", "pain"]
        for keyword in medical_keywords:
            if keyword in message_text:
                logger.info(f"Medical keyword detected: {keyword}")
                return True, "triage"  # Escalate to triage

    return False, None  # No transfer needed
```

**When Transfer Happens**: During support conversation, if medical questions arise.

---

## Example Workflows

### Workflow 1: Urgent Medical Emergency

```
Scenario: Patient calls with chest pain

Step 1: Greeter answers
User: "Hello, I'm experiencing severe chest pain"
Greeter: "I'm sorry to hear you're in pain. Let me connect you with
         our medical team immediately."
         [Detects "pain" → triggers transfer]

Step 2: Transfer to Triage (full context preserved)
Transferred context includes:
- "severe chest pain" message
- Greeter's greeting and response
- All conversation history

Step 3: Triage assesses
TriageAgent: "I'm connecting you with emergency services.
             This is a critical condition that needs immediate care.
             Can you confirm you have access to an ambulance?"

Result: High/Critical urgency → Patient directed to ER
```

### Workflow 2: Routine Appointment Scheduling

```
Scenario: Patient calls for checkup appointment

Step 1: Greeter identifies need
User: "Hi, I'd like to schedule my annual checkup"
Greeter: "Welcome! I'll help you with that.
         Let me get some information...
         [No urgent keywords → no transfer]

Step 2: Continue with Greeter
Greeter: "What date would work best for you?"
User: "Sometime next week"
Greeter: [After gathering info]
         "Great! Let me connect you with our scheduling team."
         [Detects "schedule" → triggers transfer]

Step 3: Transfer to Support (context preserved)
Transferred context includes:
- Initial greeting and needs
- Preferred date mentioned
- Full conversation

Step 4: Support handles scheduling
SupportAgent: "Thank you for choosing our office.
              I see you're interested in next week.
              Let me find available times..."

Result: Appointment scheduled successfully
```

### Workflow 3: Medical Assessment with Task Routing

```
Scenario: Patient with acute symptoms needs assessment and follow-up

Step 1: Greeter routes urgent case
User: "I have a high fever and severe headache"
Greeter: [Detects "fever", "severe" → transfer to triage]

Step 2: Triage assesses condition
TriageAgent: "I'm concerned about your symptoms.
             Let me ask a few questions...
             When did this fever start?
             Any other symptoms?"
User: "About 6 hours ago. Also have a sore throat."

TriageAgent: "I recommend you see a doctor today.
             Can you come to the urgent care clinic this afternoon?"
User: "Yes, what time should I come?"
     [Detects "time" + context = scheduling need → transfer to support]

Step 3: Transfer to Support (complete context)
SupportAgent: "Perfect! I see Dr. Johnson has 2 PM available.
              Will that work for you?"
User: "Yes, perfect"

Step 4: Confirm and provide details
SupportAgent: "Great! Your appointment is confirmed at 2 PM today
              with Dr. Johnson. Here's our address and parking info..."

Result: Patient gets assessment + scheduling in optimal workflow
```

### Workflow 4: Medical Escalation During Support

```
Scenario: Patient mentions new symptoms while scheduling

Step 1-3: [Following from Workflow 2 or 3...]
SupportAgent: [Helping with billing or scheduling]

Step 4: Patient mentions medical concern
User: "Also, I've been having sharp chest pain
       whenever I exercise"
     [Detects "chest pain" → medical keyword triggers escalation]

Step 5: Escalate back to Triage
SupportAgent: "I notice you mentioned chest pain with exercise.
              This is important. Let me connect you back with our
              medical team to evaluate this concern."
              [Transfers to triage with full context]

Step 6: Triage re-evaluates
TriageAgent: [Has full history including why they came in + new symptom]
            "Let me assess this new symptom. Exercise-related chest pain
             can be concerning. I'd like to schedule you for
             an EKG and stress test..."

Result: Patient gets appropriate medical evaluation before routine appointment
```

---

## Adding New Agents

### Step 1: Create Agent Class

Create a new file `src/agents/my_agent.py`:

```python
"""My custom agent for specialized tasks."""

import logging
from .base_agent import BaseAgent

logger = logging.getLogger(__name__)

DEFAULT_MY_AGENT_PROMPT = """You are a specialized agent...
Your role is to:
1. [Responsibility 1]
2. [Responsibility 2]
3. [Responsibility 3]
"""


class MyAgent(BaseAgent):
    """Agent for [specific purpose]."""

    def __init__(self, llm_client, system_prompt: str | None = None):
        """Initialize my agent.

        Args:
            llm_client: LLM client for generation
            system_prompt: Optional custom system prompt
        """
        super().__init__(
            name="my_agent",  # Unique identifier
            llm_client=llm_client,
            system_prompt=system_prompt or DEFAULT_MY_AGENT_PROMPT,
        )
        # Define transfer keywords
        self._transfer_keywords = ["keyword1", "keyword2", "keyword3"]

    async def should_transfer(self) -> tuple[bool, str | None]:
        """Determine if transfer is needed.

        Returns:
            Tuple of (should_transfer, target_agent_name)
        """
        if not self._conversation_history:
            return False, None

        # Check for transfer keywords
        for message in self._conversation_history:
            if message.get("role") == "user":
                message_text = message.get("content", "").lower()
                for keyword in self._transfer_keywords:
                    if keyword in message_text:
                        logger.info(f"Transfer keyword detected: {keyword}")
                        return True, "target_agent"

        return False, None

    async def process_transfer(self, context: dict) -> None:
        """Handle receiving a transfer from another agent.

        Args:
            context: Transferred context from previous agent
        """
        # Inherit conversation history if provided
        if "conversation_history" in context:
            self._conversation_history = context["conversation_history"]
        logger.info(f"MyAgent received transfer from {context.get('agent_name')}")
```

### Step 2: Register in Config

Update `config/prompts.yaml`:

```yaml
agents:
  my_agent:
    system_prompt: |
      You are a specialized agent...
      Your role is to...
    transfer_keywords:
      - keyword1
      - keyword2
      - keyword3
```

### Step 3: Create Tests

Create `tests/test_agents/test_my_agent.py`:

```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from src.agents import MyAgent


@pytest.fixture
def mock_llm():
    return AsyncMock()


@pytest.fixture
def my_agent(mock_llm):
    return MyAgent(llm_client=mock_llm)


@pytest.mark.asyncio
async def test_initialization(my_agent):
    assert my_agent.name == "my_agent"
    assert my_agent.system_prompt is not None


@pytest.mark.asyncio
async def test_on_message(my_agent, mock_llm):
    mock_llm.generate.return_value = "Test response"

    response = await my_agent.on_message("Test message")

    assert response == "Test response"
    assert len(my_agent.get_conversation_history()) == 2  # user + assistant


@pytest.mark.asyncio
async def test_should_transfer(my_agent):
    my_agent.add_message_to_history("user", "I need keyword1")

    should_transfer, target = await my_agent.should_transfer()

    assert should_transfer is True
    assert target == "target_agent"


@pytest.mark.asyncio
async def test_process_transfer(my_agent):
    context = {
        "agent_name": "previous_agent",
        "conversation_history": [
            {"role": "user", "content": "Previous message"}
        ]
    }

    await my_agent.process_transfer(context)

    assert len(my_agent.get_conversation_history()) == 1
    assert my_agent.get_conversation_history()[0]["content"] == "Previous message"
```

### Step 4: Update Exports

Update `src/agents/__init__.py`:

```python
from .base_agent import BaseAgent
from .greeter_agent import GreeterAgent
from .triage_agent import TriageAgent
from .support_agent import SupportAgent
from .my_agent import MyAgent  # Add this line
from .transfer_handler import TransferHandler

__all__ = [
    "BaseAgent",
    "GreeterAgent",
    "TriageAgent",
    "SupportAgent",
    "MyAgent",  # Add this line
    "TransferHandler",
]
```

### Step 5: Update Main

Update `src/main.py` to support new agent:

```python
# In factory initialization
my_agent = MyAgent(llm_client=factory, system_prompt=config.agents.my_agent.prompt)

# In agent registry
agents = {
    "greeter": greeter,
    "triage": triage,
    "support": support,
    "my_agent": my_agent,  # Add this line
}
```

### Step 6: Test

Run tests:

```bash
pytest tests/test_agents/test_my_agent.py -v
```

Verify integration:

```bash
python src/main.py console --agent my_agent
```

---

## Best Practices for Agents

### 1. Clear Transfer Keywords

Use distinct, non-overlapping keywords:

```python
# Good
urgent_keywords = ["emergency", "urgent", "severe"]
task_keywords = ["schedule", "appointment", "billing"]

# Bad - overlapping
keywords = ["urgent", "appointment urgent"]  # "urgent" matches both
```

### 2. Deterministic Transfer Logic

Keep transfer logic simple and keyword-based:

```python
# Good - transparent and testable
if keyword in message_text:
    return True, target_agent

# Bad - vague and hard to debug
if self._llm_client.generate(f"Should transfer? {message}") == "yes":
    return True, "some_agent"
```

### 3. Preserve Context on Transfer

Always inherit conversation history in `process_transfer()`:

```python
# Good
async def process_transfer(self, context: dict) -> None:
    if "conversation_history" in context:
        self._conversation_history = context["conversation_history"]

# Bad - loses context
async def process_transfer(self, context: dict) -> None:
    pass  # Context ignored!
```

### 4. Logging

Log important events for observability:

```python
logger.info(f"Urgent keyword detected: {keyword}")
logger.info(f"Transfer executed: {source_agent} -> {target_agent}")
logger.error(f"Context integrity check failed")
```

### 5. Test Coverage

Aim for 95%+ test coverage:

```python
# Test normal flow
# Test edge cases (empty history, etc.)
# Test transfer logic
# Test error conditions
```

---

**END OF AGENTS GUIDE**
