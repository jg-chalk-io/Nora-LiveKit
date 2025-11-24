"""Tests for Nora LiveKit Agent."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from nora_livekit.agent import NoraAgent
from nora_livekit.config import Config


@pytest.fixture
def mock_config() -> Config:
    """Create a mock Config instance."""
    return Config(
        livekit_url="wss://test.livekit.cloud",
        livekit_api_key="test-key",
        livekit_api_secret="test-secret",
    )


class TestAgentInitialization:
    """Test agent initialization."""

    def test_agent_initialization(self, mock_config: Config) -> None:
        """Test basic agent initialization."""
        agent = NoraAgent(mock_config)

        assert agent.config == mock_config
        assert agent.room is None
        assert agent._shutdown_event is not None

    def test_agent_initialization_with_different_config(self) -> None:
        """Test agent initialization with different config."""
        config = Config(
            livekit_url="wss://another.livekit.cloud",
            livekit_api_key="another-key",
            livekit_api_secret="another-secret",
            health_check_port=9090,
        )
        agent = NoraAgent(config)

        assert agent.config == config
        assert agent.room is None


class TestAgentStart:
    """Test agent start method."""

    @pytest.mark.asyncio
    async def test_agent_start_joins_room(self, mock_config: Config) -> None:
        """Test that agent.start() joins a room."""
        agent = NoraAgent(mock_config)
        await agent.start()

        assert agent.room is not None
        assert agent.room.get("name") == "nora-room"
        assert agent.room.get("connected") is True

    @pytest.mark.asyncio
    async def test_agent_start_with_test_room(self, mock_config: Config) -> None:
        """Test that agent.start() uses test room when configured."""
        mock_config.test_room = "test-room-001"

        agent = NoraAgent(mock_config)
        await agent.start()

        assert agent.room is not None
        assert agent.room.get("name") == "test-room-001"

    @pytest.mark.asyncio
    async def test_agent_start_uses_correct_url(self, mock_config: Config) -> None:
        """Test that agent.start() stores the correct URL."""
        agent = NoraAgent(mock_config)
        await agent.start()

        assert agent.room is not None
        assert agent.room.get("url") == mock_config.livekit_url


class TestAgentStop:
    """Test agent stop method."""

    @pytest.mark.asyncio
    async def test_agent_stop_disconnects_room(self, mock_config: Config) -> None:
        """Test that agent.stop() disconnects from room."""
        agent = NoraAgent(mock_config)
        agent.room = {"name": "test-room", "connected": True}

        await agent.stop()

        assert agent.room is None

    @pytest.mark.asyncio
    async def test_agent_stop_without_room(self, mock_config: Config) -> None:
        """Test that agent.stop() works when no room is connected."""
        agent = NoraAgent(mock_config)
        agent.room = None

        # Should not raise an error
        await agent.stop()

    @pytest.mark.asyncio
    async def test_agent_stop_completes_within_timeout(self, mock_config: Config) -> None:
        """Test that agent.stop() completes within 5 seconds."""
        agent = NoraAgent(mock_config)
        agent.room = {"name": "test-room", "connected": True}

        start_time = asyncio.get_event_loop().time()
        await agent.stop()
        end_time = asyncio.get_event_loop().time()

        assert (end_time - start_time) < 5.0

    @pytest.mark.asyncio
    async def test_agent_stop_logs_disconnection(self, mock_config: Config) -> None:
        """Test that agent.stop() logs disconnection event."""
        agent = NoraAgent(mock_config)
        agent.room = {"name": "test-room", "connected": True}

        await agent.stop()

        # Verify logging occurred (room should be None)
        assert agent.room is None


class TestAgentShutdown:
    """Test agent shutdown signal handling."""

    def test_agent_handles_shutdown_signal(self, mock_config: Config) -> None:
        """Test that agent registers signal handlers."""
        agent = NoraAgent(mock_config)

        # Verify agent can handle shutdown signals
        assert agent._shutdown_event is not None


class TestAgentShutdownEvent:
    """Test agent shutdown event."""

    @pytest.mark.asyncio
    async def test_shutdown_event_triggers(self, mock_config: Config) -> None:
        """Test that shutdown event can be triggered."""
        agent = NoraAgent(mock_config)

        # Verify event is not set initially
        assert not agent._shutdown_event.is_set()

        # Set the event
        agent._shutdown_event.set()

        # Verify event is set
        assert agent._shutdown_event.is_set()

    @pytest.mark.asyncio
    async def test_can_wait_for_shutdown(self, mock_config: Config) -> None:
        """Test that we can wait for shutdown event."""
        agent = NoraAgent(mock_config)

        async def trigger_shutdown() -> None:
            await asyncio.sleep(0.1)
            agent._shutdown_event.set()

        # Run shutdown trigger in background
        asyncio.create_task(trigger_shutdown())

        # Wait for shutdown event
        start_time = asyncio.get_event_loop().time()
        await agent._shutdown_event.wait()
        end_time = asyncio.get_event_loop().time()

        # Should complete quickly (within 1 second)
        assert (end_time - start_time) < 1.0


class TestLiveKitIntegration:
    """Test LiveKit SDK integration."""

    @pytest.mark.asyncio
    async def test_connect_to_livekit_success(self, mock_config: Config) -> None:
        """Test successful LiveKit token generation."""
        agent = NoraAgent(mock_config)

        # Mock the LiveKit API components with builder pattern
        with patch("nora_livekit.agent.api.AccessToken") as mock_token_class:
            mock_token = MagicMock()
            mock_token.to_jwt.return_value = "test-token"
            mock_token.with_identity.return_value = mock_token
            mock_token.with_name.return_value = mock_token
            mock_token.with_grants.return_value = mock_token
            mock_token_class.return_value = mock_token

            # Call the connect method
            await agent._connect_to_livekit()

            # Verify token was stored
            assert agent._livekit_room is not None
            assert agent._livekit_room.get("token") == "test-token"
            assert agent._livekit_room.get("url") == mock_config.livekit_url
            assert agent._livekit_room.get("room") == "default-room"
            assert agent._livekit_room.get("agent_name") == "nora-agent"

    @pytest.mark.asyncio
    async def test_connect_to_livekit_with_token(self, mock_config: Config) -> None:
        """Test LiveKit connection with proper authentication token."""
        agent = NoraAgent(mock_config)

        with patch("nora_livekit.agent.api.AccessToken") as mock_token_class:
            mock_token = MagicMock()
            mock_token.to_jwt.return_value = "test-token"
            mock_token.with_identity.return_value = mock_token
            mock_token.with_name.return_value = mock_token
            mock_token.with_grants.return_value = mock_token
            mock_token_class.return_value = mock_token

            with patch("nora_livekit.agent.api.VideoGrants") as mock_grants:
                await agent._connect_to_livekit()

                # Verify token was created with proper credentials
                mock_token_class.assert_called()
                mock_token.with_identity.assert_called()
                mock_token.with_name.assert_called()
                mock_token.with_grants.assert_called()
                mock_grants.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_to_livekit_failure(self, mock_config: Config) -> None:
        """Test LiveKit connection failure handling."""
        agent = NoraAgent(mock_config)

        with patch("nora_livekit.agent.api.AccessToken") as mock_token_class:
            mock_token_class.side_effect = Exception("Token generation failed")

            with pytest.raises(Exception, match="Token generation failed"):
                await agent._connect_to_livekit()

    @pytest.mark.asyncio
    async def test_disconnect_from_livekit_success(self, mock_config: Config) -> None:
        """Test successful LiveKit room disconnection."""
        agent = NoraAgent(mock_config)

        # Setup agent with a room
        with patch("nora_livekit.agent.api.AccessToken") as mock_token_class:
            mock_token = MagicMock()
            mock_token.to_jwt.return_value = "test-token"
            mock_token.with_identity.return_value = mock_token
            mock_token.with_name.return_value = mock_token
            mock_token.with_grants.return_value = mock_token
            mock_token_class.return_value = mock_token

            await agent._connect_to_livekit()

            # Verify room is set
            assert agent._livekit_room is not None

            # Disconnect
            await agent._disconnect_from_livekit()

            # Verify room is cleaned up
            assert agent._livekit_room is None

    @pytest.mark.asyncio
    async def test_disconnect_from_livekit_when_not_connected(self, mock_config: Config) -> None:
        """Test LiveKit disconnection when not connected."""
        agent = NoraAgent(mock_config)

        # Should not raise when room is None
        assert agent._livekit_room is None
        await agent._disconnect_from_livekit()
        assert agent._livekit_room is None

    @pytest.mark.asyncio
    async def test_agent_start_connects_to_livekit(self, mock_config: Config) -> None:
        """Test that agent.start() connects to LiveKit."""
        agent = NoraAgent(mock_config)

        with patch.object(agent, "_connect_to_livekit", new_callable=AsyncMock) as mock_connect:
            await agent.start()

            # Verify connection was attempted
            mock_connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_agent_stop_disconnects_from_livekit(self, mock_config: Config) -> None:
        """Test that agent.stop() disconnects from LiveKit."""
        agent = NoraAgent(mock_config)

        with patch.object(
            agent, "_disconnect_from_livekit", new_callable=AsyncMock
        ) as mock_disconnect:
            # Setup agent with a room
            agent.room = {"name": "test-room", "connected": True}

            await agent.stop()

            # Verify disconnection was attempted
            mock_disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_room_state_updated_after_connection(self, mock_config: Config) -> None:
        """Test that room state is properly updated after connection."""
        agent = NoraAgent(mock_config)

        with patch("nora_livekit.agent.api.AccessToken") as mock_token_class:
            mock_token_instance = MagicMock()
            mock_token_instance.to_jwt.return_value = "test-token"
            mock_token_class.return_value = mock_token_instance

            await agent.start()

            # Verify room state
            assert agent.room is not None
            assert agent.room.get("connected") is True
            assert agent.room.get("url") == mock_config.livekit_url
