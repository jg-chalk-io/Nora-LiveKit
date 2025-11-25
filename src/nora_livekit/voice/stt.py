"""Deepgram speech-to-text integration for real-time transcription."""

import asyncio
import structlog
from dataclasses import dataclass
from typing import AsyncIterator, Optional

from livekit.plugins.deepgram import STT as DeepgramPluginSTT

logger = structlog.get_logger(__name__)


@dataclass
class TranscriptionResult:
    """Result from speech-to-text transcription."""

    text: str
    is_final: bool
    confidence: Optional[float] = None


class DeepgramSTT:
    """Deepgram speech-to-text integration for real-time transcription.

    Integrates with LiveKit plugins for Deepgram STT with support for
    interim results, retry logic, and confidence scores.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "nova-2",
        language: str = "en-US",
        interim_results: bool = True,
        max_retries: int = 3,
    ) -> None:
        """Initialize Deepgram STT client using LiveKit plugin.

        Args:
            api_key: Deepgram API key
            model: STT model to use (default: nova-2)
            language: Language code (default: en-US)
            interim_results: Enable interim results (default: True)
            max_retries: Maximum retry attempts for transient errors (default: 3)

        Raises:
            ValueError: If API key is empty or whitespace-only
        """
        if not api_key or not api_key.strip():
            raise ValueError("API key cannot be empty")

        self.api_key = api_key
        self.model = model
        self.language = language
        self.interim_results = interim_results
        self.max_retries = max_retries
        self._connected = False
        self._plugin = DeepgramPluginSTT(
            api_key=api_key,
            model=model,
            language=language,
            interim_results=interim_results,
        )

    async def connect(self) -> None:
        """Establish connection to Deepgram API.

        Raises:
            RuntimeError: If connection fails
        """
        logger.info("voice.stt.connecting", model=self.model)
        try:
            # LiveKit plugin handles connection internally
            # Verify plugin is available
            if self._plugin is None:
                raise RuntimeError("Deepgram plugin failed to initialize")
            self._connected = True
            logger.info("voice.stt.connected")
        except Exception as e:
            logger.error("voice.stt.connection_error", error=str(e))
            self._connected = False
            raise

    async def disconnect(self) -> None:
        """Close connection and cleanup."""
        logger.info("voice.stt.disconnecting")
        self._connected = False
        logger.info("voice.stt.disconnected")

    async def transcribe_stream(
        self,
        audio_stream: AsyncIterator[bytes],
    ) -> AsyncIterator[TranscriptionResult]:
        """Stream audio to Deepgram and yield transcription results.

        Uses exponential backoff retry for transient errors:
        - 1s, 2s, 4s (max 3 attempts by default)

        Note: This implementation buffers the audio stream and sends it to Deepgram
        for processing. The actual LiveKit plugin integration happens through
        the internal _plugin instance which handles AudioFrame conversion.

        Args:
            audio_stream: Async iterator of audio chunks (bytes)

        Yields:
            TranscriptionResult objects with transcription text

        Raises:
            RuntimeError: If not connected or all retries exhausted
        """
        if not self._connected:
            raise RuntimeError("Not connected to Deepgram API")

        logger.info("voice.stt.transcription_started")

        retry_count = 0
        last_error: Optional[Exception] = None

        while retry_count < self.max_retries:
            try:
                # recognize() returns an async generator
                recognition_stream = await self._plugin.recognize(audio_stream)
                async for deepgram_result in recognition_stream:
                    result = await self._handle_deepgram_message(
                        {
                            "text": deepgram_result.text,
                            "is_final": deepgram_result.is_final,
                            "confidence": getattr(
                                deepgram_result, "confidence", None
                            ),
                        }
                    )
                    yield result

                logger.info("voice.stt.transcription_completed")
                return

            except (ConnectionError, TimeoutError) as e:
                # Transient error - retry with exponential backoff
                retry_count += 1
                last_error = e

                if retry_count < self.max_retries:
                    wait_time = 2 ** (retry_count - 1)  # 1s, 2s, 4s
                    logger.warning(
                        "voice.stt.transient_error",
                        error=str(e),
                        retry=retry_count,
                        wait_seconds=wait_time,
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(
                        "voice.stt.max_retries_exceeded",
                        error=str(e),
                        total_retries=self.max_retries,
                    )
                    raise

            except Exception as e:
                # Permanent error - fail immediately
                logger.error("voice.stt.transcription_error", error=str(e))
                raise

        # If we exhausted retries
        if last_error:
            raise last_error

    @property
    def is_connected(self) -> bool:
        """Check if connected to Deepgram API."""
        return self._connected

    async def _handle_deepgram_message(self, message: dict[str, object]) -> TranscriptionResult:
        """Parse Deepgram plugin results into structured results.

        Args:
            message: Dictionary with text, is_final, and confidence

        Returns:
            Parsed TranscriptionResult
        """
        return TranscriptionResult(
            text=message.get("text", ""),
            is_final=message.get("is_final", False),
            confidence=message.get("confidence"),
        )
