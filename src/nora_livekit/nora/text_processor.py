"""Text processing utilities for Nora voice assistant.

Handles phone number SSML formatting, single-question enforcement,
and TTS-safe text transformation.

Satisfies REQ-F-NORA-TEXT-001 through REQ-F-NORA-TEXT-004.
"""

import re
from typing import Optional, Tuple

import structlog

logger = structlog.get_logger(__name__)


class NoraTextProcessor:
    """Text processing for Nora voice conversations.

    Satisfies: REQ-F-NORA-TEXT-001, REQ-F-NORA-TEXT-002,
               REQ-F-NORA-TEXT-003, REQ-F-NORA-TEXT-004
    """

    # Patterns for phone number detection
    PHONE_PATTERN = re.compile(r"\b(\d{10})\b")
    PHONE_PATTERN_FORMATTED = re.compile(r"\b(\d{3}[-.\s]?\d{3}[-.\s]?\d{4})\b")

    # Emergency keywords that trigger immediate interruption (Type B)
    CRITICAL_EMERGENCY_KEYWORDS = frozenset([
        "hit by car",
        "hit by a car",
        "not breathing",
        "can't breathe",
        "cant breathe",
        "cannot breathe",
        "difficulty breathing",
        "having a seizure",
        "seizure",
        "seizing",
        "unconscious",
        "collapsed",
        "passed out",
        "unresponsive",
        "dead",
        "appears dead",
        "not moving",
        "died",
        "dying",
    ])

    # Emergency phrases that trigger triage (Type A)
    EMERGENCY_PHRASES = frozenset([
        "emergency",
        "urgent",
        "right away",
        "right now",
        "immediately",
        "need help",
        "help now",
        "asap",
    ])

    def format_phone_for_tts(self, text: str, use_ssml: bool = True) -> str:
        """Format phone numbers for TTS pronunciation.

        Converts 10-digit phone numbers to digit-by-digit format
        with ellipses for natural pacing.

        Satisfies: REQ-F-NORA-TEXT-001

        Args:
            text: Text containing phone numbers
            use_ssml: Whether to use SSML tags (default: True)

        Returns:
            Text with formatted phone numbers
        """
        def format_number(match: re.Match) -> str:
            digits = re.sub(r"[-.\s]", "", match.group(0))
            if len(digits) != 10:
                return match.group(0)

            if use_ssml:
                # SSML format for proper pronunciation
                return f'<say-as interpret-as="telephone">{digits}</say-as>'
            else:
                # Fallback: digit-by-digit with ellipses
                # Format: "four one six... eight one eight... nine one seven one"
                area = " ".join(self._digit_to_word(d) for d in digits[:3])
                prefix = " ".join(self._digit_to_word(d) for d in digits[3:6])
                line = " ".join(self._digit_to_word(d) for d in digits[6:])
                return f"{area}... {prefix}... {line}"

        # Try formatted pattern first (xxx-xxx-xxxx)
        text = self.PHONE_PATTERN_FORMATTED.sub(format_number, text)
        # Then try raw 10-digit pattern
        text = self.PHONE_PATTERN.sub(format_number, text)

        return text

    def _digit_to_word(self, digit: str) -> str:
        """Convert a digit to its spoken word form."""
        words = {
            "0": "zero",
            "1": "one",
            "2": "two",
            "3": "three",
            "4": "four",
            "5": "five",
            "6": "six",
            "7": "seven",
            "8": "eight",
            "9": "nine",
        }
        return words.get(digit, digit)

    def enforce_single_question(self, text: str) -> Tuple[str, bool]:
        """Enforce single question per response.

        If text contains multiple questions, truncate after the first.

        Satisfies: REQ-F-NORA-TEXT-002

        Args:
            text: LLM response text

        Returns:
            Tuple of (processed_text, was_truncated)
        """
        if not text:
            return text, False

        # Count question marks
        question_count = text.count("?")

        if question_count <= 1:
            return text, False

        # Find first question mark and truncate
        first_q_index = text.find("?")
        truncated = text[: first_q_index + 1].strip()

        logger.warning(
            "nora.text.multiple_questions_blocked",
            original_questions=question_count,
            truncated_text=truncated[:100],
        )

        return truncated, True

    def detect_emergency(self, text: str) -> Tuple[bool, Optional[str], str]:
        """Detect emergency keywords in user speech.

        Satisfies: REQ-F-NORA-TEXT-003

        Args:
            text: User's transcribed speech

        Returns:
            Tuple of (is_emergency, emergency_type, matched_keyword)
            emergency_type: "critical" (Type B) or "triage" (Type A) or None
        """
        text_lower = text.lower()

        # Check for Type B (critical/specific) emergencies first
        for keyword in self.CRITICAL_EMERGENCY_KEYWORDS:
            if keyword in text_lower:
                logger.info(
                    "nora.text.critical_emergency_detected",
                    keyword=keyword,
                    text=text[:100],
                )
                return True, "critical", keyword

        # Check for Type A (general emergency phrases)
        for phrase in self.EMERGENCY_PHRASES:
            if phrase in text_lower:
                logger.info(
                    "nora.text.emergency_phrase_detected",
                    phrase=phrase,
                    text=text[:100],
                )
                return True, "triage", phrase

        return False, None, ""

    def remove_markdown(self, text: str) -> str:
        """Remove markdown formatting from text.

        Satisfies: REQ-F-NORA-TEXT-004

        Args:
            text: Text potentially containing markdown

        Returns:
            Plain text without markdown
        """
        # Remove bold (**text** or __text__)
        text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
        text = re.sub(r"__(.+?)__", r"\1", text)

        # Remove italic (*text* or _text_)
        text = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"\1", text)
        text = re.sub(r"(?<!_)_(?!_)(.+?)(?<!_)_(?!_)", r"\1", text)

        # Remove code blocks
        text = re.sub(r"```[\s\S]*?```", "", text)
        text = re.sub(r"`([^`]+)`", r"\1", text)

        # Remove headers
        text = re.sub(r"^#+\s+", "", text, flags=re.MULTILINE)

        # Remove bullet points
        text = re.sub(r"^\s*[-*+]\s+", "", text, flags=re.MULTILINE)
        text = re.sub(r"^\s*\d+\.\s+", "", text, flags=re.MULTILINE)

        # Normalize whitespace
        text = re.sub(r"\n\n+", " ", text)
        text = re.sub(r"\s+", " ", text).strip()

        return text

    def validate_triage_response(self, text: str) -> Tuple[bool, Optional[str]]:
        """Validate that a response is a valid triage answer.

        Checks if the response is a clear yes/no/urgent/wait answer.

        Args:
            text: User's response to triage question

        Returns:
            Tuple of (is_valid, response_type)
            response_type: "urgent", "wait", or None if invalid
        """
        text_lower = text.lower().strip()

        # Valid wait responses - CHECK THESE FIRST (more specific)
        # "not urgent" must be checked before "urgent"
        wait_responses = {
            "no", "nope", "nah", "can wait", "not urgent", "later",
            "tomorrow", "routine", "it's fine", "its fine",
        }

        # Valid urgent responses
        urgent_responses = {
            "yes", "yeah", "yep", "immediate", "urgent", "right away",
            "asap", "now", "emergency", "help", "uh huh", "mhmm", "sure",
        }

        # Check for wait FIRST (to handle "not urgent" before "urgent")
        for response in wait_responses:
            if response in text_lower:
                return True, "wait"

        # Check for urgent
        for response in urgent_responses:
            if response in text_lower:
                return True, "urgent"

        # Check if response looks like a name (invalid for triage)
        # Names typically are 1-2 words with capital letters
        words = text.split()
        if len(words) <= 3 and all(w[0].isupper() for w in words if w):
            # Likely a name, not a valid triage response
            return False, None

        return False, None

    def sanitize_function_calls(self, text: str) -> str:
        """Remove function call syntax from LLM output.

        Handles cases where LLM outputs function calls as text instead
        of using proper tool_call format. This commonly happens with
        smaller models like llama-3.1-8b.

        Patterns removed:
        - <function=name>{"args": "..."} format
        - function_name(arg1="val1", ...) format
        - SAY THIS: / SAY EXACTLY THIS: prefixes
        - Code blocks containing function calls

        Args:
            text: LLM response that may contain function syntax

        Returns:
            Text with function call syntax removed
        """
        if not text:
            return text

        original = text

        # Pattern 1: <function=name>, <function.name>, <function$name> XML-style format (Groq/Llama output)
        # Matches: <function=route_to_urgent_transfer>{"caller_phone":"..."}</function>
        # Also matches: <function.route_to_message_flow{"caller_phone":"..."}</function> (dot format)
        # Also matches: <function$route_to_critical_emergency{"pet_name":"..."}</function> (dollar format)
        # Note: Llama/Groq models use =, ., and $ separators inconsistently
        text = re.sub(r'<function[=.$][^>]*>.*?</function>', '', text, flags=re.DOTALL)
        text = re.sub(r'<function[=.$][^>]*>\s*\{[^}]*\}', '', text)
        text = re.sub(r'<function[=.$][^{]*\{[^}]*\}</function>', '', text, flags=re.DOTALL)
        text = re.sub(r'<function[=.$][^{]*\{[^}]*\}', '', text)
        text = re.sub(r'<function[=.$][^>]*>[^\s]*', '', text)
        # Also handle any <function...> without closing tag followed by JSON
        text = re.sub(r'<function[^>]*\{[^}]*\}', '', text)

        # Pattern 2: function_name(args) format
        # Matches: transferFromAiTriageWithMetadata(callback_number="...", ...)
        # Also matches: route_to_urgent_transfer(pet_name="Max", ...)
        # Be careful not to match normal parenthetical text
        function_names = [
            'transferFromAiTriageWithMetadata',
            'collectNameNumberConcernPetName',
            'route_to_urgent_transfer',
            'route_to_message_flow',
            'route_to_critical_emergency',
            'queryCorpus',
            'hangUp',
        ]
        for func_name in function_names:
            # Match function call with any content in parentheses (including newlines)
            pattern = rf'{func_name}\s*\([^)]*\)'
            text = re.sub(pattern, '', text, flags=re.DOTALL)
            # Also match just the function name followed by open paren if args span lines
            pattern_multiline = rf'{func_name}\s*\([\s\S]*?\)'
            text = re.sub(pattern_multiline, '', text, flags=re.DOTALL)

        # Pattern 3: Remove "SAY THIS:" or "SAY EXACTLY THIS:" prefixes
        text = re.sub(r'SAY\s+(EXACTLY\s+)?THIS:\s*', '', text, flags=re.IGNORECASE)

        # Pattern 4: Remove code blocks (triple backticks) - may contain function calls
        text = re.sub(r'```[\s\S]*?```', '', text)

        # Pattern 5: Remove inline code (single backticks)
        text = re.sub(r'`[^`]+`', '', text)

        # Pattern 6: Clean up JSON-like fragments that may remain
        text = re.sub(r'\{[^}]*"callback_number"[^}]*\}', '', text)
        text = re.sub(r'\{[^}]*"first_name"[^}]*\}', '', text)

        # Clean up whitespace artifacts
        text = re.sub(r'\n\s*\n', '\n', text)  # Multiple newlines
        text = re.sub(r'\s+', ' ', text)  # Multiple spaces
        text = text.strip()

        # Log if we removed something
        if text != original:
            logger.info(
                "nora.text.function_calls_sanitized",
                original_len=len(original),
                sanitized_len=len(text),
                removed_chars=len(original) - len(text),
            )

        # CRITICAL: If sanitizing removed ALL content, the LLM only output function
        # call syntax with no natural language. Provide a fallback so TTS has something.
        if not text and original:
            # Determine appropriate fallback based on what function was called
            fallback = ""
            original_lower = original.lower()

            if "route_to_urgent_transfer" in original_lower or "transferfromaitriage" in original_lower:
                fallback = "Let me connect you to our triage team right away."
            elif "route_to_message_flow" in original_lower or "collectnamenumberconcern" in original_lower:
                fallback = "I'll make sure to pass along your message."
            elif "route_to_critical_emergency" in original_lower:
                fallback = "I'm connecting you immediately for emergency assistance."
            elif "hangup" in original_lower:
                fallback = "Thank you for calling. Goodbye."
            elif "querycorpus" in original_lower:
                # Don't say anything for corpus queries - let next response handle it
                fallback = ""

            logger.warning(
                "nora.text.sanitizer_fallback_used",
                reason="LLM output contained only function call syntax",
                original_len=len(original),
                fallback_message=fallback[:50] if fallback else "none",
            )
            return fallback

        return text

    def process_for_tts(self, text: str, use_ssml: bool = True) -> str:
        """Full processing pipeline for TTS output.

        Applies all transformations in order:
        1. Sanitize function calls (remove LLM function syntax artifacts)
        2. Remove markdown
        3. Enforce single question
        4. Format phone numbers

        Args:
            text: Raw LLM response
            use_ssml: Whether to use SSML tags

        Returns:
            TTS-ready text
        """
        text = self.sanitize_function_calls(text)
        text = self.remove_markdown(text)
        text, _ = self.enforce_single_question(text)
        text = self.format_phone_for_tts(text, use_ssml)
        return text
