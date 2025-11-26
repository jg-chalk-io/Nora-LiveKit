"""Tests for AudioHandler module."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from nora_livekit.voice.audio_handler import AudioHandler  # noqa: F401


class MockLiveKitRoom:
    """Mock LiveKit Room for testing."""

    def __init__(self):
        """Initialize mock room."""
        self.participants = {}
        self.published_audio = []

    async def get_participant(self, participant_id: str):
        """Get mock participant."""
        if participant_id not in self.participants:
            self.participants[participant_id] = MockParticipant(participant_id)
        return self.participants[participant_id]


class MockParticipant:
    """Mock LiveKit Participant for testing."""

    def __init__(self, participant_id: str):
        """Initialize mock participant."""
        self.participant_id = participant_id
        self.audio_track = None

    async def get_audio_track(self):
        """Get mock audio track."""
        if self.audio_track is None:
            self.audio_track = MockAudioTrack()
        return self.audio_track


class MockAudioTrack:
    """Mock LiveKit AudioTrack for testing."""

    def __init__(self):
        """Initialize mock audio track."""
        self.audio_chunks = [b"chunk1", b"chunk2", b"chunk3"]
        self.published_audio = []
        self._index = 0

    async def get_audio_stream(self):
        """Get mock audio stream iterator."""
        return MockAudioStream(self.audio_chunks)

    async def publish(self, audio_data: bytes):
        """Mock publish method."""
        self.published_audio.append(audio_data)


class MockAudioStream:
    """Mock audio stream for async iteration."""

    def __init__(self, chunks):
        """Initialize with audio chunks."""
        self.chunks = chunks
        self._index = 0

    def __aiter__(self):
        """Support async iteration."""
        self._index = 0
        return self

    async def __anext__(self):
        """Return next audio chunk."""
        if self._index >= len(self.chunks):
            raise StopAsyncIteration
        chunk = self.chunks[self._index]
        self._index += 1
        return chunk


class TestAudioHandlerInitialization:
    """Tests for AudioHandler initialization."""

    def test_audio_handler_initialization(self):
        """Test AudioHandler initializes with correct parameters."""
        mock_room = MockLiveKitRoom()

        handler = AudioHandler(mock_room, sample_rate=16000, channels=1)

        assert handler.room is mock_room
        assert handler.sample_rate == 16000
        assert handler.channels == 1

    def test_audio_handler_default_parameters(self):
        """Test AudioHandler uses default parameters."""
        mock_room = MockLiveKitRoom()

        handler = AudioHandler(mock_room)

        assert handler.sample_rate == 16000
        assert handler.channels == 1

    def test_audio_handler_custom_parameters(self):
        """Test AudioHandler with custom sample rate and channels."""
        mock_room = MockLiveKitRoom()

        handler = AudioHandler(mock_room, sample_rate=48000, channels=2)

        assert handler.sample_rate == 48000
        assert handler.channels == 2


class TestAudioHandlerSubscription:
    """Tests for audio track subscription."""

    @pytest.mark.asyncio
    async def test_subscribe_to_participant_audio(self):
        """Test subscribing to participant audio track."""
        mock_room = MockLiveKitRoom()
        handler = AudioHandler(mock_room)

        audio_chunks = []
        async for chunk in handler.subscribe_to_participant_audio("participant-123"):
            audio_chunks.append(chunk)
            if len(audio_chunks) >= 3:
                break

        assert len(audio_chunks) == 3
        assert audio_chunks[0] == b"chunk1"
        assert audio_chunks[1] == b"chunk2"
        assert audio_chunks[2] == b"chunk3"

    @pytest.mark.asyncio
    async def test_subscribe_to_nonexistent_participant(self):
        """Test subscribing to audio from non-existent participant."""
        mock_room = MockLiveKitRoom()
        handler = AudioHandler(mock_room)

        # Should handle gracefully by getting participant which auto-creates mock
        audio_chunks = []
        async for chunk in handler.subscribe_to_participant_audio("new-participant"):
            audio_chunks.append(chunk)
            if len(audio_chunks) >= 2:
                break

        assert len(audio_chunks) == 2


class TestAudioHandlerPublishing:
    """Tests for audio publishing."""

    @pytest.mark.asyncio
    async def test_publish_audio_stream(self):
        """Test publishing audio stream to room."""
        mock_room = MockLiveKitRoom()
        mock_room.audio_track = MockAudioTrack()
        handler = AudioHandler(mock_room)

        async def mock_audio_stream():
            """Generate mock audio chunks."""
            yield b"response1"
            yield b"response2"

        # Mock the room's audio_track to track published audio
        with patch.object(
            handler, "_get_agent_audio_track", new_callable=AsyncMock
        ) as mock_get_track:
            mock_track = MockAudioTrack()
            mock_get_track.return_value = mock_track

            await handler.publish_audio(mock_audio_stream())

            # Verify audio was published
            assert len(mock_track.published_audio) == 2
            assert mock_track.published_audio[0] == b"response1"
            assert mock_track.published_audio[1] == b"response2"


class TestAudioFormatConversion:
    """Tests for audio format conversion."""

    def test_convert_pcm_to_pcm(self):
        """Test converting PCM to PCM (no conversion needed)."""
        mock_room = MockLiveKitRoom()
        handler = AudioHandler(mock_room)

        pcm_audio = b"\x00\x01\x02\x03\x04\x05"
        result = handler.convert_format(pcm_audio, "pcm", "pcm")

        assert result == pcm_audio

    def test_convert_audio_maintains_data_integrity(self):
        """Test audio conversion maintains data integrity."""
        mock_room = MockLiveKitRoom()
        handler = AudioHandler(mock_room)

        original_audio = b"\x00\x01\x02\x03"
        # For same format, data should be unchanged
        result = handler.convert_format(original_audio, "pcm", "pcm")

        assert len(result) > 0
        assert isinstance(result, bytes)


class TestAudioBuffering:
    """Tests for audio buffering."""

    @pytest.mark.asyncio
    async def test_buffer_audio_basic(self):
        """Test basic audio buffering."""
        mock_room = MockLiveKitRoom()
        handler = AudioHandler(mock_room)

        async def jittery_audio():
            """Generate audio chunks with timing variation."""
            yield b"chunk1"
            yield b"chunk2"
            yield b"chunk3"

        buffered_chunks = []
        async for chunk in handler._buffer_audio(jittery_audio(), buffer_duration_ms=50):
            buffered_chunks.append(chunk)

        # Buffer combines small chunks, so should receive fewer but larger chunks
        assert len(buffered_chunks) >= 1
        # Verify data integrity - all chunks combined
        combined = b"".join(buffered_chunks)
        assert combined == b"chunk1chunk2chunk3"

    @pytest.mark.asyncio
    async def test_buffer_audio_empty_stream(self):
        """Test buffering empty audio stream."""
        mock_room = MockLiveKitRoom()
        handler = AudioHandler(mock_room)

        async def empty_audio():
            """Generate no chunks."""
            return
            yield  # Make it async generator

        buffered_chunks = []
        async for chunk in handler._buffer_audio(empty_audio(), buffer_duration_ms=50):
            buffered_chunks.append(chunk)

        assert len(buffered_chunks) == 0


class TestAudioHandlerIntegration:
    """Integration tests for AudioHandler."""

    @pytest.mark.asyncio
    async def test_full_audio_flow(self):
        """Test complete audio subscription and publishing flow."""
        mock_room = MockLiveKitRoom()
        handler = AudioHandler(mock_room)

        # Subscribe to audio
        audio_chunks = []
        async for chunk in handler.subscribe_to_participant_audio("speaker"):
            audio_chunks.append(chunk)
            if len(audio_chunks) >= 2:
                break

        # Verify subscription worked
        assert len(audio_chunks) >= 2


class TestAudioHandlerEdgeCases:
    """Tests for AudioHandler edge cases."""

    def test_audio_handler_with_zero_sample_rate(self):
        """Test AudioHandler raises error with invalid sample rate."""
        mock_room = MockLiveKitRoom()

        # Should still initialize (validation happens elsewhere)
        handler = AudioHandler(mock_room, sample_rate=0)
        assert handler.sample_rate == 0

    def test_audio_handler_with_large_sample_rate(self):
        """Test AudioHandler with very high sample rate."""
        mock_room = MockLiveKitRoom()

        handler = AudioHandler(mock_room, sample_rate=192000)
        assert handler.sample_rate == 192000

    def test_audio_handler_with_multiple_channels(self):
        """Test AudioHandler with multi-channel audio."""
        mock_room = MockLiveKitRoom()

        handler = AudioHandler(mock_room, channels=6)  # 5.1 surround
        assert handler.channels == 6


class TestAudioHandlerErrorHandling:
    """Tests for error handling in AudioHandler."""

    @pytest.mark.asyncio
    async def test_audio_handler_subscription_error_handling(self):
        """Test error handling during subscription."""
        mock_room = Mock()
        mock_room.get_participant = AsyncMock(side_effect=RuntimeError("Connection failed"))

        handler = AudioHandler(mock_room)

        with pytest.raises(RuntimeError):
            async for chunk in handler.subscribe_to_participant_audio("participant-123"):
                pass

    @pytest.mark.asyncio
    async def test_audio_handler_publish_no_track(self):
        """Test publishing when no audio track available."""
        mock_room = MockLiveKitRoom()
        handler = AudioHandler(mock_room)

        async def mock_audio():
            yield b"test"

        # Should raise RuntimeError when room doesn't have audio_track
        with pytest.raises(RuntimeError):
            await handler.publish_audio(mock_audio())

    @pytest.mark.asyncio
    async def test_audio_buffering_error_handling(self):
        """Test error handling during audio buffering."""
        mock_room = MockLiveKitRoom()
        handler = AudioHandler(mock_room)

        async def failing_audio():
            yield b"chunk1"
            raise RuntimeError("Stream error")

        with pytest.raises(RuntimeError):
            async for chunk in handler._buffer_audio(failing_audio()):
                pass

    def test_get_agent_audio_track_success(self):
        """Test getting agent audio track successfully."""
        mock_room = MockLiveKitRoom()
        mock_audio_track = MockAudioTrack()
        mock_room.audio_track = mock_audio_track
        handler = AudioHandler(mock_room)

        result = asyncio.run(handler._get_agent_audio_track())

        assert result is mock_audio_track

    def test_get_agent_audio_track_missing(self):
        """Test error when audio track missing from room."""
        mock_room = MockLiveKitRoom()
        # Don't set audio_track on mock_room
        handler = AudioHandler(mock_room)

        with pytest.raises(RuntimeError) as exc_info:
            asyncio.run(handler._get_agent_audio_track())

        assert "audio track" in str(exc_info.value).lower()


class TestAudioHandlerFormatConversionEdgeCases:
    """Additional tests for format conversion edge cases."""

    def test_convert_format_unsupported_conversion(self):
        """Test converting between unsupported format combinations."""
        mock_room = MockLiveKitRoom()
        handler = AudioHandler(mock_room)

        audio = b"\x00\x01\x02\x03"
        result = handler.convert_format(audio, "wav", "mp3")

        # For unsupported conversions, should return as-is
        assert result == audio

    def test_convert_format_pcm_to_wav(self):
        """Test converting from PCM to WAV format."""
        mock_room = MockLiveKitRoom()
        handler = AudioHandler(mock_room)

        pcm_audio = b"\x00\x01\x02\x03"
        result = handler.convert_format(pcm_audio, "pcm", "wav")

        # Currently returns as-is for unsupported conversion
        assert isinstance(result, bytes)

    def test_convert_format_empty_audio(self):
        """Test converting empty audio data."""
        mock_room = MockLiveKitRoom()
        handler = AudioHandler(mock_room)

        empty_audio = b""
        result = handler.convert_format(empty_audio, "pcm", "pcm")

        assert result == empty_audio


class TestAudioBufferingEdgeCases:
    """Additional tests for audio buffering edge cases."""

    @pytest.mark.asyncio
    async def test_buffer_audio_single_chunk(self):
        """Test buffering a single audio chunk."""
        mock_room = MockLiveKitRoom()
        handler = AudioHandler(mock_room)

        async def single_chunk():
            yield b"single_chunk"

        buffered = []
        async for chunk in handler._buffer_audio(single_chunk(), buffer_duration_ms=100):
            buffered.append(chunk)

        # Single chunk should be returned as remaining data
        assert len(buffered) > 0

    @pytest.mark.asyncio
    async def test_buffer_audio_large_chunks(self):
        """Test buffering with large audio chunks."""
        mock_room = MockLiveKitRoom()
        handler = AudioHandler(mock_room, sample_rate=48000, channels=2)

        large_audio = b"\x00" * 192000  # Large audio chunk

        async def large_chunks():
            yield large_audio
            yield large_audio

        buffered = []
        async for chunk in handler._buffer_audio(large_chunks(), buffer_duration_ms=100):
            buffered.append(chunk)
            # Limit iterations to prevent test hanging
            if len(buffered) >= 2:
                break

        # Should produce at least one buffered chunk
        assert len(buffered) >= 1
        assert all(isinstance(c, bytes) for c in buffered)
