"""Langfuse tracer for Nora voice agent observability.

Uses Langfuse SDK v3 (OTEL-based) API.

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
from dataclasses import dataclass
from typing import Any, Optional

import structlog

logger = structlog.get_logger(__name__)

# Global tracer instance
_tracer: Optional["NoraLangfuseTracer"] = None


@dataclass
class ConversationMetrics:
    """Accumulated metrics for a conversation session."""

    # Counts
    total_turns: int = 0
    total_tool_calls: int = 0

    # STT metrics
    stt_total_duration_ms: float = 0
    stt_total_characters: int = 0

    # LLM metrics
    llm_total_prompt_tokens: int = 0
    llm_total_completion_tokens: int = 0
    llm_total_latency_ms: float = 0

    # TTS metrics
    tts_total_characters: int = 0
    tts_total_latency_ms: float = 0

    # Pipeline latency (end-to-end)
    total_pipeline_latency_ms: float = 0


class NoraLangfuseTracer:
    """Langfuse tracer for comprehensive voice agent observability.

    Uses Langfuse SDK v3 API with manual span management.
    Integrates with LiveKit's metrics_collected events.
    """

    def __init__(
        self,
        public_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        host: Optional[str] = None,
        enabled: bool = True,
        session_id: Optional[str] = None,
    ) -> None:
        """Initialize Langfuse tracer.

        Args:
            public_key: Langfuse public key (or LANGFUSE_PUBLIC_KEY env var)
            secret_key: Langfuse secret key (or LANGFUSE_SECRET_KEY env var)
            host: Langfuse host URL (or LANGFUSE_HOST env var)
            enabled: Whether tracing is enabled
            session_id: Optional session ID for grouping traces
        """
        self.public_key = public_key or os.getenv("LANGFUSE_PUBLIC_KEY")
        self.secret_key = secret_key or os.getenv("LANGFUSE_SECRET_KEY")
        self.host = host or os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")

        self.enabled = enabled and bool(self.public_key)

        if not self.enabled:
            logger.info("langfuse.disabled", reason="No API keys provided")
            self.langfuse = None
            return

        try:
            # Set environment variables for Langfuse SDK v3
            if self.public_key:
                os.environ["LANGFUSE_PUBLIC_KEY"] = self.public_key
            if self.secret_key:
                os.environ["LANGFUSE_SECRET_KEY"] = self.secret_key
            if self.host:
                os.environ["LANGFUSE_HOST"] = self.host

            # Import and get the v3 client
            from langfuse import get_client

            self.langfuse = get_client()
        except Exception as e:
            logger.warning("langfuse.init_failed", error=str(e))
            self.langfuse = None
            self.enabled = False
            return

        self.session_id = session_id
        self._root_span: Optional[Any] = None
        self._metrics = ConversationMetrics()

        logger.info("langfuse.initialized", host=self.host, session_id=session_id)

    def start_conversation(
        self,
        caller_phone: str = "",
        office_name: str = "",
        metadata: Optional[dict] = None,
    ) -> Optional[Any]:
        """Start a new conversation trace.

        In Langfuse v3, traces are created implicitly by the first span.
        We create a root span to represent the conversation.

        Args:
            caller_phone: Caller's phone number
            office_name: Office/clinic name
            metadata: Additional metadata

        Returns:
            Root span object or None
        """
        if not self.enabled or not self.langfuse:
            return None

        try:
            # Build trace metadata
            trace_metadata = {
                "caller_phone": caller_phone[:4] + "..." if caller_phone else "unknown",
                "office_name": office_name,
                "agent": "nora",
                "platform": "livekit",
                **(metadata or {}),
            }

            # Create root span - this implicitly creates the trace in v3
            self._root_span = self.langfuse.start_span(
                name="nora-conversation",
                metadata=trace_metadata,
            )

            # Reset metrics for new conversation
            self._metrics = ConversationMetrics()

            logger.info(
                "langfuse.conversation_started",
                office_name=office_name,
            )

            return self._root_span
        except Exception as e:
            logger.warning("langfuse.start_conversation_failed", error=str(e))
            return None

    def end_conversation(
        self,
        outcome: str = "completed",
        metadata: Optional[dict] = None,
    ) -> None:
        """End the current conversation trace with summary metrics.

        Args:
            outcome: Conversation outcome (completed, transferred, dropped, etc.)
            metadata: Additional metadata
        """
        if not self._root_span:
            return

        try:
            # Build summary output
            summary = {
                "outcome": outcome,
                "metrics": {
                    "total_turns": self._metrics.total_turns,
                    "total_tool_calls": self._metrics.total_tool_calls,
                    "stt": {
                        "total_duration_ms": self._metrics.stt_total_duration_ms,
                        "total_characters": self._metrics.stt_total_characters,
                    },
                    "llm": {
                        "prompt_tokens": self._metrics.llm_total_prompt_tokens,
                        "completion_tokens": self._metrics.llm_total_completion_tokens,
                        "total_latency_ms": self._metrics.llm_total_latency_ms,
                    },
                    "tts": {
                        "total_characters": self._metrics.tts_total_characters,
                        "total_latency_ms": self._metrics.tts_total_latency_ms,
                    },
                    "pipeline_latency_ms": self._metrics.total_pipeline_latency_ms,
                },
                **(metadata or {}),
            }

            # Update and end root span
            self._root_span.update(output=summary)
            self._root_span.end()

            # Flush to ensure all events are sent
            if self.langfuse:
                self.langfuse.flush()

            logger.info(
                "langfuse.conversation_ended",
                outcome=outcome,
                total_turns=self._metrics.total_turns,
            )
        except Exception as e:
            logger.warning("langfuse.end_conversation_failed", error=str(e))

        self._root_span = None

    def trace_metrics(self, metrics: Any) -> None:
        """Process LiveKit metrics_collected event and send to Langfuse.

        This is the main integration point with LiveKit's metrics system.
        Called from session.on("metrics_collected") handler.

        Args:
            metrics: LiveKit AgentMetrics object
        """
        if not self._root_span:
            return

        try:
            # Process different metric types from LiveKit
            for metric in metrics:
                metric_type = type(metric).__name__

                if metric_type == "STTMetrics":
                    self._trace_stt_metrics(metric)
                elif metric_type == "LLMMetrics":
                    self._trace_llm_metrics(metric)
                elif metric_type == "TTSMetrics":
                    self._trace_tts_metrics(metric)
                elif metric_type == "PipelineMetrics":
                    self._trace_pipeline_metrics(metric)

        except Exception as e:
            logger.warning("langfuse.trace_metrics_failed", error=str(e))

    def _trace_stt_metrics(self, metric: Any) -> None:
        """Trace STT (speech-to-text) metrics."""
        if not self._root_span:
            return

        try:
            duration_ms = getattr(metric, "duration", 0) * 1000
            audio_duration_ms = getattr(metric, "audio_duration", 0) * 1000

            # Create child span for STT under root
            span = self._root_span.start_span(
                name="stt-transcription",
                input={"audio_duration_ms": audio_duration_ms},
                metadata={
                    "duration_ms": duration_ms,
                    "streamed": getattr(metric, "streamed", False),
                },
            )
            span.update(output={"transcript": getattr(metric, "transcript", "")})
            span.end()

            # Accumulate metrics
            self._metrics.stt_total_duration_ms += duration_ms
            self._metrics.stt_total_characters += len(getattr(metric, "transcript", ""))

            logger.debug(
                "langfuse.stt_traced",
                duration_ms=duration_ms,
                audio_duration_ms=audio_duration_ms,
            )
        except Exception as e:
            logger.warning("langfuse.stt_trace_failed", error=str(e))

    def _trace_llm_metrics(self, metric: Any) -> None:
        """Trace LLM (language model) metrics."""
        if not self._root_span:
            return

        try:
            ttft_ms = getattr(metric, "ttft", 0) * 1000  # Time to first token
            duration_ms = getattr(metric, "duration", 0) * 1000
            prompt_tokens = getattr(metric, "prompt_tokens", 0)
            completion_tokens = getattr(metric, "completion_tokens", 0)

            # Create generation span for LLM under root
            generation = self._root_span.start_generation(
                name="llm-generation",
                model=getattr(metric, "model", "unknown"),
                input={"request_id": getattr(metric, "request_id", "")},
                metadata={
                    "ttft_ms": ttft_ms,
                    "duration_ms": duration_ms,
                    "cancelled": getattr(metric, "cancelled", False),
                },
            )
            generation.update(
                output=getattr(metric, "content", ""),
                usage={
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": prompt_tokens + completion_tokens,
                },
            )
            generation.end()

            # Accumulate metrics
            self._metrics.llm_total_prompt_tokens += prompt_tokens
            self._metrics.llm_total_completion_tokens += completion_tokens
            self._metrics.llm_total_latency_ms += duration_ms
            self._metrics.total_turns += 1

            logger.debug(
                "langfuse.llm_traced",
                ttft_ms=ttft_ms,
                duration_ms=duration_ms,
                tokens=prompt_tokens + completion_tokens,
            )
        except Exception as e:
            logger.warning("langfuse.llm_trace_failed", error=str(e))

    def _trace_tts_metrics(self, metric: Any) -> None:
        """Trace TTS (text-to-speech) metrics."""
        if not self._root_span:
            return

        try:
            ttfb_ms = getattr(metric, "ttfb", 0) * 1000  # Time to first byte
            duration_ms = getattr(metric, "duration", 0) * 1000
            characters = getattr(metric, "characters_count", 0)

            # Create span for TTS under root
            span = self._root_span.start_span(
                name="tts-synthesis",
                input={"characters": characters},
                metadata={
                    "ttfb_ms": ttfb_ms,
                    "duration_ms": duration_ms,
                    "streamed": getattr(metric, "streamed", False),
                    "cancelled": getattr(metric, "cancelled", False),
                },
            )
            span.update(output={"audio_duration_ms": getattr(metric, "audio_duration", 0) * 1000})
            span.end()

            # Accumulate metrics
            self._metrics.tts_total_characters += characters
            self._metrics.tts_total_latency_ms += ttfb_ms  # Track TTFB for latency

            logger.debug(
                "langfuse.tts_traced",
                ttfb_ms=ttfb_ms,
                characters=characters,
            )
        except Exception as e:
            logger.warning("langfuse.tts_trace_failed", error=str(e))

    def _trace_pipeline_metrics(self, metric: Any) -> None:
        """Trace end-to-end pipeline metrics."""
        if not self._root_span:
            return

        try:
            sequence_id = getattr(metric, "sequence_id", "")
            e2e_latency_ms = getattr(metric, "e2e_latency", 0) * 1000

            # Create span for pipeline under root
            span = self._root_span.start_span(
                name="pipeline-turn",
                input={"sequence_id": sequence_id},
                metadata={
                    "e2e_latency_ms": e2e_latency_ms,
                    "stt_latency_ms": getattr(metric, "stt_latency", 0) * 1000,
                    "llm_latency_ms": getattr(metric, "llm_latency", 0) * 1000,
                    "tts_latency_ms": getattr(metric, "tts_latency", 0) * 1000,
                },
            )
            span.end()

            # Accumulate metrics
            self._metrics.total_pipeline_latency_ms += e2e_latency_ms

            logger.debug(
                "langfuse.pipeline_traced",
                e2e_latency_ms=e2e_latency_ms,
            )
        except Exception as e:
            logger.warning("langfuse.pipeline_trace_failed", error=str(e))

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
        if not self._root_span:
            return

        try:
            span = self._root_span.start_span(
                name=f"tool-{tool_name}",
                input=parameters,
                metadata={"latency_ms": latency_ms},
            )
            span.update(output=result)
            span.end()

            self._metrics.total_tool_calls += 1

            logger.info(
                "langfuse.tool_traced",
                tool=tool_name,
                latency_ms=latency_ms,
            )
        except Exception as e:
            logger.warning("langfuse.tool_trace_failed", error=str(e))

    def flush(self) -> None:
        """Flush all pending events to Langfuse."""
        if self.langfuse:
            try:
                self.langfuse.flush()
            except Exception as e:
                logger.warning("langfuse.flush_failed", error=str(e))


def init_langfuse(
    public_key: Optional[str] = None,
    secret_key: Optional[str] = None,
    host: Optional[str] = None,
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
