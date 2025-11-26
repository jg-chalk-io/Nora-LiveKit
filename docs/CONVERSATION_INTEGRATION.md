---
id: conversation-integration-guide
title: Conversation Engine Integration Guide
description: Step-by-step integration guide for adding ConversationEngine to LiveKit agents
author: GOOS
created: 2025-11-25
updated: 2025-11-25
version: 1.0.0
---

# Conversation Engine Integration Guide

## Table of Contents

1. [Overview](#overview)
2. [Integration Steps](#integration-steps)
3. [LiveKit Room Events](#livekit-room-events)
4. [VoicePipeline Integration](#voicepipeline-integration)
5. [Configuration Integration](#configuration-integration)
6. [Agent Initialization](#agent-initialization)
7. [End-to-End Example](#end-to-end-example)
8. [Testing Integration](#testing-integration)

---

## Overview

The Conversation Engine integrates into Nora-LiveKit at three key points:

1. **VoicePipeline**: Delegates response generation to ConversationEngine
2. **LiveKit Room Events**: Tracks participant join/leave
3. **Configuration System**: Loads LLM settings from environment

This guide walks through each integration point.

---

## Integration Steps

### Step 1: Install Dependencies

```bash
# Add conversation engine dependencies
pip install openai anthropic tenacity

# Or with poetry
poetry add openai anthropic tenacity
```

**Verify installation**:
```python
import openai
import anthropic
print(f"OpenAI: {openai.__version__}")
print(f"Anthropic: {anthropic.__version__}")
```

### Step 2: Configure LLM Provider

Set environment variables:

```bash
# Choose provider
export LLM_PROVIDER=openai  # or "anthropic"
export LLM_API_KEY=sk-...

# Or set provider-specific
export OPENAI_API_KEY=sk-...
export ANTHROPIC_API_KEY=sk-ant-...

# Optional: tune settings
export LLM_MODEL=gpt-4
export LLM_TEMPERATURE=0.7
export LLM_MAX_TOKENS=150
```

Or create `.env` file:
```
LLM_PROVIDER=openai
LLM_API_KEY=sk-...
LLM_MODEL=gpt-4
LLM_TEMPERATURE=0.7
CONVERSATION_MAX_HISTORY=20
```

### Step 3: Initialize Conversation Engine

In your agent initialization code:

```python
from nora_livekit.config import Config
from nora_livekit.conversation import (
    ConversationEngine, ConversationContext, LLMIntegration,
    TurnManager, ConversationEngineConfig, LLMProvider
)

async def initialize_agent():
    # Load configuration from environment
    config = Config.from_env()

    # Create conversation engine if LLM is configured
    conversation_engine = None
    if config.conversation:
        llm_provider = (
            LLMProvider.OPENAI
            if config.conversation.llm_provider == "openai"
            else LLMProvider.ANTHROPIC
        )

        conversation_engine = ConversationEngine(
            config=ConversationEngineConfig(
                max_history=config.conversation.max_history,
                idle_timeout_seconds=config.conversation.idle_timeout_seconds,
                enable_interruptions=config.conversation.enable_interruptions,
                fallback_response=config.conversation.fallback_response
            ),
            context=ConversationContext(max_history=config.conversation.max_history),
            llm=LLMIntegration(
                provider=llm_provider,
                api_key=config.conversation.llm_api_key,
                model=config.conversation.llm_model,
                temperature=config.conversation.llm_temperature,
                max_tokens=config.conversation.llm_max_tokens
            ),
            turn_manager=TurnManager(
                vad_threshold=config.conversation.vad_threshold,
                min_speech_duration_ms=config.conversation.min_speech_duration_ms,
                silence_duration_ms=config.conversation.silence_duration_ms
            )
        )

        # Start conversation engine
        await conversation_engine.start()
        logger.info("Conversation engine initialized")
    else:
        logger.warning("Conversation engine not configured, using fallback mode")

    return conversation_engine
```

---

## LiveKit Room Events

### Handling Participant Join

In your LiveKit agent class:

```python
from livekit.agents import WorkerOptions, VoiceAssistantOptions, llm
from livekit import agents
from livekit.agents import EventFilter, EventFilterOptions

@room.event.on("participant_connected")
async def on_participant_connected(participant: agents.Participant):
    """Handle new participant joining the room."""
    logger.info(f"Participant joined: {participant.name} ({participant.sid})")

    if self.conversation_engine:
        # Add participant to conversation engine
        self.conversation_engine.participant_manager.add_participant(
            participant_id=participant.sid,
            name=participant.name or f"participant-{participant.sid[:8]}"
        )
        logger.debug(f"Added to conversation engine: {participant.name}")
```

### Handling Participant Leave

```python
@room.event.on("participant_disconnected")
async def on_participant_disconnected(participant_id: str):
    """Handle participant leaving the room."""
    logger.info(f"Participant left: {participant_id}")

    if self.conversation_engine:
        # Remove from conversation engine
        self.conversation_engine.participant_manager.remove_participant(participant_id)
        logger.debug(f"Removed from conversation engine: {participant_id}")
```

### Full LiveKit Integration Example

```python
class NoraLiveKitAgent:
    def __init__(self, room: agents.VirtualRoom):
        self.room = room
        self.conversation_engine = None

    async def setup(self):
        """Setup agent with conversation engine."""
        # Initialize conversation engine
        self.conversation_engine = await initialize_conversation_engine()

        # Register room event handlers
        self.room.on_participant_connected(self._on_participant_connected)
        self.room.on_participant_disconnected(self._on_participant_disconnected)

    async def _on_participant_connected(self, participant: agents.Participant):
        """Handle participant join."""
        if self.conversation_engine:
            self.conversation_engine.participant_manager.add_participant(
                participant_id=participant.sid,
                name=participant.name
            )

    async def _on_participant_disconnected(self, participant_id: str):
        """Handle participant leave."""
        if self.conversation_engine:
            self.conversation_engine.participant_manager.remove_participant(
                participant_id
            )

    async def teardown(self):
        """Cleanup on shutdown."""
        if self.conversation_engine:
            await self.conversation_engine.stop()
```

---

## VoicePipeline Integration

### Modify Pipeline Constructor

In `src/nora_livekit/voice/pipeline.py`:

```python
from typing import Optional, Any
from nora_livekit.conversation import ConversationEngine

class VoicePipeline:
    def __init__(
        self,
        config: Config,
        stt: DeepgramSTT,
        tts: CartesiaTTS,
        audio_handler: AudioHandler,
        conversation_engine: Optional[ConversationEngine] = None,  # NEW
    ) -> None:
        """Initialize voice pipeline with optional conversation engine.

        Args:
            config: Configuration instance
            stt: Speech-to-text engine
            tts: Text-to-speech engine
            audio_handler: Audio handler
            conversation_engine: Optional ConversationEngine for SPEC-003
        """
        self.config = config
        self.stt = stt
        self.tts = tts
        self.audio_handler = audio_handler
        self.conversation_engine = conversation_engine  # NEW
        self._running = False
```

### Modify Response Generation

In `_generate_response()` method:

```python
async def _generate_response(
    self,
    text: str,
    participant_id: str = "",
) -> str:
    """Generate response using ConversationEngine.

    Args:
        text: Transcribed user text
        participant_id: ID of speaking participant

    Returns:
        Response text for TTS synthesis
    """
    if self.conversation_engine:
        # Use conversation engine (SPEC-003)
        try:
            response = await self.conversation_engine.process_transcription(
                text=text,
                participant_id=participant_id or "default",
            )
            return response
        except Exception as e:
            logger.error("Conversation engine error", error=str(e))
            # Fall back to simple echo
            return f"You said: {text}"
    else:
        # Fallback to echo (for testing without conversation engine)
        return f"You said: {text}"
```

### Integration with Transcription Handler

```python
async def _handle_transcription(
    self,
    text: str,
    participant_id: str = ""
) -> None:
    """Handle transcribed text from STT.

    Args:
        text: Transcribed text
        participant_id: ID of speaking participant
    """
    logger.info("voice.stt.transcription", text=text, participant_id=participant_id)

    try:
        # Generate response (uses conversation engine if available)
        response_text = await self._generate_response(text, participant_id)

        # Synthesize with TTS
        async for audio_chunk in self.tts.synthesize(response_text):
            # Buffer and prepare audio for publishing to LiveKit
            await self.audio_handler.publish_audio(audio_chunk)

        logger.info("voice.audio.published")

    except Exception as e:
        logger.error("voice.pipeline.transcription_error", error=str(e))
```

---

## Configuration Integration

### Config Class Extension

In `src/nora_livekit/config.py`:

```python
from dataclasses import dataclass
from typing import Optional
from nora_livekit.conversation import ConversationConfig

@dataclass
class Config:
    """Main configuration for Nora LiveKit agent."""

    livekit_url: str
    livekit_api_key: str
    livekit_api_secret: str
    health_check_port: int = 8080
    log_level: str = "INFO"
    log_format: str = "json"
    test_room: Optional[str] = None
    voice: Optional[VoiceConfig] = None
    conversation: Optional[ConversationConfig] = None  # NEW

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""

        # ... existing LiveKit and voice configuration ...

        # Load conversation configuration if LLM API key is present
        conversation_config = None
        llm_api_key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")

        if llm_api_key:
            llm_provider = os.getenv("LLM_PROVIDER", "openai")

            conversation_config = ConversationConfig(
                llm_provider=llm_provider,
                llm_api_key=llm_api_key,
                llm_model=os.getenv(
                    "LLM_MODEL",
                    "gpt-4" if llm_provider == "openai"
                    else "claude-3-sonnet-20240229"
                ),
                llm_temperature=float(os.getenv("LLM_TEMPERATURE", "0.7")),
                llm_max_tokens=int(os.getenv("LLM_MAX_TOKENS", "150")),
                max_history=int(os.getenv("CONVERSATION_MAX_HISTORY", "20")),
                vad_threshold=float(os.getenv("VAD_THRESHOLD", "0.5")),
                min_speech_duration_ms=int(
                    os.getenv("MIN_SPEECH_DURATION_MS", "300")
                ),
                silence_duration_ms=int(
                    os.getenv("SILENCE_DURATION_MS", "700")
                ),
                idle_timeout_seconds=int(
                    os.getenv("IDLE_TIMEOUT_SECONDS", "120")
                ),
                enable_interruptions=os.getenv(
                    "ENABLE_INTERRUPTIONS", "true"
                ).lower() == "true",
                fallback_response=os.getenv(
                    "FALLBACK_RESPONSE",
                    "I'm having trouble right now. Please try again."
                ),
            )

        return cls(
            livekit_url=livekit_url,
            livekit_api_key=livekit_api_key,
            livekit_api_secret=livekit_api_secret,
            health_check_port=health_check_port,
            log_level=log_level,
            log_format=log_format,
            test_room=test_room,
            voice=voice_config,
            conversation=conversation_config,  # NEW
        )
```

---

## Agent Initialization

### Complete Agent Setup

```python
import asyncio
from livekit.agents import VirtualRoom, WorkerOptions, VoiceAssistantOptions
from nora_livekit.config import Config, setup_logging
from nora_livekit.conversation import ConversationEngine, ConversationContext, \
    LLMIntegration, TurnManager, ConversationEngineConfig, LLMProvider
from nora_livekit.voice.pipeline import VoicePipeline
import structlog

logger = structlog.get_logger(__name__)

class NoraLiveKitAgent:
    """Nora LiveKit AI Voice Agent with Conversation Engine."""

    def __init__(self):
        self.config = None
        self.voice_pipeline = None
        self.conversation_engine = None

    async def initialize(self):
        """Initialize agent components."""
        # Load configuration
        self.config = Config.from_env()
        setup_logging(self.config)

        logger.info("initializing_agent", config=self.config)

        # Initialize conversation engine if configured
        if self.config.conversation:
            await self._initialize_conversation_engine()
        else:
            logger.warning("conversation_engine_not_configured")

        # Initialize voice pipeline
        if self.config.voice:
            await self._initialize_voice_pipeline()

    async def _initialize_conversation_engine(self):
        """Initialize conversation engine with LLM."""
        try:
            llm_provider = (
                LLMProvider.OPENAI
                if self.config.conversation.llm_provider == "openai"
                else LLMProvider.ANTHROPIC
            )

            self.conversation_engine = ConversationEngine(
                config=ConversationEngineConfig(
                    max_history=self.config.conversation.max_history,
                    idle_timeout_seconds=self.config.conversation.idle_timeout_seconds,
                    enable_interruptions=self.config.conversation.enable_interruptions,
                    fallback_response=self.config.conversation.fallback_response
                ),
                context=ConversationContext(
                    max_history=self.config.conversation.max_history
                ),
                llm=LLMIntegration(
                    provider=llm_provider,
                    api_key=self.config.conversation.llm_api_key,
                    model=self.config.conversation.llm_model,
                    temperature=self.config.conversation.llm_temperature,
                    max_tokens=self.config.conversation.llm_max_tokens
                ),
                turn_manager=TurnManager(
                    vad_threshold=self.config.conversation.vad_threshold,
                    min_speech_duration_ms=self.config.conversation.min_speech_duration_ms,
                    silence_duration_ms=self.config.conversation.silence_duration_ms
                )
            )

            await self.conversation_engine.start()
            logger.info("conversation_engine_started")

        except Exception as e:
            logger.error("conversation_engine_initialization_failed", error=str(e))
            self.conversation_engine = None

    async def _initialize_voice_pipeline(self):
        """Initialize voice pipeline with conversation engine."""
        # Initialize STT, TTS, audio handler...
        stt = await initialize_stt(self.config.voice)
        tts = await initialize_tts(self.config.voice)
        audio_handler = await initialize_audio_handler(self.config.voice)

        self.voice_pipeline = VoicePipeline(
            config=self.config,
            stt=stt,
            tts=tts,
            audio_handler=audio_handler,
            conversation_engine=self.conversation_engine  # Pass engine
        )

        await self.voice_pipeline.start()
        logger.info("voice_pipeline_started")

    async def shutdown(self):
        """Shutdown agent and cleanup."""
        if self.voice_pipeline:
            await self.voice_pipeline.stop()

        if self.conversation_engine:
            await self.conversation_engine.stop()

        logger.info("agent_shutdown_complete")


async def main():
    """Main entry point."""
    agent = NoraLiveKitAgent()
    try:
        await agent.initialize()

        # Keep agent running
        await asyncio.Event().wait()

    except KeyboardInterrupt:
        logger.info("shutdown_requested")
    finally:
        await agent.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
```

---

## End-to-End Example

### Complete Integration Flow

```python
# 1. Initialize config from environment
config = Config.from_env()

# 2. Initialize conversation engine
if config.conversation:
    conversation_engine = ConversationEngine(
        config=ConversationEngineConfig(...),
        context=ConversationContext(...),
        llm=LLMIntegration(...),
        turn_manager=TurnManager(...)
    )
    await conversation_engine.start()

# 3. Initialize voice pipeline with conversation engine
voice_pipeline = VoicePipeline(
    config=config,
    stt=deepgram_stt,
    tts=cartesia_tts,
    audio_handler=audio_handler,
    conversation_engine=conversation_engine  # Pass here
)
await voice_pipeline.start()

# 4. Handle LiveKit events
@room.event.on("participant_connected")
async def on_join(participant):
    if conversation_engine:
        conversation_engine.participant_manager.add_participant(
            participant.sid, participant.name
        )

@room.event.on("participant_disconnected")
async def on_leave(participant_id):
    if conversation_engine:
        conversation_engine.participant_manager.remove_participant(participant_id)

# 5. Processing flow
# User speaks → STT → voice_pipeline._handle_transcription()
# → conversation_engine.process_transcription()
# → LLM generates response
# → TTS synthesizes → audio published to LiveKit
```

---

## Testing Integration

### Unit Test: Conversation Engine Integration

```python
import pytest
from nora_livekit.conversation import ConversationEngine, ConversationContext, \
    LLMIntegration, TurnManager, ConversationEngineConfig, LLMProvider
from nora_livekit.voice.pipeline import VoicePipeline
from unittest.mock import Mock, AsyncMock

@pytest.mark.asyncio
async def test_voice_pipeline_with_conversation_engine():
    """Test VoicePipeline integration with ConversationEngine."""

    # Setup
    config = Mock()
    stt = Mock()
    tts = Mock()
    audio_handler = Mock()

    # Create conversation engine mock
    conversation_engine = AsyncMock(spec=ConversationEngine)
    conversation_engine.process_transcription = AsyncMock(
        return_value="Hello! How can I help?"
    )

    # Create pipeline with conversation engine
    pipeline = VoicePipeline(
        config=config,
        stt=stt,
        tts=tts,
        audio_handler=audio_handler,
        conversation_engine=conversation_engine
    )

    # Test response generation
    response = await pipeline._generate_response(
        text="What time is it?",
        participant_id="user-123"
    )

    # Verify conversation engine was called
    conversation_engine.process_transcription.assert_called_once_with(
        text="What time is it?",
        participant_id="user-123"
    )

    assert response == "Hello! How can I help?"

@pytest.mark.asyncio
async def test_voice_pipeline_fallback_without_conversation_engine():
    """Test VoicePipeline fallback when conversation engine is None."""

    # Setup without conversation engine
    config = Mock()
    stt = Mock()
    tts = Mock()
    audio_handler = Mock()

    pipeline = VoicePipeline(
        config=config,
        stt=stt,
        tts=tts,
        audio_handler=audio_handler,
        conversation_engine=None  # No engine
    )

    # Test fallback response
    response = await pipeline._generate_response(
        text="What time is it?",
        participant_id="user-123"
    )

    assert "You said:" in response
    assert "What time is it?" in response
```

### Integration Test: Full Conversation Flow

```python
@pytest.mark.asyncio
async def test_full_conversation_with_voice_pipeline():
    """Test complete conversation flow with voice pipeline."""

    # Initialize components
    config = Config.from_env()
    conversation_engine = await initialize_conversation_engine(config)
    voice_pipeline = VoicePipeline(
        config=config,
        stt=deepgram_stt,
        tts=cartesia_tts,
        audio_handler=audio_handler,
        conversation_engine=conversation_engine
    )

    try:
        # Start pipeline
        await voice_pipeline.start()

        # Simulate user input
        response = await voice_pipeline._generate_response(
            text="Hello",
            participant_id="test-user"
        )

        # Verify response
        assert response
        assert len(response) > 0

        # Check conversation context
        history = conversation_engine.context.get_history()
        assert any(msg.content == "Hello" for msg in history)

    finally:
        await voice_pipeline.stop()
        await conversation_engine.stop()
```

---

## Troubleshooting Integration

### Issue: "conversation_engine is None in VoicePipeline"

**Cause**: LLM_API_KEY environment variable not set

**Solution**:
```bash
export LLM_API_KEY=sk-...
export LLM_PROVIDER=openai
```

### Issue: "Participant not found in conversation_engine"

**Cause**: Room event handler not called or participant already removed

**Solution**:
```python
# Verify event handler is registered
logger.info(f"Participants: {[p.participant_id for p in engine.participant_manager.get_active_participants()]}")

# Check if room events are firing
@room.event.on("participant_connected")
async def on_join(participant):
    logger.info(f"Event fired for: {participant.sid}")  # Debug log
```

### Issue: "LLM response not being used"

**Cause**: Conversation engine not passed to VoicePipeline

**Solution**:
```python
# Make sure engine is passed
pipeline = VoicePipeline(
    config=config,
    stt=stt,
    tts=tts,
    audio_handler=audio_handler,
    conversation_engine=conversation_engine  # Must pass here!
)
```

---

## Related Documentation

- [Conversation Engine Guide](./CONVERSATION_ENGINE.md)
- [API Reference](./CONVERSATION_API.md)
- [Configuration Reference](./CONFIGURATION.md)
- [Architecture Overview](./ARCHITECTURE.md)

---

**Version**: 1.0.0
**Last Updated**: 2025-11-25
