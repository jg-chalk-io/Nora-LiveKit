"""Sanitized TTS wrapper for Nora voice agent.

Wraps any LiveKit TTS plugin to sanitize LLM output before synthesis.
This handles cases where LLMs output function call syntax as text.

IMPORTANT: This uses composition/delegation rather than inheritance to avoid
issues with LiveKit's abstract base classes requiring internal methods like _run.
"""

import structlog
from livekit.agents import tts, APIConnectOptions

from nora_livekit.nora.text_processor import NoraTextProcessor

logger = structlog.get_logger(__name__)

# Shared text processor instance
_text_processor = NoraTextProcessor()

# Default connection options
_DEFAULT_CONN_OPTIONS = APIConnectOptions(max_retry=3, retry_interval=2.0, timeout=10.0)


class SanitizedTTS(tts.TTS):
    """TTS wrapper that sanitizes text before synthesis.

    Removes function call syntax and other artifacts that LLMs
    sometimes output as text instead of using proper tool calling.
    """

    def __init__(self, wrapped_tts: tts.TTS) -> None:
        """Initialize with a wrapped TTS instance.

        Args:
            wrapped_tts: The underlying TTS to use (e.g., deepgram.TTS)
        """
        # Initialize parent with same capabilities
        super().__init__(
            capabilities=wrapped_tts.capabilities,
            sample_rate=wrapped_tts.sample_rate,
            num_channels=wrapped_tts.num_channels,
        )
        self._wrapped = wrapped_tts
        self._processor = _text_processor

    def synthesize(
        self,
        text: str,
        *,
        conn_options: APIConnectOptions = _DEFAULT_CONN_OPTIONS,
    ) -> tts.ChunkedStream:
        """Synthesize speech from sanitized text.

        Args:
            text: Text to synthesize (will be sanitized first)
            conn_options: Connection options for the TTS API

        Returns:
            ChunkedStream of audio data
        """
        # Sanitize text before synthesis
        sanitized = self._processor.process_for_tts(text, use_ssml=False)

        if sanitized != text:
            logger.info(
                "sanitized_tts.text_cleaned",
                original_len=len(text),
                sanitized_len=len(sanitized),
                original_preview=text[:100] if len(text) > 100 else text,
                sanitized_preview=sanitized[:100] if len(sanitized) > 100 else sanitized,
            )

        # Pass sanitized text to underlying TTS
        return self._wrapped.synthesize(sanitized, conn_options=conn_options)

    def stream(
        self,
        *,
        conn_options: APIConnectOptions = _DEFAULT_CONN_OPTIONS,
    ) -> tts.SynthesizeStream:
        """Create a streaming synthesis session.

        For streaming, we return a wrapped stream that sanitizes text
        before passing to the underlying TTS. The wrapper uses composition
        rather than inheritance to avoid abstract method requirements.

        Args:
            conn_options: Connection options for the TTS API

        Returns:
            SynthesizeStream for incremental text input
        """
        underlying_stream = self._wrapped.stream(conn_options=conn_options)
        return SanitizedSynthesizeStream(underlying_stream, self._processor)


class SanitizedSynthesizeStream:
    """Wrapped SynthesizeStream that sanitizes pushed text.

    Uses composition/delegation pattern - does NOT inherit from tts.SynthesizeStream
    to avoid needing to implement abstract methods like _run.
    All method calls are delegated to the wrapped stream.
    """

    def __init__(
        self,
        wrapped_stream: tts.SynthesizeStream,
        processor: NoraTextProcessor,
    ) -> None:
        """Initialize with wrapped stream and processor.

        Args:
            wrapped_stream: Underlying synthesis stream
            processor: Text processor for sanitization
        """
        self._wrapped = wrapped_stream
        self._processor = processor
        self._buffer = ""

    def push_text(self, text: str) -> None:
        """Push text to the synthesis stream after sanitization.

        Args:
            text: Text chunk to synthesize
        """
        # Buffer text to handle partial function calls across chunks
        self._buffer += text

        # Sanitize the buffered text
        sanitized = self._processor.sanitize_function_calls(self._buffer)

        # If buffer looks complete (ends with sentence terminator), flush
        if sanitized and sanitized[-1] in '.?!':
            if sanitized:
                self._wrapped.push_text(sanitized)
            self._buffer = ""
        elif len(self._buffer) > 500:
            # Flush if buffer gets too long
            if sanitized:
                self._wrapped.push_text(sanitized)
            self._buffer = ""

    def flush(self) -> None:
        """Flush any remaining buffered text."""
        if self._buffer:
            sanitized = self._processor.sanitize_function_calls(self._buffer)
            if sanitized:
                self._wrapped.push_text(sanitized)
            self._buffer = ""
        self._wrapped.flush()

    def end_input(self) -> None:
        """Signal end of input."""
        self.flush()
        self._wrapped.end_input()

    async def aclose(self) -> None:
        """Close the stream."""
        await self._wrapped.aclose()

    def __aiter__(self):
        """Iterate over audio chunks from underlying stream."""
        return self._wrapped.__aiter__()

    async def __anext__(self):
        """Get next audio chunk from underlying stream."""
        return await self._wrapped.__anext__()

    # Delegate all other attributes to wrapped stream for compatibility
    def __getattr__(self, name):
        """Delegate unknown attributes to wrapped stream."""
        return getattr(self._wrapped, name)

    # Context manager support - delegate to wrapped stream
    async def __aenter__(self):
        """Enter async context."""
        if hasattr(self._wrapped, '__aenter__'):
            await self._wrapped.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context."""
        if hasattr(self._wrapped, '__aexit__'):
            return await self._wrapped.__aexit__(exc_type, exc_val, exc_tb)
        await self.aclose()
        return False


def wrap_tts(tts_instance: tts.TTS) -> SanitizedTTS:
    """Convenience function to wrap a TTS instance.

    Args:
        tts_instance: TTS to wrap (e.g., deepgram.TTS())

    Returns:
        SanitizedTTS wrapper
    """
    logger.info("sanitized_tts.wrapper_created", wrapped_type=type(tts_instance).__name__)
    return SanitizedTTS(tts_instance)
