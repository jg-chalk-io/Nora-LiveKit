"""Tests for Deepgram STT module."""

import pytest
from unittest.mock import AsyncMock, patch
from nora_livekit.voice.stt import DeepgramSTT, TranscriptionResult


class TestTranscriptionResult:
    """Tests for TranscriptionResult dataclass."""

    def test_transcription_result_creation(self):
        """Test creating TranscriptionResult."""
        result = TranscriptionResult(text="hello world", is_final=True, confidence=0.95)

        assert result.text == "hello world"
        assert result.is_final is True
        assert result.confidence == 0.95

    def test_transcription_result_interim(self):
        """Test interim TranscriptionResult without final flag."""
        result = TranscriptionResult(text="hello", is_final=False)

        assert result.text == "hello"
        assert result.is_final is False
        assert result.confidence is None


class TestDeepgramSTTInitialization:
    """Tests for DeepgramSTT initialization."""

    def test_deepgram_stt_initialization(self):
        """Test DeepgramSTT initializes with correct parameters."""
        stt = DeepgramSTT(
            api_key="test-key",
            model="nova-2",
            language="en-US",
        )

        assert stt.api_key == "test-key"
        assert stt.model == "nova-2"
        assert stt.language == "en-US"
        assert stt.interim_results is True
        assert stt.is_connected is False

    def test_deepgram_stt_custom_model(self):
        """Test DeepgramSTT with custom model."""
        stt = DeepgramSTT(api_key="test-key", model="nova-3")

        assert stt.model == "nova-3"

    def test_deepgram_stt_interim_results_disabled(self):
        """Test DeepgramSTT with interim results disabled."""
        stt = DeepgramSTT(api_key="test-key", interim_results=False)

        assert stt.interim_results is False


class TestDeepgramSTTConnection:
    """Tests for Deepgram STT connection."""

    @pytest.mark.asyncio
    async def test_deepgram_connect(self):
        """Test connecting to Deepgram API."""
        stt = DeepgramSTT(api_key="test-key")

        await stt.connect()

        assert stt.is_connected is True

    @pytest.mark.asyncio
    async def test_deepgram_disconnect(self):
        """Test disconnecting from Deepgram API."""
        stt = DeepgramSTT(api_key="test-key")

        await stt.connect()
        assert stt.is_connected is True

        await stt.disconnect()

        assert stt.is_connected is False

    @pytest.mark.asyncio
    async def test_deepgram_transcribe_not_connected(self):
        """Test transcribe_stream raises error when not connected."""
        stt = DeepgramSTT(api_key="test-key")

        async def dummy_audio():
            yield b"audio"

        with pytest.raises(RuntimeError) as exc_info:
            async for _ in stt.transcribe_stream(dummy_audio()):
                pass

        assert "not connected" in str(exc_info.value).lower()


class TestDeepgramSTTTranscription:
    """Tests for STT transcription."""

    @pytest.mark.asyncio
    async def test_transcribe_stream_basic(self):
        """Test basic transcription streaming."""
        stt = DeepgramSTT(api_key="test-key")
        await stt.connect()

        async def mock_audio():
            yield b"audio_chunk_1"
            yield b"audio_chunk_2"

        results = []
        async for result in stt.transcribe_stream(mock_audio()):
            results.append(result)

        assert len(results) > 0
        assert all(isinstance(r, TranscriptionResult) for r in results)

    @pytest.mark.asyncio
    async def test_transcribe_stream_includes_final_result(self):
        """Test transcription includes final result."""
        stt = DeepgramSTT(api_key="test-key")
        await stt.connect()

        async def mock_audio():
            yield b"audio_chunk"

        results = []
        async for result in stt.transcribe_stream(mock_audio()):
            results.append(result)

        # Should have at least one final result
        final_results = [r for r in results if r.is_final]
        assert len(final_results) > 0


class TestDeepgramSTTEdgeCases:
    """Tests for DeepgramSTT edge cases."""

    def test_deepgram_stt_empty_api_key(self):
        """Test DeepgramSTT with empty API key."""
        stt = DeepgramSTT(api_key="")

        assert stt.api_key == ""

    @pytest.mark.asyncio
    async def test_deepgram_transcribe_empty_stream(self):
        """Test transcription with empty audio stream."""
        stt = DeepgramSTT(api_key="test-key")
        await stt.connect()

        async def empty_audio():
            return
            yield  # Make it async generator

        results = []
        async for result in stt.transcribe_stream(empty_audio()):
            results.append(result)

        # Should still return results (at least final)
        assert len(results) > 0

    def test_deepgram_multiple_languages(self):
        """Test DeepgramSTT with different languages."""
        stt_en = DeepgramSTT(api_key="test-key", language="en-US")
        stt_es = DeepgramSTT(api_key="test-key", language="es-ES")
        stt_fr = DeepgramSTT(api_key="test-key", language="fr-FR")

        assert stt_en.language == "en-US"
        assert stt_es.language == "es-ES"
        assert stt_fr.language == "fr-FR"
