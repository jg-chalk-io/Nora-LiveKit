"""Tests for Cartesia TTS module."""

import pytest
from unittest.mock import AsyncMock, patch
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

        audio_chunks = []
        async for chunk in tts.synthesize("Hello, world!"):
            audio_chunks.append(chunk)

        assert len(audio_chunks) > 0
        assert all(isinstance(chunk, bytes) for chunk in audio_chunks)

    @pytest.mark.asyncio
    async def test_synthesize_with_sample_rate(self):
        """Test synthesis with custom sample rate."""
        tts = CartesiaTTS(api_key="test-key")
        await tts.connect()

        audio_chunks = []
        async for chunk in tts.synthesize("Test", sample_rate=48000):
            audio_chunks.append(chunk)

        assert len(audio_chunks) > 0

    @pytest.mark.asyncio
    async def test_synthesize_empty_text(self):
        """Test synthesis with empty text."""
        tts = CartesiaTTS(api_key="test-key")
        await tts.connect()

        audio_chunks = []
        async for chunk in tts.synthesize(""):
            audio_chunks.append(chunk)

        # Empty text should not generate audio
        assert len(audio_chunks) == 0

    @pytest.mark.asyncio
    async def test_synthesize_whitespace_text(self):
        """Test synthesis with whitespace-only text."""
        tts = CartesiaTTS(api_key="test-key")
        await tts.connect()

        audio_chunks = []
        async for chunk in tts.synthesize("   "):
            audio_chunks.append(chunk)

        # Whitespace should not generate audio
        assert len(audio_chunks) == 0


class TestCartesiaTTSVoiceParameters:
    """Tests for voice parameter configuration."""

    @pytest.mark.asyncio
    async def test_different_speeds(self):
        """Test TTS with different speed settings."""
        for speed in [0.5, 1.0, 1.5, 2.0]:
            tts = CartesiaTTS(api_key="test-key", speed=speed)
            await tts.connect()

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

            audio_chunks = []
            async for chunk in tts.synthesize("Test text"):
                audio_chunks.append(chunk)

            assert len(audio_chunks) > 0
            await tts.disconnect()


class TestCartesiaTTSEdgeCases:
    """Tests for CartesiaTTS edge cases."""

    def test_cartesia_tts_empty_api_key(self):
        """Test CartesiaTTS with empty API key."""
        tts = CartesiaTTS(api_key="")

        assert tts.api_key == ""

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

        audio_chunks = []
        async for chunk in tts.synthesize(long_text):
            audio_chunks.append(chunk)

        assert len(audio_chunks) > 0
