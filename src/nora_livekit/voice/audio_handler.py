"""LiveKit audio track handling for voice pipeline."""

import asyncio
import structlog
from typing import AsyncIterator, Any

logger = structlog.get_logger(__name__)


class AudioHandler:
    """Manages LiveKit audio track publishing and subscription.

    Handles bidirectional audio communication with LiveKit rooms,
    including format conversion and buffering for smooth playback.
    """

    def __init__(
        self,
        room: Any,
        sample_rate: int = 16000,
        channels: int = 1,
    ) -> None:
        """Initialize audio handler for LiveKit room.

        Args:
            room: LiveKit Room instance
            sample_rate: Audio sample rate in Hz (default: 16000)
            channels: Number of audio channels (default: 1 = mono)
        """
        self.room = room
        self.sample_rate = sample_rate
        self.channels = channels

    async def subscribe_to_participant_audio(
        self,
        participant_id: str,
    ) -> AsyncIterator[bytes]:
        """Subscribe to participant's audio track and yield audio chunks.

        Args:
            participant_id: ID of participant to subscribe to

        Yields:
            Audio data chunks as bytes
        """
        logger.info(
            "voice.audio.subscribed",
            participant_id=participant_id,
            sample_rate=self.sample_rate,
        )

        try:
            # Get participant from room
            participant = await self.room.get_participant(participant_id)

            # Get audio track from participant
            audio_track = await participant.get_audio_track()

            # Get audio stream and yield chunks
            audio_stream = await audio_track.get_audio_stream()

            async for chunk in audio_stream:
                yield chunk

        except Exception as e:
            logger.error(
                "voice.audio.subscription_error",
                participant_id=participant_id,
                error=str(e),
            )
            raise

    async def publish_audio(
        self,
        audio_stream: AsyncIterator[bytes],
    ) -> None:
        """Publish audio stream to LiveKit track for playback.

        Args:
            audio_stream: Async iterator yielding audio chunks
        """
        logger.info("voice.audio.publishing_started")

        try:
            # Get or create agent audio track
            audio_track = await self._get_agent_audio_track()

            # Publish audio chunks
            async for chunk in audio_stream:
                await audio_track.publish(chunk)

            logger.info("voice.audio.publishing_completed")

        except Exception as e:
            logger.error("voice.audio.publishing_error", error=str(e))
            raise

    async def _get_agent_audio_track(self) -> Any:
        """Get or create agent's audio track in room.

        Returns:
            Audio track for agent publishing

        Raises:
            RuntimeError: If unable to get audio track from room
        """
        # In a real implementation, this would get the actual agent's
        # audio track from the LiveKit room
        if not hasattr(self.room, "audio_track"):
            raise RuntimeError("Room does not have audio track")

        return self.room.audio_track

    def convert_format(
        self,
        audio: bytes,
        source_format: str,
        target_format: str,
    ) -> bytes:
        """Convert audio between formats (PCM, WAV, etc.).

        Args:
            audio: Audio data to convert
            source_format: Source format (e.g., 'pcm', 'wav')
            target_format: Target format (e.g., 'pcm', 'wav')

        Returns:
            Converted audio data

        Note:
            For this implementation, we focus on PCM which is the
            primary format. Full format conversion would require
            additional audio processing libraries.
        """
        logger.debug(
            "voice.audio.format_conversion",
            source_format=source_format,
            target_format=target_format,
            audio_size=len(audio),
        )

        # If formats are the same, return as-is
        if source_format == target_format:
            return audio

        # For now, return audio as-is for unsupported conversions
        # In a full implementation, would use numpy/scipy for conversion
        return audio

    async def _buffer_audio(
        self,
        audio_stream: AsyncIterator[bytes],
        buffer_duration_ms: int = 100,
    ) -> AsyncIterator[bytes]:
        """Buffer audio stream to smooth playback.

        Collects audio chunks and yields them at regular intervals
        to handle network jitter and variable chunk arrival times.

        Args:
            audio_stream: Input audio stream to buffer
            buffer_duration_ms: Buffer duration in milliseconds

        Yields:
            Buffered audio chunks
        """
        buffer: list[bytes] = []
        buffer_size = max(1, (self.sample_rate * self.channels * 2 * buffer_duration_ms) // 1000)

        try:
            async for chunk in audio_stream:
                buffer.append(chunk)

                # Yield buffered data when buffer is full
                total_size = sum(len(b) for b in buffer)
                if total_size >= buffer_size:
                    # Concatenate buffered chunks
                    buffered_chunk = b"".join(buffer)
                    yield buffered_chunk
                    buffer = []

            # Yield remaining buffered data
            if buffer:
                remaining = b"".join(buffer)
                if remaining:
                    yield remaining

        except Exception as e:
            logger.error("voice.audio.buffering_error", error=str(e))
            raise
