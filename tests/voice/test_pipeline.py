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


class TestVoicePipelineProcessAudio:
    """Tests for audio stream processing."""

    @pytest.mark.asyncio
    async def test_process_audio_with_participant(self):
        """Test processing audio from specific participant."""
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

        # Create a proper async generator
        async def mock_audio_stream():
            yield b"test_chunk"

        # Mock the audio handler's subscribe method
        with patch.object(
            audio_handler, "subscribe_to_participant_audio"
        ) as mock_subscribe:
            mock_subscribe.return_value = mock_audio_stream()

            await pipeline.process_audio_stream("participant-123")

            mock_subscribe.assert_called_once_with("participant-123")

        await pipeline.stop()

    @pytest.mark.asyncio
    async def test_process_audio_empty_participant_id(self):
        """Test processing audio with empty participant ID."""
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

        # Create a proper async generator
        async def mock_audio_stream():
            yield b"test_chunk"

        # Mock the audio handler's subscribe method
        with patch.object(
            audio_handler, "subscribe_to_participant_audio"
        ) as mock_subscribe:
            mock_subscribe.return_value = mock_audio_stream()

            await pipeline.process_audio_stream("")

            mock_subscribe.assert_called_once_with("")

        await pipeline.stop()

    @pytest.mark.asyncio
    async def test_process_audio_stream_error_handling(self):
        """Test error handling during audio stream processing."""
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

        # Mock the audio handler to raise error
        with patch.object(
            audio_handler, "subscribe_to_participant_audio", side_effect=RuntimeError("Stream error")
        ):
            with pytest.raises(RuntimeError):
                await pipeline.process_audio_stream("participant-123")

        await pipeline.stop()


class TestVoicePipelineTranscription:
    """Tests for transcription handling."""

    @pytest.mark.asyncio
    async def test_handle_transcription_basic(self):
        """Test handling transcription text."""
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

        # Create proper async generator
        async def mock_tts_stream():
            yield b"audio_chunk1"
            yield b"audio_chunk2"

        # Mock TTS synthesize method
        with patch.object(tts, "synthesize") as mock_synthesize:
            mock_synthesize.return_value = mock_tts_stream()

            await pipeline._handle_transcription("Hello agent")

            mock_synthesize.assert_called_once()
            call_args = mock_synthesize.call_args[0][0]
            assert "You said:" in call_args
            assert "Hello agent" in call_args

        await pipeline.stop()

    @pytest.mark.asyncio
    async def test_handle_transcription_with_tts_error(self):
        """Test transcription handling when TTS fails."""
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

        # Mock TTS to raise error
        with patch.object(tts, "synthesize", side_effect=RuntimeError("TTS error")):
            # Should catch error gracefully
            await pipeline._handle_transcription("Hello agent")

        await pipeline.stop()

    @pytest.mark.asyncio
    async def test_handle_transcription_empty_text(self):
        """Test handling empty transcription text."""
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

        # Create proper async generator
        async def mock_tts_stream():
            yield b"audio"

        with patch.object(tts, "synthesize") as mock_synthesize:
            mock_synthesize.return_value = mock_tts_stream()

            await pipeline._handle_transcription("")

            # Should still process empty text
            assert mock_synthesize.called

        await pipeline.stop()


class TestVoicePipelineStartErrorRecovery:
    """Tests for startup error recovery."""

    @pytest.mark.asyncio
    async def test_pipeline_start_tts_failure(self):
        """Test pipeline start when TTS fails to connect."""
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

        # Mock TTS to fail
        with patch.object(tts, "connect", side_effect=RuntimeError("TTS connection failed")):
            with pytest.raises(RuntimeError):
                await pipeline.start()

            assert pipeline.is_running is False


class TestVoicePipelineStopErrorRecovery:
    """Tests for shutdown error recovery."""

    @pytest.mark.asyncio
    async def test_pipeline_stop_stt_failure(self):
        """Test pipeline stop when STT fails to disconnect."""
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

        # Mock STT disconnect to fail
        with patch.object(stt, "disconnect", side_effect=RuntimeError("STT disconnect failed")):
            with pytest.raises(RuntimeError):
                await pipeline.stop()

        # Pipeline should still be marked as stopped
        assert pipeline.is_running is False
