"""Observability module for Nora voice agent.

Provides Langfuse integration for tracing:
- LLM calls (latency, tokens, cost)
- STT transcriptions
- TTS synthesis
- Full conversation turns
- Tool executions
"""

from nora_livekit.observability.langfuse_tracer import (
    NoraLangfuseTracer,
    init_langfuse,
    get_tracer,
)

__all__ = [
    "NoraLangfuseTracer",
    "init_langfuse",
    "get_tracer",
]
