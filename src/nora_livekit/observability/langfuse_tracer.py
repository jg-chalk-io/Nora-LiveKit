"""Langfuse tracer for Nora voice agent observability.

Tracks:
- LLM calls with latency, tokens, and cost
- STT transcriptions with audio duration and word count
- TTS synthesis with character count and latency
- Full conversation turns from user speech to assistant response
- Tool executions with parameters and results

Environment Variables:
    LANGFUSE_PUBLIC_KEY: Langfuse public key (required)
    LANGFUSE_SECRET_KEY: Langfuse secret key (required)
    LANGFUSE_HOST: Langfuse host URL (default: https://cloud.langfuse.com)
    LANGFUSE_ENABLED: Enable/disable tracing (default: true)
"""

import os
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Generator, Optional

import structlog
from langfuse import Langfuse

logger = structlog.get_logger(__name__)

# Type aliases for Langfuse objects (actual types are internal)
StatefulTraceClient = Any
StatefulSpanClient = Any

# Global tracer instance
_tracer: Optional["NoraLangfuseTracer"] = None


@dataclass
class TurnMetrics:
    """Metrics for a single conversation turn."""

    # Timing (all in milliseconds)
    stt_start_ms: float = 0
    stt_end_ms: float = 0
    llm_start_ms: float = 0
    llm_end_ms: float = 0
    tts_start_ms: float = 0
    tts_end_ms: float = 0

    # STT metrics
    audio_duration_ms: float = 0
    transcript_word_count: int = 0
    stt_confidence: float = 0

    # LLM metrics
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    llm_model: str = ""

    # TTS metrics
    tts_character_count: int = 0
    tts_audio_duration_ms: float = 0

    # Overall
    turn_id: str = ""
    user_text: str = ""
    assistant_text: str = ""

    @property
    def stt_latency_ms(self) -> float:
        """Time from audio start to transcript ready."""
        return self.stt_end_ms - self.stt_start_ms if self.stt_end_ms else 0

    @property
    def llm_latency_ms(self) -> float:
        """Time from prompt sent to response received."""
        return self.llm_end_ms - self.llm_start_ms if self.llm_end_ms else 0

    @property
    def tts_latency_ms(self) -> float:
        """Time to first audio byte from TTS."""
        return self.tts_end_ms - self.tts_start_ms if self.tts_end_ms else 0

    @property
    def total_latency_ms(self) -> float:
        """Total turn latency from user speech end to assistant speech start."""
        # STT end -> LLM -> TTS start
        if self.stt_end_ms and self.tts_start_ms:
            return self.tts_start_ms - self.stt_end_ms
        return self.stt_latency_ms + self.llm_latency_ms + self.tts_latency_ms


class NoraLangfuseTracer:
    """Langfuse tracer for comprehensive voice agent observability."""

    def __init__(
        self,
        public_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        host: str = "https://cloud.langfuse.com",
        enabled: bool = True,
        session_id: Optional[str] = None,
    ) -> None:
        """Initialize Langfuse tracer.

        Args:
            public_key: Langfuse public key (or LANGFUSE_PUBLIC_KEY env var)
            secret_key: Langfuse secret key (or LANGFUSE_SECRET_KEY env var)
            host: Langfuse host URL
            enabled: Whether tracing is enabled
            session_id: Optional session ID for grouping traces
        """
        self.enabled = enabled and bool(public_key or os.getenv("LANGFUSE_PUBLIC_KEY"))

        if not self.enabled:
            logger.info("langfuse.disabled", reason="No API keys provided")
            self.langfuse = None
            return

        try:
            self.langfuse = Langfuse(
                public_key=public_key or os.getenv("LANGFUSE_PUBLIC_KEY"),
                secret_key=secret_key or os.getenv("LANGFUSE_SECRET_KEY"),
                host=host,
            )
        except Exception as e:
            logger.warning("langfuse.init_failed", error=str(e))
            self.langfuse = None
            self.enabled = False
            return

        self.session_id = session_id
        self._current_trace: Optional[Any] = None
        self._current_turn: Optional[TurnMetrics] = None
        self._turn_span: Optional[Any] = None

        logger.info("langfuse.initialized", host=host, session_id=session_id)

    def start_conversation(
        self,
        caller_phone: str = "",
        office_name: str = "",
        metadata: Optional[dict] = None,
    ) -> Optional[Any]:
        """Start a new conversation trace.

        Args:
            caller_phone: Caller's phone number
            office_name: Office/clinic name
            metadata: Additional metadata

        Returns:
            Trace ID or None
        """
        if not self.enabled or not self.langfuse:
            return None

        try:
            # Langfuse v3 uses create_trace_id for manual tracing
            trace_id = self.langfuse.create_trace_id()
            self._current_trace = trace_id

            # Log the conversation start as a structured event
            logger.info(
                "langfuse.conversation_started",
                trace_id=trace_id,
                caller_phone=caller_phone[:4] + "..." if caller_phone else "unknown",
                office_name=office_name,
            )

            return trace_id
        except Exception as e:
            logger.warning("langfuse.start_conversation_failed", error=str(e))
            return None

    def end_conversation(
        self,
        outcome: str = "completed",
        metadata: Optional[dict] = None,
    ) -> None:
        """End the current conversation trace.

        Args:
            outcome: Conversation outcome (completed, transferred, dropped, etc.)
            metadata: Additional metadata
        """
        if not self._current_trace:
            return

        try:
            # Flush to ensure all events are sent
            if self.langfuse:
                self.langfuse.flush()

            logger.info(
                "langfuse.conversation_ended",
                trace_id=self._current_trace,
                outcome=outcome,
            )
        except Exception as e:
            logger.warning("langfuse.end_conversation_failed", error=str(e))

        self._current_trace = None

    def start_turn(self, turn_id: str = "") -> TurnMetrics:
        """Start tracking a conversation turn.

        A turn is: User speaks -> STT -> LLM -> TTS -> Assistant speaks

        Args:
            turn_id: Optional turn identifier

        Returns:
            TurnMetrics object for this turn
        """
        self._current_turn = TurnMetrics(
            turn_id=turn_id or f"turn-{int(time.time() * 1000)}",
        )

        if self._current_trace:
            self._turn_span = self._current_trace.span(
                name="conversation-turn",
                metadata={"turn_id": self._current_turn.turn_id},
            )

        return self._current_turn

    def end_turn(self) -> Optional[TurnMetrics]:
        """End the current turn and log metrics.

        Returns:
            Completed TurnMetrics
        """
        if not self._current_turn:
            return None

        turn = self._current_turn

        # Log turn summary
        if self._turn_span:
            self._turn_span.end(
                output={
                    "user_text": turn.user_text,
                    "assistant_text": turn.assistant_text,
                },
                metadata={
                    "latency": {
                        "stt_ms": turn.stt_latency_ms,
                        "llm_ms": turn.llm_latency_ms,
                        "tts_ms": turn.tts_latency_ms,
                        "total_ms": turn.total_latency_ms,
                    },
                    "tokens": {
                        "prompt": turn.prompt_tokens,
                        "completion": turn.completion_tokens,
                        "total": turn.total_tokens,
                    },
                    "stt": {
                        "audio_duration_ms": turn.audio_duration_ms,
                        "word_count": turn.transcript_word_count,
                        "confidence": turn.stt_confidence,
                    },
                    "tts": {
                        "character_count": turn.tts_character_count,
                        "audio_duration_ms": turn.tts_audio_duration_ms,
                    },
                },
            )

        logger.info(
            "langfuse.turn_completed",
            turn_id=turn.turn_id,
            total_latency_ms=turn.total_latency_ms,
            stt_ms=turn.stt_latency_ms,
            llm_ms=turn.llm_latency_ms,
            tts_ms=turn.tts_latency_ms,
        )

        self._current_turn = None
        self._turn_span = None

        return turn

    @contextmanager
    def trace_stt(
        self,
        model: str = "nova-3",
        language: str = "en",
    ) -> Generator[dict, None, None]:
        """Context manager for tracing STT transcription.

        Args:
            model: STT model name
            language: Language code

        Yields:
            Dict to populate with results (transcript, confidence, etc.)
        """
        result: dict = {}
        start_time = time.time() * 1000

        if self._current_turn:
            self._current_turn.stt_start_ms = start_time

        span = None
        if self._turn_span:
            span = self._turn_span.span(
                name="stt-transcription",
                input={"model": model, "language": language},
            )

        try:
            yield result
        finally:
            end_time = time.time() * 1000

            if self._current_turn:
                self._current_turn.stt_end_ms = end_time
                self._current_turn.user_text = result.get("transcript", "")
                self._current_turn.transcript_word_count = len(
                    result.get("transcript", "").split()
                )
                self._current_turn.stt_confidence = result.get("confidence", 0)
                self._current_turn.audio_duration_ms = result.get("audio_duration_ms", 0)

            if span:
                span.end(
                    output=result,
                    metadata={
                        "latency_ms": end_time - start_time,
                        "word_count": len(result.get("transcript", "").split()),
                    },
                )

    @contextmanager
    def trace_llm(
        self,
        model: str = "gpt-4o-mini",
        messages: Optional[list] = None,
    ) -> Generator[dict, None, None]:
        """Context manager for tracing LLM generation.

        Args:
            model: LLM model name
            messages: Input messages

        Yields:
            Dict to populate with results (response, tokens, etc.)
        """
        result: dict = {}
        start_time = time.time() * 1000

        if self._current_turn:
            self._current_turn.llm_start_ms = start_time
            self._current_turn.llm_model = model

        generation = None
        if self._turn_span:
            generation = self._turn_span.generation(
                name="llm-generation",
                model=model,
                input=messages,
            )

        try:
            yield result
        finally:
            end_time = time.time() * 1000

            if self._current_turn:
                self._current_turn.llm_end_ms = end_time
                self._current_turn.assistant_text = result.get("response", "")
                self._current_turn.prompt_tokens = result.get("prompt_tokens", 0)
                self._current_turn.completion_tokens = result.get("completion_tokens", 0)
                self._current_turn.total_tokens = result.get("total_tokens", 0)

            if generation:
                generation.end(
                    output=result.get("response", ""),
                    usage={
                        "prompt_tokens": result.get("prompt_tokens", 0),
                        "completion_tokens": result.get("completion_tokens", 0),
                        "total_tokens": result.get("total_tokens", 0),
                    },
                    metadata={
                        "latency_ms": end_time - start_time,
                        "finish_reason": result.get("finish_reason", ""),
                    },
                )

    @contextmanager
    def trace_tts(
        self,
        voice_id: str = "",
        text: str = "",
    ) -> Generator[dict, None, None]:
        """Context manager for tracing TTS synthesis.

        Args:
            voice_id: TTS voice ID
            text: Text to synthesize

        Yields:
            Dict to populate with results (audio_duration_ms, etc.)
        """
        result: dict = {}
        start_time = time.time() * 1000

        if self._current_turn:
            self._current_turn.tts_start_ms = start_time
            self._current_turn.tts_character_count = len(text)

        span = None
        if self._turn_span:
            span = self._turn_span.span(
                name="tts-synthesis",
                input={"voice_id": voice_id, "text_length": len(text)},
            )

        try:
            yield result
        finally:
            end_time = time.time() * 1000

            if self._current_turn:
                self._current_turn.tts_end_ms = end_time
                self._current_turn.tts_audio_duration_ms = result.get("audio_duration_ms", 0)

            if span:
                span.end(
                    output={"audio_duration_ms": result.get("audio_duration_ms", 0)},
                    metadata={
                        "latency_ms": end_time - start_time,
                        "character_count": len(text),
                    },
                )

    def trace_tool_call(
        self,
        tool_name: str,
        parameters: dict,
        result: str,
        latency_ms: float = 0,
    ) -> None:
        """Trace a tool/function call.

        Args:
            tool_name: Name of the tool
            parameters: Tool parameters
            result: Tool result
            latency_ms: Call latency in milliseconds
        """
        if not self._turn_span:
            return

        self._turn_span.span(
            name=f"tool-{tool_name}",
            input=parameters,
            output=result,
            metadata={"latency_ms": latency_ms},
        ).end()

        logger.info(
            "langfuse.tool_traced",
            tool=tool_name,
            latency_ms=latency_ms,
        )

    def flush(self) -> None:
        """Flush all pending events to Langfuse."""
        if self.langfuse:
            self.langfuse.flush()


def init_langfuse(
    public_key: Optional[str] = None,
    secret_key: Optional[str] = None,
    host: str = "https://cloud.langfuse.com",
    session_id: Optional[str] = None,
) -> NoraLangfuseTracer:
    """Initialize the global Langfuse tracer.

    Args:
        public_key: Langfuse public key
        secret_key: Langfuse secret key
        host: Langfuse host URL
        session_id: Session ID for grouping traces

    Returns:
        Initialized NoraLangfuseTracer
    """
    global _tracer

    enabled = os.getenv("LANGFUSE_ENABLED", "true").lower() == "true"

    _tracer = NoraLangfuseTracer(
        public_key=public_key,
        secret_key=secret_key,
        host=host,
        enabled=enabled,
        session_id=session_id,
    )

    return _tracer


def get_tracer() -> Optional[NoraLangfuseTracer]:
    """Get the global Langfuse tracer instance.

    Returns:
        NoraLangfuseTracer or None if not initialized
    """
    return _tracer
