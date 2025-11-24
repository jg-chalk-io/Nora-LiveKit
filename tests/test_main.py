"""Tests for Nora LiveKit Agent main entry point."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from nora_livekit.__main__ import main, run_health_server
from nora_livekit.config import Config


@pytest.fixture
def mock_config() -> Config:
    """Create a mock Config instance."""
    return Config(
        livekit_url="wss://test.livekit.cloud",
        livekit_api_key="test-key",
        livekit_api_secret="test-secret",
    )


class TestRunHealthServer:
    """Test health server startup."""

    def test_health_server_starts(self, mock_config: Config) -> None:
        """Test that health server can be started."""
        with patch("nora_livekit.__main__.uvicorn.run") as mock_uvicorn:
            run_health_server(mock_config.health_check_port)

            # Verify uvicorn was called
            mock_uvicorn.assert_called_once()
            call_args = mock_uvicorn.call_args
            assert call_args[1]["port"] == mock_config.health_check_port
            assert call_args[1]["host"] == "0.0.0.0"

    def test_health_server_with_custom_port(self) -> None:
        """Test health server with custom port."""
        custom_port = 9090

        with patch("nora_livekit.__main__.uvicorn.run") as mock_uvicorn:
            run_health_server(custom_port)

            call_args = mock_uvicorn.call_args
            assert call_args[1]["port"] == custom_port


class TestMain:
    """Test main entry point."""

    @pytest.mark.asyncio
    async def test_main_orchestrates_lifecycle(self, mock_config: Config) -> None:
        """Test that main() orchestrates agent lifecycle."""
        with patch("nora_livekit.__main__.Config.from_env", return_value=mock_config):
            with patch("nora_livekit.__main__.setup_logging"):
                with patch("nora_livekit.__main__.threading.Thread") as mock_thread:
                    with patch("nora_livekit.__main__.NoraAgent") as mock_agent_class:
                        mock_agent = AsyncMock()
                        mock_agent._shutdown_event.wait = AsyncMock(return_value=None)
                        mock_agent_class.return_value = mock_agent

                        mock_thread_instance = MagicMock()
                        mock_thread.return_value = mock_thread_instance

                        await main()

                        # Verify config was loaded
                        assert mock_agent_class.called

                        # Verify agent was started
                        mock_agent.start.assert_called_once()

                        # Verify agent was stopped
                        mock_agent.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_main_starts_health_thread(self, mock_config: Config) -> None:
        """Test that main() starts health check thread."""
        with patch("nora_livekit.__main__.Config.from_env", return_value=mock_config):
            with patch("nora_livekit.__main__.setup_logging"):
                with patch("nora_livekit.__main__.threading.Thread") as mock_thread:
                    with patch("nora_livekit.__main__.NoraAgent") as mock_agent_class:
                        mock_agent = AsyncMock()
                        mock_agent._shutdown_event.wait = AsyncMock(return_value=None)
                        mock_agent_class.return_value = mock_agent

                        mock_thread_instance = MagicMock()
                        mock_thread.return_value = mock_thread_instance

                        await main()

                        # Verify thread was created with health server target
                        mock_thread.assert_called_once()
                        call_args = mock_thread.call_args
                        assert call_args[1]["daemon"] is True
                        assert call_args[1]["target"] is not None

                        # Verify thread was started
                        mock_thread_instance.start.assert_called_once()

    @pytest.mark.asyncio
    async def test_main_waits_for_shutdown(self, mock_config: Config) -> None:
        """Test that main() waits for shutdown signal."""
        with patch("nora_livekit.__main__.Config.from_env", return_value=mock_config):
            with patch("nora_livekit.__main__.setup_logging"):
                with patch("nora_livekit.__main__.threading.Thread"):
                    with patch("nora_livekit.__main__.NoraAgent") as mock_agent_class:
                        mock_agent = AsyncMock()
                        mock_wait_called = False

                        async def mock_wait() -> None:
                            nonlocal mock_wait_called
                            mock_wait_called = True

                        mock_agent._shutdown_event.wait = mock_wait
                        mock_agent_class.return_value = mock_agent

                        await main()

                        # Verify we waited for shutdown
                        assert mock_wait_called

    @pytest.mark.asyncio
    async def test_main_loads_config_from_env(self, mock_config: Config) -> None:
        """Test that main() loads configuration from environment."""
        with patch(
            "nora_livekit.__main__.Config.from_env", return_value=mock_config
        ) as mock_from_env:
            with patch("nora_livekit.__main__.setup_logging"):
                with patch("nora_livekit.__main__.threading.Thread"):
                    with patch("nora_livekit.__main__.NoraAgent") as mock_agent_class:
                        mock_agent = AsyncMock()
                        mock_agent._shutdown_event.wait = AsyncMock(return_value=None)
                        mock_agent_class.return_value = mock_agent

                        await main()

                        # Verify config was loaded from environment
                        mock_from_env.assert_called_once()

    @pytest.mark.asyncio
    async def test_main_calls_setup_logging(self, mock_config: Config) -> None:
        """Test that main() calls setup_logging."""
        with patch("nora_livekit.__main__.Config.from_env", return_value=mock_config):
            with patch("nora_livekit.__main__.setup_logging") as mock_setup_logging:
                with patch("nora_livekit.__main__.threading.Thread"):
                    with patch("nora_livekit.__main__.NoraAgent") as mock_agent_class:
                        mock_agent = AsyncMock()
                        mock_agent._shutdown_event.wait = AsyncMock(return_value=None)
                        mock_agent_class.return_value = mock_agent

                        await main()

                        # Verify logging was configured
                        mock_setup_logging.assert_called_once_with(mock_config)

    @pytest.mark.asyncio
    async def test_main_creates_agent_with_config(self, mock_config: Config) -> None:
        """Test that main() creates agent with configuration."""
        with patch("nora_livekit.__main__.Config.from_env", return_value=mock_config):
            with patch("nora_livekit.__main__.setup_logging"):
                with patch("nora_livekit.__main__.threading.Thread"):
                    with patch("nora_livekit.__main__.NoraAgent") as mock_agent_class:
                        mock_agent = AsyncMock()
                        mock_agent._shutdown_event.wait = AsyncMock(return_value=None)
                        mock_agent_class.return_value = mock_agent

                        await main()

                        # Verify agent was created with config
                        mock_agent_class.assert_called_once_with(mock_config)

    @pytest.mark.asyncio
    async def test_main_graceful_shutdown(self, mock_config: Config) -> None:
        """Test that main() performs graceful shutdown."""
        with patch("nora_livekit.__main__.Config.from_env", return_value=mock_config):
            with patch("nora_livekit.__main__.setup_logging"):
                with patch("nora_livekit.__main__.threading.Thread"):
                    with patch("nora_livekit.__main__.NoraAgent") as mock_agent_class:
                        mock_agent = AsyncMock()
                        mock_agent._shutdown_event.wait = AsyncMock(return_value=None)
                        mock_agent_class.return_value = mock_agent

                        await main()

                        # Verify shutdown sequence
                        assert mock_agent.start.call_count == 1
                        assert mock_agent.stop.call_count == 1

                        # Verify stop was called after start
                        start_call_index = next(
                            i
                            for i, call in enumerate(mock_agent.mock_calls)
                            if "start" in str(call)
                        )
                        stop_call_index = next(
                            i for i, call in enumerate(mock_agent.mock_calls) if "stop" in str(call)
                        )
                        assert stop_call_index > start_call_index


class TestMainEntry:
    """Test main entry point invocation."""

    @pytest.mark.asyncio
    async def test_main_completes_successfully(self, mock_config: Config) -> None:
        """Test that main() completes successfully."""
        with patch("nora_livekit.__main__.Config.from_env", return_value=mock_config):
            with patch("nora_livekit.__main__.setup_logging"):
                with patch("nora_livekit.__main__.threading.Thread"):
                    with patch("nora_livekit.__main__.NoraAgent") as mock_agent_class:
                        mock_agent = AsyncMock()
                        mock_agent._shutdown_event.wait = AsyncMock(return_value=None)
                        mock_agent_class.return_value = mock_agent

                        # Should not raise any exception
                        await main()

    @pytest.mark.asyncio
    async def test_main_handles_agent_startup_exception(self, mock_config: Config) -> None:
        """Test that main handles agent startup exceptions."""
        with patch("nora_livekit.__main__.Config.from_env", return_value=mock_config):
            with patch("nora_livekit.__main__.setup_logging"):
                with patch("nora_livekit.__main__.threading.Thread"):
                    with patch("nora_livekit.__main__.NoraAgent") as mock_agent_class:
                        mock_agent = AsyncMock()
                        mock_agent.start.side_effect = Exception("Agent startup failed")
                        mock_agent._shutdown_event.wait = AsyncMock(return_value=None)
                        mock_agent_class.return_value = mock_agent

                        # Should propagate the exception
                        with pytest.raises(Exception, match="Agent startup failed"):
                            await main()

    @pytest.mark.asyncio
    async def test_main_health_server_port_from_config(self, mock_config: Config) -> None:
        """Test that health server uses port from configuration."""
        mock_config.health_check_port = 9999

        with patch("nora_livekit.__main__.Config.from_env", return_value=mock_config):
            with patch("nora_livekit.__main__.setup_logging"):
                with patch("nora_livekit.__main__.run_health_server") as mock_health_server:
                    with patch("nora_livekit.__main__.threading.Thread") as mock_thread:
                        mock_thread_instance = MagicMock()
                        mock_thread.return_value = mock_thread_instance

                        with patch("nora_livekit.__main__.NoraAgent") as mock_agent_class:
                            mock_agent = AsyncMock()
                            mock_agent._shutdown_event.wait = AsyncMock(return_value=None)
                            mock_agent_class.return_value = mock_agent

                            await main()

                            # Verify health server was configured with custom port
                            call_args = mock_thread.call_args
                            assert call_args[1]["args"][0] == 9999
