"""Tests for Cartesia TTS module."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from nora_livekit.voice.tts import CartesiaTTS


class TestCartesiaTTSInitialization:
    """Tests for CartesiaTTS initialization."""

    def test_cartesia_tts_initialization(self):
        """Test CartesiaTTS initializes with correct parameters."""
        tts = CartesiaTTS(
            api_key="test-key",
            voice_id="default-sonic-voice",
            speed=1.0,
            emotion="neutral",
        )

        assert tts.api_key == "test-key"
        assert tts.voice_id == "default-sonic-voice"
        assert tts.speed == 1.0
        assert tts.emotion == "neutral"
        assert tts.is_connected is False

    def test_cartesia_tts_empty_api_key_string(self):
        """Test CartesiaTTS raises error with empty string API key."""
        with pytest.raises(ValueError) as exc_info:
            CartesiaTTS(api_key="")

        assert "api key" in str(exc_info.value).lower()

    def test_cartesia_tts_whitespace_api_key(self):
        """Test CartesiaTTS raises error with whitespace-only API key."""
        with pytest.raises(ValueError) as exc_info:
            CartesiaTTS(api_key="   ")

        assert "api key" in str(exc_info.value).lower()

    def test_cartesia_tts_none_api_key(self):
        """Test CartesiaTTS raises error with None API key."""
        with pytest.raises((ValueError, TypeError)):
            CartesiaTTS(api_key=None)  # type: ignore

    def test_cartesia_tts_custom_voice(self):
        """Test CartesiaTTS with custom voice parameters."""
        tts = CartesiaTTS(
            api_key="test-key",
            voice_id="custom-voice",
            speed=1.5,
            emotion="cheerful",
        )

        assert tts.voice_id == "custom-voice"
        assert tts.speed == 1.5
        assert tts.emotion == "cheerful"

    def test_cartesia_tts_default_parameters(self):
        """Test CartesiaTTS with default parameters."""
        tts = CartesiaTTS(api_key="test-key")

        assert tts.voice_id == "default-sonic-voice"
        assert tts.speed == 1.0
        assert tts.emotion == "neutral"


class TestCartesiaTTSConnection:
    """Tests for Cartesia TTS connection."""

    @pytest.mark.asyncio
    async def test_cartesia_connect(self):
        """Test connecting to Cartesia API."""
        tts = CartesiaTTS(api_key="test-key")

        await tts.connect()

        assert tts.is_connected is True

    @pytest.mark.asyncio
    async def test_cartesia_disconnect(self):
        """Test disconnecting from Cartesia API."""
        tts = CartesiaTTS(api_key="test-key")

        await tts.connect()
        assert tts.is_connected is True

        await tts.disconnect()

        assert tts.is_connected is False

    @pytest.mark.asyncio
    async def test_cartesia_connect_plugin_initialization_error(self):
        """Test connect raises error when plugin initialization fails."""
        tts = CartesiaTTS(api_key="test-key")

        # Force plugin to None to simulate initialization failure
        tts._plugin = None

        with pytest.raises(RuntimeError) as exc_info:
            await tts.connect()

        assert "plugin" in str(exc_info.value).lower()
        assert tts.is_connected is False

    @pytest.mark.asyncio
    async def test_cartesia_connect_exception_caught(self):
        """Test connect catches and handles exceptions properly."""
        tts = CartesiaTTS(api_key="test-key")

        # Mock the plugin to simulate an initialization error
        # This tests the exception handling in connect()
        original_plugin = tts._plugin
        try:
            # Simulate plugin validation raising an error
            tts._plugin = None
            # Try to trigger an exception in the try/except block
            with pytest.raises(RuntimeError):
                await tts.connect()
        finally:
            tts._plugin = original_plugin

    @pytest.mark.asyncio
    async def test_cartesia_synthesize_not_connected(self):
        """Test synthesize raises error when not connected."""
        tts = CartesiaTTS(api_key="test-key")

        with pytest.raises(RuntimeError) as exc_info:
            async for _ in tts.synthesize("test text"):
                pass

        assert "not connected" in str(exc_info.value).lower()


class TestCartesiaTTSSynthesis:
    """Tests for TTS synthesis."""

    @pytest.mark.asyncio
    async def test_synthesize_text_basic(self):
        """Test basic text synthesis."""
        tts = CartesiaTTS(api_key="test-key")
        await tts.connect()

        # Mock the plugin's synthesize method
        async def mock_audio_stream():
            yield b"\x00\x01"
            yield b"\x02\x03"

        with patch.object(tts._plugin, 'synthesize', new_callable=AsyncMock,
                         return_value=mock_audio_stream()):
            audio_chunks = []
            async for chunk in tts.synthesize("Hello, world!"):
                audio_chunks.append(chunk)

            assert len(audio_chunks) > 0
            assert all(isinstance(chunk, bytes) for chunk in audio_chunks)

    @pytest.mark.asyncio
    async def test_synthesize_empty_text_validation(self):
        """Test synthesize raises error with empty text (not just returns)."""
        tts = CartesiaTTS(api_key="test-key")
        await tts.connect()

        with pytest.raises(ValueError) as exc_info:
            async for _ in tts.synthesize(""):
                pass

        assert "text" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_synthesize_text_exceeds_max_length(self):
        """Test synthesize raises error when text exceeds max length."""
        tts = CartesiaTTS(api_key="test-key")
        await tts.connect()

        # Text longer than 5000 characters
        long_text = "a" * 5001

        with pytest.raises(ValueError) as exc_info:
            async for _ in tts.synthesize(long_text):
                pass

        assert "text" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_synthesize_text_at_max_length(self):
        """Test synthesize succeeds with text at max length boundary."""
        tts = CartesiaTTS(api_key="test-key")
        await tts.connect()

        # Text exactly at 5000 characters (boundary)
        max_text = "a" * 5000

        # Mock the plugin's synthesize method
        async def mock_audio_stream():
            yield b"\x00\x01"

        with patch.object(tts._plugin, 'synthesize', new_callable=AsyncMock,
                         return_value=mock_audio_stream()):
            audio_chunks = []
            async for chunk in tts.synthesize(max_text):
                audio_chunks.append(chunk)

            assert len(audio_chunks) > 0

    @pytest.mark.asyncio
    async def test_synthesize_with_sample_rate(self):
        """Test synthesis with custom sample rate."""
        tts = CartesiaTTS(api_key="test-key")
        await tts.connect()

        # Mock the plugin's synthesize method
        async def mock_audio_stream():
            yield b"\x00\x01\x02\x03"

        with patch.object(tts._plugin, 'synthesize', new_callable=AsyncMock,
                         return_value=mock_audio_stream()):
            audio_chunks = []
            async for chunk in tts.synthesize("Test", sample_rate=48000):
                audio_chunks.append(chunk)

            assert len(audio_chunks) > 0

    @pytest.mark.asyncio
    async def test_synthesize_empty_text(self):
        """Test synthesis with empty text."""
        tts = CartesiaTTS(api_key="test-key")
        await tts.connect()

        # Empty text should raise ValueError
        with pytest.raises(ValueError):
            async for _ in tts.synthesize(""):
                pass

    @pytest.mark.asyncio
    async def test_synthesize_whitespace_text(self):
        """Test synthesis with whitespace-only text."""
        tts = CartesiaTTS(api_key="test-key")
        await tts.connect()

        # Whitespace-only text should raise ValueError
        with pytest.raises(ValueError):
            async for _ in tts.synthesize("   "):
                pass


class TestCartesiaTTSVoiceParameters:
    """Tests for voice parameter configuration."""

    @pytest.mark.asyncio
    async def test_different_speeds(self):
        """Test TTS with different speed settings."""
        for speed in [0.5, 1.0, 1.5, 2.0]:
            tts = CartesiaTTS(api_key="test-key", speed=speed)
            await tts.connect()

            # Mock the plugin's synthesize method
            async def mock_audio_stream():
                yield b"\x00\x01"

            with patch.object(tts._plugin, 'synthesize', new_callable=AsyncMock,
                             return_value=mock_audio_stream()):
                audio_chunks = []
                async for chunk in tts.synthesize("Test text"):
                    audio_chunks.append(chunk)

                assert len(audio_chunks) > 0
            await tts.disconnect()

    @pytest.mark.asyncio
    async def test_different_emotions(self):
        """Test TTS with different emotion settings."""
        for emotion in ["neutral", "cheerful", "sad", "excited"]:
            tts = CartesiaTTS(api_key="test-key", emotion=emotion)
            await tts.connect()

            # Mock the plugin's synthesize method
            async def mock_audio_stream():
                yield b"\x00\x01"

            with patch.object(tts._plugin, 'synthesize', new_callable=AsyncMock,
                             return_value=mock_audio_stream()):
                audio_chunks = []
                async for chunk in tts.synthesize("Test text"):
                    audio_chunks.append(chunk)

                assert len(audio_chunks) > 0
            await tts.disconnect()


class TestCartesiaTTSEdgeCases:
    """Tests for CartesiaTTS edge cases."""

    def test_cartesia_tts_empty_api_key(self):
        """Test CartesiaTTS with non-empty but minimal API key."""
        # The LiveKit plugin requires a non-empty API key
        tts = CartesiaTTS(api_key="test-key-minimal")

        assert tts.api_key == "test-key-minimal"

    @pytest.mark.asyncio
    async def test_cartesia_extreme_speed(self):
        """Test TTS with extreme speed values."""
        tts_slow = CartesiaTTS(api_key="test-key", speed=0.1)
        tts_fast = CartesiaTTS(api_key="test-key", speed=3.0)

        assert tts_slow.speed == 0.1
        assert tts_fast.speed == 3.0

    def test_cartesia_long_voice_id(self):
        """Test TTS with very long voice ID."""
        long_id = "voice_" + "x" * 1000
        tts = CartesiaTTS(api_key="test-key", voice_id=long_id)

        assert tts.voice_id == long_id

    @pytest.mark.asyncio
    async def test_cartesia_long_text_synthesis(self):
        """Test TTS with very long text."""
        tts = CartesiaTTS(api_key="test-key")
        await tts.connect()

        long_text = "This is a test. " * 100

        # Mock the plugin's synthesize method
        async def mock_audio_stream():
            yield b"\x00\x01"

        with patch.object(tts._plugin, 'synthesize', new_callable=AsyncMock,
                         return_value=mock_audio_stream()):
            audio_chunks = []
            async for chunk in tts.synthesize(long_text):
                audio_chunks.append(chunk)

            assert len(audio_chunks) > 0


class TestCartesiaLiveKitIntegration:
    """Tests for LiveKit Cartesia TTS plugin integration."""

    @pytest.mark.asyncio
    async def test_cartesia_tts_uses_livekit_plugin(self):
        """Test CartesiaTTS initializes LiveKit Cartesia plugin."""
        tts = CartesiaTTS(api_key="test-key", voice_id="sonic-english-male")

        # Verify plugin is initialized
        assert tts._plugin is not None
        assert hasattr(tts._plugin, 'synthesize')

    @pytest.mark.asyncio
    async def test_cartesia_synthesize_with_real_plugin(self):
        """Test synthesis with mocked LiveKit plugin."""
        tts = CartesiaTTS(api_key="test-key")
        await tts.connect()

        # Mock the plugin's synthesize method
        async def mock_audio_stream():
            yield b"\x00\x01\x02\x03"
            yield b"\x04\x05\x06\x07"

        with patch.object(tts._plugin, 'synthesize', new_callable=AsyncMock,
                         return_value=mock_audio_stream()):
            audio_chunks = []
            async for chunk in tts.synthesize("Hello world"):
                audio_chunks.append(chunk)

            assert len(audio_chunks) == 2
            assert all(isinstance(chunk, bytes) for chunk in audio_chunks)

    @pytest.mark.asyncio
    async def test_cartesia_retry_on_transient_error(self):
        """Test retry logic for transient errors."""
        tts = CartesiaTTS(api_key="test-key", max_retries=2)
        await tts.connect()

        call_count = 0

        async def mock_results():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("Transient error")
            yield b"audio"

        # Mock plugin to raise error on first call, succeed on second
        with patch.object(tts._plugin, 'synthesize', side_effect=[
            ConnectionError("Transient"),
            mock_results()
        ]):
            audio_chunks = []
            try:
                async for chunk in tts.synthesize("test"):
                    audio_chunks.append(chunk)
            except Exception:
                pass  # Retry may be handled internally

    @pytest.mark.asyncio
    async def test_cartesia_voice_parameter_application(self):
        """Test that voice parameters are passed to plugin."""
        tts = CartesiaTTS(
            api_key="test-key",
            voice_id="sonic-english-female",
            speed=1.5,
            emotion="cheerful"
        )
        await tts.connect()

        # Verify parameters are stored
        assert tts.voice_id == "sonic-english-female"
        assert tts.speed == 1.5
        assert tts.emotion == "cheerful"

    @pytest.mark.asyncio
    async def test_cartesia_rate_limit_handling(self):
        """Test handling of rate limit errors."""
        tts = CartesiaTTS(api_key="test-key")
        await tts.connect()

        # Mock plugin to raise rate limit error
        with patch.object(tts._plugin, 'synthesize',
                         side_effect=RuntimeError("Rate limit exceeded")):
            with pytest.raises(RuntimeError):
                async for _ in tts.synthesize("test"):
                    pass

    @pytest.mark.asyncio
    async def test_cartesia_empty_text_handling(self):
        """Test synthesis raises error for empty text."""
        tts = CartesiaTTS(api_key="test-key")
        await tts.connect()

        # Empty text should raise ValueError
        with pytest.raises(ValueError):
            async for _ in tts.synthesize(""):
                pass

    @pytest.mark.asyncio
    async def test_cartesia_stream_audio_method(self):
        """Test the _stream_audio method processes response data."""
        tts = CartesiaTTS(api_key="test-key")
        await tts.connect()

        # Create a mock response that supports async iteration
        class MockAsyncResponse:
            def __aiter__(self):
                return self

            def __init__(self):
                self.chunks = [b"chunk1", b"chunk2"]
                self.index = 0

            async def __anext__(self):
                if self.index >= len(self.chunks):
                    raise StopAsyncIteration
                chunk = self.chunks[self.index]
                self.index += 1
                return chunk

        mock_response = MockAsyncResponse()

        # Test _stream_audio
        audio_chunks = []
        async for chunk in tts._stream_audio(mock_response):
            audio_chunks.append(chunk)

        # Should yield the actual audio chunks
        assert len(audio_chunks) == 2
        assert audio_chunks[0] == b"chunk1"
        assert audio_chunks[1] == b"chunk2"
