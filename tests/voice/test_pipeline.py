"""Tests for VoicePipeline orchestration."""

import pytest
import time
from unittest.mock import AsyncMock, Mock, patch
from nora_livekit.config import Config, VoiceConfig
from nora_livekit.voice.pipeline import VoicePipeline
from nora_livekit.voice.stt import DeepgramSTT
from nora_livekit.voice.tts import CartesiaTTS
from nora_livekit.voice.audio_handler import AudioHandler


class MockRoom:
    """Mock LiveKit room for testing."""

    pass


class TestVoicePipelineInitialization:
    """Tests for VoicePipeline initialization."""

    def test_pipeline_initialization(self):
        """Test VoicePipeline initializes with required components."""
        config = Config(
            livekit_url="wss://test.livekit.io",
            livekit_api_key="test-key",
            livekit_api_secret="test-secret",
            voice=VoiceConfig(deepgram_api_key="dg-key", cartesia_api_key="ca-key"),
        )
        mock_room = MockRoom()
        stt = DeepgramSTT(api_key="dg-key")
        tts = CartesiaTTS(api_key="ca-key")
        audio_handler = AudioHandler(mock_room)

        pipeline = VoicePipeline(config, stt, tts, audio_handler)

        assert pipeline.config is config
        assert pipeline.stt is stt
        assert pipeline.tts is tts
        assert pipeline.audio_handler is audio_handler
        assert pipeline.is_running is False


class TestVoicePipelineLifecycle:
    """Tests for VoicePipeline lifecycle."""

    @pytest.mark.asyncio
    async def test_pipeline_start(self):
        """Test starting voice pipeline."""
        config = Config(
            livekit_url="wss://test.livekit.io",
            livekit_api_key="test-key",
            livekit_api_secret="test-secret",
        )
        mock_room = MockRoom()
        stt = DeepgramSTT(api_key="test-key")
        tts = CartesiaTTS(api_key="test-key")
        audio_handler = AudioHandler(mock_room)

        pipeline = VoicePipeline(config, stt, tts, audio_handler)

        await pipeline.start()

        assert pipeline.is_running is True
        assert stt.is_connected is True
        assert tts.is_connected is True

    @pytest.mark.asyncio
    async def test_pipeline_stop(self):
        """Test stopping voice pipeline."""
        config = Config(
            livekit_url="wss://test.livekit.io",
            livekit_api_key="test-key",
            livekit_api_secret="test-secret",
        )
        mock_room = MockRoom()
        stt = DeepgramSTT(api_key="test-key")
        tts = CartesiaTTS(api_key="test-key")
        audio_handler = AudioHandler(mock_room)

        pipeline = VoicePipeline(config, stt, tts, audio_handler)

        await pipeline.start()
        assert pipeline.is_running is True

        await pipeline.stop()

        assert pipeline.is_running is False
        assert stt.is_connected is False
        assert tts.is_connected is False

    @pytest.mark.asyncio
    async def test_pipeline_graceful_shutdown(self):
        """Test pipeline shutdown completes in reasonable time."""
        config = Config(
            livekit_url="wss://test.livekit.io",
            livekit_api_key="test-key",
            livekit_api_secret="test-secret",
        )
        mock_room = MockRoom()
        stt = DeepgramSTT(api_key="test-key")
        tts = CartesiaTTS(api_key="test-key")
        audio_handler = AudioHandler(mock_room)

        pipeline = VoicePipeline(config, stt, tts, audio_handler)

        await pipeline.start()

        start_time = time.time()
        await pipeline.stop()
        shutdown_duration = time.time() - start_time

        # Should complete within 5 seconds
        assert shutdown_duration < 5.0


class TestVoicePipelineAudioProcessing:
    """Tests for audio processing in voice pipeline."""

    @pytest.mark.asyncio
    async def test_process_audio_not_running(self):
        """Test process_audio_stream raises error when pipeline not running."""
        config = Config(
            livekit_url="wss://test.livekit.io",
            livekit_api_key="test-key",
            livekit_api_secret="test-secret",
        )
        mock_room = MockRoom()
        stt = DeepgramSTT(api_key="test-key")
        tts = CartesiaTTS(api_key="test-key")
        audio_handler = AudioHandler(mock_room)

        pipeline = VoicePipeline(config, stt, tts, audio_handler)

        with pytest.raises(RuntimeError) as exc_info:
            await pipeline.process_audio_stream()

        assert "not running" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_generate_response_echo(self):
        """Test response generation (echo behavior)."""
        config = Config(
            livekit_url="wss://test.livekit.io",
            livekit_api_key="test-key",
            livekit_api_secret="test-secret",
        )
        mock_room = MockRoom()
        stt = DeepgramSTT(api_key="test-key")
        tts = CartesiaTTS(api_key="test-key")
        audio_handler = AudioHandler(mock_room)

        pipeline = VoicePipeline(config, stt, tts, audio_handler)

        response = await pipeline._generate_response("Hello agent")

        assert "Hello agent" in response
        assert "You said:" in response


class TestVoicePipelineErrorHandling:
    """Tests for error handling in voice pipeline."""

    @pytest.mark.asyncio
    async def test_pipeline_start_with_invalid_config(self):
        """Test pipeline handles errors during startup."""
        config = Config(
            livekit_url="wss://test.livekit.io",
            livekit_api_key="test-key",
            livekit_api_secret="test-secret",
        )
        mock_room = MockRoom()

        # Create mock STT that fails to connect
        stt = DeepgramSTT(api_key="test-key")
        with patch.object(stt, "connect", side_effect=RuntimeError("Connection failed")):
            tts = CartesiaTTS(api_key="test-key")
            audio_handler = AudioHandler(mock_room)
            pipeline = VoicePipeline(config, stt, tts, audio_handler)

            with pytest.raises(RuntimeError):
                await pipeline.start()

            assert pipeline.is_running is False


class TestVoicePipelineIntegration:
    """Integration tests for VoicePipeline."""

    @pytest.mark.asyncio
    async def test_full_pipeline_lifecycle(self):
        """Test complete pipeline lifecycle."""
        config = Config(
            livekit_url="wss://test.livekit.io",
            livekit_api_key="test-key",
            livekit_api_secret="test-secret",
        )
        mock_room = MockRoom()
        stt = DeepgramSTT(api_key="test-key")
        tts = CartesiaTTS(api_key="test-key")
        audio_handler = AudioHandler(mock_room)

        pipeline = VoicePipeline(config, stt, tts, audio_handler)

        # Start pipeline
        await pipeline.start()
        assert pipeline.is_running is True

        # Test response generation
        response = await pipeline._generate_response("test input")
        assert len(response) > 0

        # Stop pipeline
        await pipeline.stop()
        assert pipeline.is_running is False


class TestVoicePipelineEdgeCases:
    """Tests for edge cases in VoicePipeline."""

    @pytest.mark.asyncio
    async def test_multiple_start_calls(self):
        """Test calling start multiple times."""
        config = Config(
            livekit_url="wss://test.livekit.io",
            livekit_api_key="test-key",
            livekit_api_secret="test-secret",
        )
        mock_room = MockRoom()
        stt = DeepgramSTT(api_key="test-key")
        tts = CartesiaTTS(api_key="test-key")
        audio_handler = AudioHandler(mock_room)

        pipeline = VoicePipeline(config, stt, tts, audio_handler)

        await pipeline.start()
        first_start = pipeline.is_running

        # Starting again should work (idempotent)
        await pipeline.start()
        second_start = pipeline.is_running

        assert first_start is True
        assert second_start is True

        await pipeline.stop()

    @pytest.mark.asyncio
    async def test_multiple_stop_calls(self):
        """Test calling stop multiple times."""
        config = Config(
            livekit_url="wss://test.livekit.io",
            livekit_api_key="test-key",
            livekit_api_secret="test-secret",
        )
        mock_room = MockRoom()
        stt = DeepgramSTT(api_key="test-key")
        tts = CartesiaTTS(api_key="test-key")
        audio_handler = AudioHandler(mock_room)

        pipeline = VoicePipeline(config, stt, tts, audio_handler)

        await pipeline.start()
        await pipeline.stop()

        first_state = pipeline.is_running

        # Stopping again should be safe
        await pipeline.stop()
        second_state = pipeline.is_running

        assert first_state is False
        assert second_state is False
