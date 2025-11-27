"""LLM integration for conversation generation.

Supports multiple LLM providers (OpenAI, Anthropic) with retry logic,
error handling, and TTS-compatible formatting.

Satisfies REQ-F-LLM-001 through REQ-F-LLM-007.
"""

import asyncio
import re
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any

import structlog
from openai import OpenAI, APIError as OpenAIAPIError

# Anthropic is optional - only needed if using Anthropic LLM provider
try:
    from anthropic import Anthropic, APIError as AnthropicAPIError
    ANTHROPIC_AVAILABLE = True
except ImportError:
    Anthropic = None  # type: ignore
    AnthropicAPIError = Exception  # type: ignore
    ANTHROPIC_AVAILABLE = False

from nora_livekit.conversation.context import ConversationContext, ConversationPhase

logger = structlog.get_logger(__name__)


class LLMProvider(Enum):
    """Supported LLM providers."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"


@dataclass
class LLMResponse:
    """Response from LLM API."""

    text: str
    tokens_used: int
    latency_ms: float
    model: str
    finish_reason: str


class LLMIntegration:
    """Handles LLM API integration for conversation generation.

    Satisfies: REQ-F-LLM-001, REQ-F-LLM-002, REQ-F-LLM-003,
               REQ-F-LLM-004, REQ-F-LLM-005, REQ-F-LLM-006, REQ-F-LLM-007
    """

    # System prompts by conversation phase
    SYSTEM_PROMPTS = {
        ConversationPhase.GREETING: """You are Nora, a friendly AI voice assistant.
The conversation is just starting. Greet the user warmly and ask how you can help.
Keep responses SHORT (1-2 sentences) since this is a voice conversation.
Avoid markdown, bullet points, or complex formatting.""",
        ConversationPhase.ACTIVE: """You are Nora, a helpful AI voice assistant.
Provide clear, concise answers to user questions.
Keep responses SHORT (2-3 sentences max) for voice conversations.
Avoid markdown, lists, or complex formatting.
Ask clarifying questions if needed.""",
        ConversationPhase.CLOSING: """You are Nora, a friendly AI voice assistant.
The conversation is ending. Provide a brief closing statement.
Keep it SHORT (1 sentence) and friendly.
Avoid markdown or complex formatting.""",
    }

    def __init__(
        self,
        provider: LLMProvider,
        api_key: str,
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 150,
    ) -> None:
        """Initialize LLM integration with provider configuration.

        Satisfies: REQ-F-LLM-001

        Args:
            provider: LLM provider (OPENAI or ANTHROPIC)
            api_key: API key for the provider
            model: Model name (e.g., gpt-4, claude-3-sonnet-20240229)
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens in response
        """
        self.provider = provider
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

        # Initialize API clients
        if provider == LLMProvider.OPENAI:
            self._openai_client = OpenAI(api_key=api_key)
        elif provider == LLMProvider.ANTHROPIC:
            self._anthropic_client = Anthropic(api_key=api_key)

    async def generate_response(
        self,
        context: ConversationContext,
        system_prompt: str | None = None,
    ) -> LLMResponse:
        """Generate response using LLM based on conversation context.

        Satisfies: REQ-F-LLM-002, REQ-F-LLM-003, REQ-F-LLM-004, REQ-F-LLM-005

        Args:
            context: Current conversation context
            system_prompt: Optional override for system prompt

        Returns:
            LLMResponse with text and metrics

        Raises:
            LLMError: On permanent API failure after retries
        """
        messages = context.format_for_llm()
        system_prompt = system_prompt or self._construct_system_prompt(context.phase)

        if self.provider == LLMProvider.OPENAI:
            return await self._call_openai(messages, system_prompt)
        else:  # ANTHROPIC
            return await self._call_anthropic(messages, system_prompt)

    def _construct_system_prompt(self, phase: ConversationPhase) -> str:
        """Construct phase-specific system prompt.

        Satisfies: REQ-F-LLM-007

        Args:
            phase: Current conversation phase

        Returns:
            System prompt text
        """
        return self.SYSTEM_PROMPTS[phase]

    def _format_for_tts(self, text: str) -> str:
        """Format LLM response for TTS compatibility.

        Removes markdown, code blocks, bullet points.

        Satisfies: REQ-F-LLM-006

        Args:
            text: Raw LLM response text

        Returns:
            Formatted text safe for TTS
        """
        # Remove markdown bold (**text**)
        text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)

        # Remove markdown italic (_text_ or *text*)
        text = re.sub(r"[_*]([^_*]+)[_*]", r"\1", text)

        # Remove code blocks (``` ... ```)
        text = re.sub(r"```[\s\S]*?```", "", text)

        # Remove inline code (`code`)
        text = re.sub(r"`([^`]+)`", r"\1", text)

        # Remove markdown headers (# ## ###)
        text = re.sub(r"^#+\s+", "", text, flags=re.MULTILINE)

        # Remove bullet points and list markers
        text = re.sub(r"^\s*[-*+]\s+", "", text, flags=re.MULTILINE)
        text = re.sub(r"^\s*\d+\.\s+", "", text, flags=re.MULTILINE)

        # Remove line breaks that are artifacts
        text = re.sub(r"\n\n+", " ", text)
        text = text.replace("\n", " ")

        # Clean up extra spaces
        text = re.sub(r"\s+", " ", text).strip()

        return text

    async def _call_openai(
        self,
        messages: list[dict[str, str]],
        system_prompt: str,
    ) -> LLMResponse:
        """Call OpenAI API with retry logic.

        Satisfies: REQ-F-LLM-001, REQ-F-LLM-004

        Args:
            messages: Formatted messages for LLM
            system_prompt: System prompt for the request

        Returns:
            LLMResponse with text and metrics

        Raises:
            LLMError: On permanent failure
        """
        max_retries = 3
        retry_delays = [1, 2, 4]  # Exponential backoff: 1s, 2s, 4s
        retryable_errors = {429, 500, 503}

        for attempt in range(max_retries):
            try:
                start_time = time.time()

                # Call OpenAI API
                response = self._openai_client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        *messages,
                    ],
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                )

                latency_ms = (time.time() - start_time) * 1000
                text = response.choices[0].message.content or ""

                # Format for TTS
                text = self._format_for_tts(text)

                # Log metrics
                tokens = response.usage.total_tokens if hasattr(response, "usage") else 0
                await logger.ainfo(
                    "llm_response_generated",
                    model=self.model,
                    tokens_used=tokens,
                    latency_ms=latency_ms,
                    finish_reason=response.choices[0].finish_reason,
                )

                return LLMResponse(
                    text=text,
                    tokens_used=tokens,
                    latency_ms=latency_ms,
                    model=self.model,
                    finish_reason=response.choices[0].finish_reason or "unknown",
                )

            except OpenAIAPIError as e:
                status_code = getattr(e, "status_code", None)
                if status_code in retryable_errors and attempt < max_retries - 1:
                    await logger.awarning(
                        "llm_api_error_retryable",
                        attempt=attempt + 1,
                        status_code=status_code,
                        delay_seconds=retry_delays[attempt],
                    )
                    await asyncio.sleep(retry_delays[attempt])
                    continue

                # Non-retryable or final retry failed
                await logger.aerror(
                    "llm_api_error_permanent",
                    status_code=status_code,
                    error=str(e),
                )
                raise

        raise RuntimeError("LLM API failed after all retries")

    async def _call_anthropic(
        self,
        messages: list[dict[str, str]],
        system_prompt: str,
    ) -> LLMResponse:
        """Call Anthropic API with retry logic.

        Satisfies: REQ-F-LLM-001, REQ-F-LLM-004

        Args:
            messages: Formatted messages for LLM
            system_prompt: System prompt for the request

        Returns:
            LLMResponse with text and metrics

        Raises:
            LLMError: On permanent failure
        """
        max_retries = 3
        retry_delays = [1, 2, 4]  # Exponential backoff
        retryable_errors = {429, 500, 503}

        for attempt in range(max_retries):
            try:
                start_time = time.time()

                # Call Anthropic API
                response = self._anthropic_client.messages.create(
                    model=self.model,
                    max_tokens=self.max_tokens,
                    system=system_prompt,
                    messages=messages,
                    temperature=self.temperature,
                )

                latency_ms = (time.time() - start_time) * 1000
                text = response.content[0].text if response.content else ""

                # Format for TTS
                text = self._format_for_tts(text)

                # Log metrics
                tokens = response.usage.input_tokens + response.usage.output_tokens
                await logger.ainfo(
                    "llm_response_generated",
                    model=self.model,
                    tokens_used=tokens,
                    latency_ms=latency_ms,
                    finish_reason=response.stop_reason,
                )

                return LLMResponse(
                    text=text,
                    tokens_used=tokens,
                    latency_ms=latency_ms,
                    model=self.model,
                    finish_reason=response.stop_reason or "unknown",
                )

            except AnthropicAPIError as e:
                status_code = getattr(e, "status_code", None)
                if status_code in retryable_errors and attempt < max_retries - 1:
                    await logger.awarning(
                        "llm_api_error_retryable",
                        attempt=attempt + 1,
                        status_code=status_code,
                        delay_seconds=retry_delays[attempt],
                    )
                    await asyncio.sleep(retry_delays[attempt])
                    continue

                # Non-retryable or final retry failed
                await logger.aerror(
                    "llm_api_error_permanent",
                    status_code=status_code,
                    error=str(e),
                )
                raise

        raise RuntimeError("LLM API failed after all retries")
