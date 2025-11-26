---
id: configuration-reference
title: Nora-LiveKit Configuration Reference
description: Complete configuration reference for all Nora-LiveKit components
author: GOOS
created: 2025-11-25
updated: 2025-11-25
version: 1.0.0
---

# Configuration Reference

## Table of Contents

1. [Overview](#overview)
2. [Main Config (Config)](#main-config)
3. [Voice Configuration](#voice-configuration)
4. [Conversation Configuration](#conversation-configuration)
5. [Environment Variables](#environment-variables)
6. [Configuration Loading](#configuration-loading)
7. [Configuration Examples](#configuration-examples)
8. [Validation & Errors](#validation--errors)

---

## Overview

Nora-LiveKit uses hierarchical configuration with three main levels:

```
Config (Main)
├── VoiceConfig (optional)
│   ├── Deepgram STT settings
│   └── Cartesia TTS settings
└── ConversationConfig (optional)
    ├── LLM provider settings
    └── Turn detection settings
```

**Loading Strategy**:
1. Read from environment variables
2. Apply defaults for optional settings
3. Validate required fields
4. Return Config object

---

## Main Config

### Config Class

```python
@dataclass
class Config:
    """Main configuration for Nora LiveKit agent."""

    # Required LiveKit configuration
    livekit_url: str
    livekit_api_key: str
    livekit_api_secret: str

    # Optional settings
    health_check_port: int = 8080
    log_level: str = "INFO"
    log_format: str = "json"
    test_room: str | None = None
    voice: VoiceConfig | None = None
    conversation: ConversationConfig | None = None
```

### Required Fields

#### `livekit_url`

**Environment Variable**: `LIVEKIT_URL`

**Type**: `str`

**Purpose**: WebSocket URL for LiveKit server

**Format**: `ws://host:port` or `wss://host:port`

**Example**:
```bash
export LIVEKIT_URL=ws://localhost:7880
# or for cloud
export LIVEKIT_URL=wss://my-livekit.example.com
```

#### `livekit_api_key`

**Environment Variable**: `LIVEKIT_API_KEY`

**Type**: `str`

**Purpose**: API key for LiveKit authentication

**Example**:
```bash
export LIVEKIT_API_KEY=devkey
```

#### `livekit_api_secret`

**Environment Variable**: `LIVEKIT_API_SECRET`

**Type**: `str`

**Purpose**: Secret for LiveKit API signing

**Example**:
```bash
export LIVEKIT_API_SECRET=secret
```

### Optional Fields

#### `health_check_port`

**Environment Variable**: `HEALTH_CHECK_PORT`

**Type**: `int`

**Default**: `8080`

**Purpose**: Port for health check endpoint

**Example**:
```bash
export HEALTH_CHECK_PORT=8080
```

#### `log_level`

**Environment Variable**: `LOG_LEVEL`

**Type**: `str`

**Default**: `"INFO"`

**Values**: `"DEBUG"`, `"INFO"`, `"WARNING"`, `"ERROR"`, `"CRITICAL"`

**Example**:
```bash
export LOG_LEVEL=DEBUG
```

#### `log_format`

**Environment Variable**: `LOG_FORMAT`

**Type**: `str`

**Default**: `"json"`

**Values**: `"json"`, `"text"`

**Example**:
```bash
export LOG_FORMAT=json
```

#### `test_room`

**Environment Variable**: `LIVEKIT_TEST_ROOM`

**Type**: `str | None`

**Default**: `None`

**Purpose**: Test room name for agent testing

**Example**:
```bash
export LIVEKIT_TEST_ROOM=test-room
```

---

## Voice Configuration

### VoiceConfig Class

```python
@dataclass
class VoiceConfig:
    """Voice pipeline configuration."""

    # Deepgram (STT) - required for voice
    deepgram_api_key: str
    deepgram_model: str = "nova-2"
    deepgram_language: str = "en-US"

    # Cartesia (TTS) - optional
    cartesia_api_key: str = ""
    cartesia_voice_id: str = "default-sonic-voice"
    cartesia_speed: float = 1.0
    cartesia_emotion: str = "neutral"

    # Audio settings
    sample_rate: int = 16000
    channels: int = 1
    latency_target_ms: int = 500
    vad_threshold: float = 0.5
```

### Deepgram Settings

#### `deepgram_api_key`

**Environment Variable**: `DEEPGRAM_API_KEY`

**Type**: `str`

**Required For**: Voice input (speech-to-text)

**Example**:
```bash
export DEEPGRAM_API_KEY=your-deepgram-key
```

#### `deepgram_model`

**Environment Variable**: `DEEPGRAM_MODEL`

**Type**: `str`

**Default**: `"nova-2"`

**Options**: `"nova-2"`, `"nova"`, `"enhanced"`, `"standard"`

**Trade-offs**:
- `nova-2`: Latest, most accurate
- `nova`: Good balance
- `enhanced`: Better accents
- `standard`: Fastest, least accurate

**Example**:
```bash
export DEEPGRAM_MODEL=nova-2
```

#### `deepgram_language`

**Environment Variable**: `DEEPGRAM_LANGUAGE`

**Type**: `str`

**Default**: `"en-US"`

**Options**: Language codes (en-US, es-ES, fr-FR, etc.)

**Example**:
```bash
export DEEPGRAM_LANGUAGE=en-US
```

### Cartesia Settings

#### `cartesia_api_key`

**Environment Variable**: `CARTESIA_API_KEY`

**Type**: `str`

**Default**: `""`

**Purpose**: Text-to-speech provider

**Example**:
```bash
export CARTESIA_API_KEY=your-cartesia-key
```

#### `cartesia_voice_id`

**Environment Variable**: `CARTESIA_VOICE_ID`

**Type**: `str`

**Default**: `"default-sonic-voice"`

**Purpose**: Voice ID for TTS output

**Example**:
```bash
export CARTESIA_VOICE_ID=default-sonic-voice
```

#### `cartesia_speed`

**Environment Variable**: `CARTESIA_SPEED`

**Type**: `float`

**Default**: `1.0`

**Range**: `0.5` - `2.0`

**Example**:
```bash
export CARTESIA_SPEED=1.0
```

#### `cartesia_emotion`

**Environment Variable**: `CARTESIA_EMOTION`

**Type**: `str`

**Default**: `"neutral"`

**Options**: `"neutral"`, `"angry"`, `"happy"`, `"sad"`, `"professional"`

**Example**:
```bash
export CARTESIA_EMOTION=neutral
```

### Audio Settings

#### `sample_rate`

**Environment Variable**: `VOICE_SAMPLE_RATE`

**Type**: `int`

**Default**: `16000`

**Values**: `16000` (CD quality), `8000` (telephony)

**Example**:
```bash
export VOICE_SAMPLE_RATE=16000
```

#### `channels`

**Environment Variable**: `VOICE_CHANNELS`

**Type**: `int`

**Default**: `1`

**Values**: `1` (mono), `2` (stereo)

**Example**:
```bash
export VOICE_CHANNELS=1
```

#### `latency_target_ms`

**Environment Variable**: `VOICE_LATENCY_TARGET`

**Type**: `int`

**Default**: `500`

**Purpose**: Target latency for voice processing

**Example**:
```bash
export VOICE_LATENCY_TARGET=500
```

#### `vad_threshold`

**Environment Variable**: `VAD_THRESHOLD`

**Type**: `float`

**Default**: `0.5`

**Range**: `0.0` - `1.0`

**Purpose**: Voice activity detection sensitivity

**Example**:
```bash
export VAD_THRESHOLD=0.5
```

---

## Conversation Configuration

### ConversationConfig Class

```python
@dataclass
class ConversationConfig:
    """Conversation engine configuration."""

    # LLM Configuration
    llm_provider: str = "openai"
    llm_api_key: str = ""
    llm_model: str = "gpt-4"
    llm_temperature: float = 0.7
    llm_max_tokens: int = 150

    # Context Configuration
    max_history: int = 20

    # Turn Detection Configuration
    vad_threshold: float = 0.5
    min_speech_duration_ms: int = 300
    silence_duration_ms: int = 700

    # Conversation Behavior
    idle_timeout_seconds: int = 120
    enable_interruptions: bool = True
    fallback_response: str = "I'm having trouble right now. Please try again."
```

### LLM Configuration

#### `llm_provider`

**Environment Variable**: `LLM_PROVIDER`

**Type**: `str`

**Default**: `"openai"`

**Options**: `"openai"`, `"anthropic"`

**Example**:
```bash
export LLM_PROVIDER=openai
```

#### `llm_api_key`

**Environment Variable**: `LLM_API_KEY`

**Type**: `str`

**Alternative**: `OPENAI_API_KEY` or `ANTHROPIC_API_KEY`

**Purpose**: API key for LLM provider

**Example**:
```bash
export LLM_API_KEY=sk-...
# Or provider-specific
export OPENAI_API_KEY=sk-...
export ANTHROPIC_API_KEY=sk-ant-...
```

#### `llm_model`

**Environment Variable**: `LLM_MODEL`

**Type**: `str`

**Default**: `"gpt-4"` (OpenAI) or `"claude-3-sonnet-20240229"` (Anthropic)

**OpenAI Options**:
- `"gpt-4"` - Most capable, $0.03/$0.06 per 1K tokens
- `"gpt-4-turbo"` - Balanced, $0.01/$0.03
- `"gpt-3.5-turbo"` - Budget, $0.0005/$0.0015

**Anthropic Options**:
- `"claude-3-opus-20240229"` - Most capable
- `"claude-3-sonnet-20240229"` - Balanced
- `"claude-3-haiku-20240307"` - Fast/cheap

**Example**:
```bash
# OpenAI
export LLM_MODEL=gpt-4

# Anthropic
export LLM_MODEL=claude-3-sonnet-20240229
```

#### `llm_temperature`

**Environment Variable**: `LLM_TEMPERATURE`

**Type**: `float`

**Default**: `0.7`

**Range**: `0.0` - `2.0`

**Impact**:
- `0.0`: Deterministic, factual (best for Q&A)
- `0.7`: Balanced (default, good for conversation)
- `1.5+`: Creative, unpredictable

**Example**:
```bash
export LLM_TEMPERATURE=0.7
```

#### `llm_max_tokens`

**Environment Variable**: `LLM_MAX_TOKENS`

**Type**: `int`

**Default**: `150`

**Range**: `1` - `4096` (model-dependent)

**Impact**:
- Shorter responses = lower cost, faster
- Longer responses = higher cost, slower
- Voice conversations typically need <200 tokens

**Example**:
```bash
export LLM_MAX_TOKENS=150
```

### Context Configuration

#### `max_history`

**Environment Variable**: `CONVERSATION_MAX_HISTORY`

**Type**: `int`

**Default**: `20`

**Range**: `1` - `100`

**Impact**:
- Smaller = cheaper, faster
- Larger = better context, higher cost
- Automatically prunes oldest messages

**Example**:
```bash
export CONVERSATION_MAX_HISTORY=20
```

### Turn Detection Configuration

#### `vad_threshold`

**Environment Variable**: `VAD_THRESHOLD`

**Type**: `float`

**Default**: `0.5`

**Range**: `0.0` - `1.0`

**Example**:
```bash
export VAD_THRESHOLD=0.5
```

#### `min_speech_duration_ms`

**Environment Variable**: `MIN_SPEECH_DURATION_MS`

**Type**: `int`

**Default**: `300`

**Range**: `100` - `1000`

**Impact**:
- Shorter = more sensitive (false positives)
- Longer = less sensitive (misses short utterances)

**Example**:
```bash
export MIN_SPEECH_DURATION_MS=300
```

#### `silence_duration_ms`

**Environment Variable**: `SILENCE_DURATION_MS`

**Type**: `int`

**Default**: `700`

**Range**: `300` - `2000`

**Impact**:
- Shorter = faster turn detection (may interrupt)
- Longer = slower turn detection (awkward pauses)

**Example**:
```bash
export SILENCE_DURATION_MS=700
```

### Conversation Behavior

#### `idle_timeout_seconds`

**Environment Variable**: `IDLE_TIMEOUT_SECONDS`

**Type**: `int`

**Default**: `120`

**Purpose**: Seconds before auto-transitioning to CLOSING phase

**Example**:
```bash
export IDLE_TIMEOUT_SECONDS=120
```

#### `enable_interruptions`

**Environment Variable**: `ENABLE_INTERRUPTIONS`

**Type**: `bool`

**Default**: `true`

**Purpose**: Allow user to interrupt agent speech

**Example**:
```bash
export ENABLE_INTERRUPTIONS=true
```

#### `fallback_response`

**Environment Variable**: `FALLBACK_RESPONSE`

**Type**: `str`

**Default**: `"I'm having trouble right now. Please try again."`

**Purpose**: Response when LLM API fails

**Example**:
```bash
export FALLBACK_RESPONSE="I'm having trouble right now. Please try again."
```

---

## Environment Variables

### Quick Reference

```bash
# ===== REQUIRED =====
LIVEKIT_URL=ws://localhost:7880
LIVEKIT_API_KEY=devkey
LIVEKIT_API_SECRET=secret

# ===== OPTIONAL: Logging =====
LOG_LEVEL=INFO                          # DEBUG, INFO, WARNING, ERROR
LOG_FORMAT=json                         # json, text
HEALTH_CHECK_PORT=8080

# ===== OPTIONAL: Voice (STT/TTS) =====
DEEPGRAM_API_KEY=...
DEEPGRAM_MODEL=nova-2
DEEPGRAM_LANGUAGE=en-US
CARTESIA_API_KEY=...
CARTESIA_VOICE_ID=default-sonic-voice
CARTESIA_SPEED=1.0
CARTESIA_EMOTION=neutral
VOICE_SAMPLE_RATE=16000
VOICE_CHANNELS=1
VOICE_LATENCY_TARGET=500
VAD_THRESHOLD=0.5

# ===== OPTIONAL: Conversation (LLM) =====
LLM_PROVIDER=openai                    # openai or anthropic
LLM_API_KEY=sk-...                     # or OPENAI_API_KEY, ANTHROPIC_API_KEY
LLM_MODEL=gpt-4
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=150
CONVERSATION_MAX_HISTORY=20
MIN_SPEECH_DURATION_MS=300
SILENCE_DURATION_MS=700
IDLE_TIMEOUT_SECONDS=120
ENABLE_INTERRUPTIONS=true
FALLBACK_RESPONSE="I'm having trouble right now. Please try again."
```

---

## Configuration Loading

### Programmatic Loading

```python
from nora_livekit.config import Config

# Load from environment
config = Config.from_env()

# Access fields
print(config.livekit_url)
print(config.conversation.llm_model if config.conversation else None)
```

### Environment File

Create `.env` file:
```
# .env
LIVEKIT_URL=ws://localhost:7880
LIVEKIT_API_KEY=devkey
LIVEKIT_API_SECRET=secret
LOG_LEVEL=INFO
DEEPGRAM_API_KEY=your-key
OPENAI_API_KEY=sk-...
LLM_MODEL=gpt-4
CONVERSATION_MAX_HISTORY=20
```

Load in Python:
```python
from dotenv import load_dotenv
load_dotenv()

config = Config.from_env()
```

### Docker Environment

In `Dockerfile`:
```dockerfile
ENV LIVEKIT_URL=ws://livekit:7880
ENV LIVEKIT_API_KEY=devkey
ENV LIVEKIT_API_SECRET=secret
ENV LOG_LEVEL=INFO
```

Or in `docker-compose.yml`:
```yaml
services:
  agent:
    image: nora-livekit:latest
    environment:
      LIVEKIT_URL: ws://livekit:7880
      LIVEKIT_API_KEY: devkey
      LIVEKIT_API_SECRET: secret
      OPENAI_API_KEY: ${OPENAI_API_KEY}
      LOG_LEVEL: INFO
```

---

## Configuration Examples

### Minimal Configuration (No Conversation Engine)

```bash
# .env
LIVEKIT_URL=ws://localhost:7880
LIVEKIT_API_KEY=devkey
LIVEKIT_API_SECRET=secret
```

**Result**: VoicePipeline with echo fallback, no LLM

### Standard Configuration (OpenAI + Voice)

```bash
# .env
LIVEKIT_URL=ws://localhost:7880
LIVEKIT_API_KEY=devkey
LIVEKIT_API_SECRET=secret
LOG_LEVEL=INFO

# Voice (STT/TTS)
DEEPGRAM_API_KEY=your-deepgram-key
DEEPGRAM_MODEL=nova-2
CARTESIA_API_KEY=your-cartesia-key

# Conversation (LLM)
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
LLM_MODEL=gpt-4
LLM_TEMPERATURE=0.7
CONVERSATION_MAX_HISTORY=20
```

**Result**: Full voice conversation with GPT-4

### Cost-Optimized Configuration

```bash
# Use cheaper models and shorter history
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
LLM_MODEL=gpt-3.5-turbo           # 10x cheaper than gpt-4
LLM_TEMPERATURE=0.5               # More predictable
LLM_MAX_TOKENS=100                # Shorter responses
CONVERSATION_MAX_HISTORY=10       # Smaller context
```

**Impact**: ~70% cost reduction vs. standard config

### Premium Configuration (Claude + Extended History)

```bash
# Use best model with extended context
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
LLM_MODEL=claude-3-opus-20240229  # Most capable
LLM_TEMPERATURE=0.8               # More creative
LLM_MAX_TOKENS=200                # Longer responses
CONVERSATION_MAX_HISTORY=30       # Extended context
```

**Result**: Highest quality conversations, highest cost

### Debug Configuration

```bash
# Enable detailed logging
LOG_LEVEL=DEBUG
LOG_FORMAT=text                   # Human-readable logs
VAD_THRESHOLD=0.5
MIN_SPEECH_DURATION_MS=300
SILENCE_DURATION_MS=700
```

---

## Validation & Errors

### Required Field Validation

```python
# This raises ValueError
config = Config.from_env()  # Missing LIVEKIT_URL

# Error: Missing required environment variable: LIVEKIT_URL
```

### Optional Component Validation

```python
config = Config.from_env()

# Check if conversation engine is configured
if config.conversation:
    # Conversation engine is available
    llm_model = config.conversation.llm_model
else:
    # Conversation engine disabled
    logger.warning("Conversation engine not configured")
```

### Value Range Validation

```python
# Invalid temperature (outside 0.0-2.0 range)
# Python doesn't enforce at construction, but API will reject

# Invalid language code
# Deepgram will reject unsupported language codes

# Invalid max_tokens for model
# OpenAI will reject if > model limit (e.g., 4096 for gpt-3.5-turbo)
```

### Common Configuration Errors

| Error | Cause | Solution |
|-------|-------|----------|
| "Missing required environment variable: LIVEKIT_URL" | LIVEKIT_URL not set | `export LIVEKIT_URL=...` |
| "Conversation engine not configured" | LLM_API_KEY not set | `export OPENAI_API_KEY=...` |
| "Invalid API key" | Wrong key format or expired | Generate new API key |
| "Model not found: gpt-5" | Invalid model name | Use valid model names |
| "Rate limit exceeded" | Too many API calls | Increase idle_timeout_seconds |

---

## Performance Tuning

### For Faster Responses

```bash
# Reduce LLM max tokens
LLM_MAX_TOKENS=50

# Use smaller model
LLM_MODEL=gpt-3.5-turbo

# Reduce history window
CONVERSATION_MAX_HISTORY=10

# Faster turn detection
SILENCE_DURATION_MS=500
```

### For Better Quality

```bash
# Increase LLM max tokens
LLM_MAX_TOKENS=200

# Use larger model
LLM_MODEL=gpt-4

# Larger history for context
CONVERSATION_MAX_HISTORY=30

# More careful turn detection
SILENCE_DURATION_MS=1000
```

### For Lower Costs

```bash
# Use cheapest model
LLM_MODEL=gpt-3.5-turbo

# Reduce max tokens
LLM_MAX_TOKENS=100

# Smaller history
CONVERSATION_MAX_HISTORY=10

# Use fewer messages
IDLE_TIMEOUT_SECONDS=60
```

---

## Related Documentation

- [Conversation Engine Guide](./CONVERSATION_ENGINE.md)
- [API Reference](./CONVERSATION_API.md)
- [Integration Guide](./CONVERSATION_INTEGRATION.md)

---

**Version**: 1.0.0
**Last Updated**: 2025-11-25
