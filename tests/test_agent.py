"""Tests for NoraAgent module."""

import pytest
import asyncio
from nora_livekit.config import Config
from nora_livekit.agent import NoraAgent


class TestNoraAgentInitialization:
    """Tests for NoraAgent initialization."""

    def test_nora_agent_initialization(self):
        """Test NoraAgent initializes correctly."""
        config = Config(
            livekit_url="wss://livekit.example.com",
            livekit_api_key="test-key",
            livekit_api_secret="test-secret",
        )

        agent = NoraAgent(config)

        assert agent.config is config
        assert agent.room is None
        assert agent.is_running is False

    def test_nora_agent_has_shutdown_event(self):
        """Test NoraAgent has shutdown event."""
        config = Config(
            livekit_url="wss://livekit.example.com",
            livekit_api_key="test-key",
            livekit_api_secret="test-secret",
        )

        agent = NoraAgent(config)

        assert hasattr(agent, "_shutdown_event")
        assert isinstance(agent._shutdown_event, asyncio.Event)


class TestNoraAgentLifecycle:
    """Tests for NoraAgent lifecycle."""

    @pytest.mark.asyncio
    async def test_nora_agent_start(self):
        """Test starting NoraAgent."""
        config = Config(
            livekit_url="wss://livekit.example.com",
            livekit_api_key="test-key",
            livekit_api_secret="test-secret",
        )

        agent = NoraAgent(config)

        await agent.start()

        assert agent.is_running is True

    @pytest.mark.asyncio
    async def test_nora_agent_stop(self):
        """Test stopping NoraAgent."""
        config = Config(
            livekit_url="wss://livekit.example.com",
            livekit_api_key="test-key",
            livekit_api_secret="test-secret",
        )

        agent = NoraAgent(config)

        await agent.start()
        assert agent.is_running is True

        await agent.stop()

        assert agent.is_running is False
        assert agent._shutdown_event.is_set()

    @pytest.mark.asyncio
    async def test_nora_agent_full_lifecycle(self):
        """Test full agent lifecycle."""
        config = Config(
            livekit_url="wss://livekit.example.com",
            livekit_api_key="test-key",
            livekit_api_secret="test-secret",
        )

        agent = NoraAgent(config)

        # Initial state
        assert agent.is_running is False

        # Start
        await agent.start()
        assert agent.is_running is True

        # Stop
        await agent.stop()
        assert agent.is_running is False


class TestNoraAgentEdgeCases:
    """Tests for NoraAgent edge cases."""

    @pytest.mark.asyncio
    async def test_nora_agent_stop_without_start(self):
        """Test stopping agent that was never started."""
        config = Config(
            livekit_url="wss://livekit.example.com",
            livekit_api_key="test-key",
            livekit_api_secret="test-secret",
        )

        agent = NoraAgent(config)

        # Should be safe to stop without starting
        await agent.stop()

        assert agent.is_running is False

    @pytest.mark.asyncio
    async def test_nora_agent_multiple_start_calls(self):
        """Test calling start multiple times."""
        config = Config(
            livekit_url="wss://livekit.example.com",
            livekit_api_key="test-key",
            livekit_api_secret="test-secret",
        )

        agent = NoraAgent(config)

        await agent.start()
        first_state = agent.is_running

        # Start again
        await agent.start()
        second_state = agent.is_running

        assert first_state is True
        assert second_state is True

        await agent.stop()

    @pytest.mark.asyncio
    async def test_nora_agent_multiple_stop_calls(self):
        """Test calling stop multiple times."""
        config = Config(
            livekit_url="wss://livekit.example.com",
            livekit_api_key="test-key",
            livekit_api_secret="test-secret",
        )

        agent = NoraAgent(config)

        await agent.start()
        await agent.stop()

        first_state = agent.is_running

        # Stop again
        await agent.stop()
        second_state = agent.is_running

        assert first_state is False
        assert second_state is False


class TestNoraAgentProperties:
    """Tests for NoraAgent properties."""

    def test_nora_agent_is_running_property(self):
        """Test is_running property."""
        config = Config(
            livekit_url="wss://livekit.example.com",
            livekit_api_key="test-key",
            livekit_api_secret="test-secret",
        )

        agent = NoraAgent(config)

        # Default state
        assert agent.is_running is False
        assert isinstance(agent.is_running, bool)


class TestNoraAgentVoicePipelineIntegration:
    """Tests for NoraAgent voice pipeline integration."""

    def test_agent_has_voice_pipeline_attribute(self):
        """Test agent has voice_pipeline attribute after initialization with voice config."""
        from nora_livekit.config import VoiceConfig

        config = Config(
            livekit_url="wss://livekit.example.com",
            livekit_api_key="test-key",
            livekit_api_secret="test-secret",
            voice=VoiceConfig(deepgram_api_key="dg-key", cartesia_api_key="ca-key"),
        )

        agent = NoraAgent(config)

        # Agent should be able to initialize with voice config
        assert agent.config is config
        assert agent.config.voice is not None

    def test_agent_initialization_with_voice_config(self):
        """Test agent initialization when voice config is provided."""
        from nora_livekit.config import VoiceConfig

        config = Config(
            livekit_url="wss://livekit.example.com",
            livekit_api_key="test-key",
            livekit_api_secret="test-secret",
            voice=VoiceConfig(deepgram_api_key="dg-key", cartesia_api_key="ca-key"),
        )

        agent = NoraAgent(config)

        assert agent.config.voice.deepgram_api_key == "dg-key"
        assert agent.config.voice.cartesia_api_key == "ca-key"
        assert agent.is_running is False

    @pytest.mark.asyncio
    async def test_agent_start_with_voice_config(self):
        """Test starting agent with voice configuration."""
        from nora_livekit.config import VoiceConfig

        config = Config(
            livekit_url="wss://livekit.example.com",
            livekit_api_key="test-key",
            livekit_api_secret="test-secret",
            voice=VoiceConfig(deepgram_api_key="dg-key", cartesia_api_key="ca-key"),
        )

        agent = NoraAgent(config)

        await agent.start()

        assert agent.is_running is True

    @pytest.mark.asyncio
    async def test_agent_stop_with_voice_config(self):
        """Test stopping agent with voice configuration."""
        from nora_livekit.config import VoiceConfig

        config = Config(
            livekit_url="wss://livekit.example.com",
            livekit_api_key="test-key",
            livekit_api_secret="test-secret",
            voice=VoiceConfig(deepgram_api_key="dg-key", cartesia_api_key="ca-key"),
        )

        agent = NoraAgent(config)

        await agent.start()
        assert agent.is_running is True

        await agent.stop()

        assert agent.is_running is False
        assert agent._shutdown_event.is_set()

    @pytest.mark.asyncio
    async def test_agent_full_lifecycle_with_voice(self):
        """Test full agent lifecycle with voice support."""
        from nora_livekit.config import VoiceConfig

        config = Config(
            livekit_url="wss://livekit.example.com",
            livekit_api_key="test-key",
            livekit_api_secret="test-secret",
            voice=VoiceConfig(deepgram_api_key="dg-key", cartesia_api_key="ca-key"),
        )

        agent = NoraAgent(config)

        # Initial state
        assert agent.is_running is False

        # Start
        await agent.start()
        assert agent.is_running is True

        # Verify shutdown event not set
        assert not agent._shutdown_event.is_set()

        # Stop
        await agent.stop()
        assert agent.is_running is False
        assert agent._shutdown_event.is_set()
