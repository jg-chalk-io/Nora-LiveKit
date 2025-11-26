"""Tests for Nora text processor."""

import pytest

from nora_livekit.nora.text_processor import NoraTextProcessor


class TestPhoneFormatting:
    """Tests for phone number TTS formatting."""

    def setup_method(self):
        """Set up test fixtures."""
        self.processor = NoraTextProcessor()

    def test_format_10_digit_phone_with_ssml(self):
        """Test 10-digit phone formatted with SSML."""
        text = "Your number is 4168189171."
        result = self.processor.format_phone_for_tts(text, use_ssml=True)
        assert '<say-as interpret-as="telephone">4168189171</say-as>' in result

    def test_format_10_digit_phone_without_ssml(self):
        """Test 10-digit phone formatted without SSML (digit-by-digit)."""
        text = "Your number is 4168189171."
        result = self.processor.format_phone_for_tts(text, use_ssml=False)
        # Should be digit-by-digit with ellipses
        assert "four one six" in result
        assert "eight one eight" in result
        assert "nine one seven one" in result
        assert "..." in result

    def test_format_formatted_phone_number(self):
        """Test phone number with dashes."""
        text = "Call us at 416-818-9171."
        result = self.processor.format_phone_for_tts(text, use_ssml=True)
        assert '<say-as interpret-as="telephone">' in result

    def test_non_phone_numbers_unchanged(self):
        """Test that non-phone numbers are not changed."""
        text = "Your code is 12345."
        result = self.processor.format_phone_for_tts(text, use_ssml=True)
        assert result == text


class TestSingleQuestionEnforcement:
    """Tests for single question enforcement."""

    def setup_method(self):
        """Set up test fixtures."""
        self.processor = NoraTextProcessor()

    def test_single_question_passes(self):
        """Test that single question passes through unchanged."""
        text = "What's your first name?"
        result, truncated = self.processor.enforce_single_question(text)
        assert result == text
        assert truncated is False

    def test_multiple_questions_truncated(self):
        """Test that multiple questions are truncated to first."""
        text = "What's your name? And what's your pet's name?"
        result, truncated = self.processor.enforce_single_question(text)
        assert result == "What's your name?"
        assert truncated is True

    def test_no_questions_passes(self):
        """Test that text without questions passes unchanged."""
        text = "Thank you for calling."
        result, truncated = self.processor.enforce_single_question(text)
        assert result == text
        assert truncated is False

    def test_empty_text(self):
        """Test empty text handling."""
        result, truncated = self.processor.enforce_single_question("")
        assert result == ""
        assert truncated is False


class TestEmergencyDetection:
    """Tests for emergency keyword detection."""

    def setup_method(self):
        """Set up test fixtures."""
        self.processor = NoraTextProcessor()

    def test_detect_type_b_critical_emergency(self):
        """Test detection of Type B (specific) emergencies."""
        critical_phrases = [
            "my dog was hit by a car",
            "my cat is not breathing",
            "he's having a seizure",
            "she collapsed and is unconscious",
            "I think my pet is dead",
        ]

        for phrase in critical_phrases:
            is_emergency, emergency_type, keyword = self.processor.detect_emergency(phrase)
            assert is_emergency is True, f"Failed to detect: {phrase}"
            assert emergency_type == "critical", f"Wrong type for: {phrase}"

    def test_detect_type_a_emergency_phrases(self):
        """Test detection of Type A (general) emergency phrases."""
        type_a_phrases = [
            "this is an emergency",
            "it's urgent",
            "I need help right away",
            "we need help right now",
        ]

        for phrase in type_a_phrases:
            is_emergency, emergency_type, keyword = self.processor.detect_emergency(phrase)
            assert is_emergency is True, f"Failed to detect: {phrase}"
            assert emergency_type == "triage", f"Wrong type for: {phrase}"

    def test_non_emergency_not_detected(self):
        """Test that non-emergency text is not flagged."""
        normal_phrases = [
            "I need a prescription refill",
            "when are you open",
            "my dog needs a checkup",
            "I have a question about my bill",
        ]

        for phrase in normal_phrases:
            is_emergency, emergency_type, _ = self.processor.detect_emergency(phrase)
            assert is_emergency is False, f"False positive for: {phrase}"
            assert emergency_type is None


class TestMarkdownRemoval:
    """Tests for markdown removal."""

    def setup_method(self):
        """Set up test fixtures."""
        self.processor = NoraTextProcessor()

    def test_remove_bold(self):
        """Test bold markdown removal."""
        text = "This is **bold** text."
        result = self.processor.remove_markdown(text)
        assert result == "This is bold text."

    def test_remove_italic(self):
        """Test italic markdown removal."""
        text = "This is *italic* text."
        result = self.processor.remove_markdown(text)
        assert result == "This is italic text."

    def test_remove_code_block(self):
        """Test code block removal."""
        text = "Here is code:\n```python\nprint('hello')\n```\nDone."
        result = self.processor.remove_markdown(text)
        assert "```" not in result
        assert "print" not in result

    def test_remove_inline_code(self):
        """Test inline code removal."""
        text = "Use the `print` function."
        result = self.processor.remove_markdown(text)
        assert result == "Use the print function."

    def test_remove_headers(self):
        """Test header removal."""
        text = "# Header\nSome content"
        result = self.processor.remove_markdown(text)
        assert "#" not in result

    def test_remove_bullet_points(self):
        """Test bullet point removal."""
        text = "- Item 1\n- Item 2"
        result = self.processor.remove_markdown(text)
        assert "- " not in result


class TestTriageValidation:
    """Tests for triage response validation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.processor = NoraTextProcessor()

    def test_valid_urgent_responses(self):
        """Test valid urgent triage responses."""
        urgent_responses = ["yes", "yeah", "urgent", "right away", "asap"]
        for response in urgent_responses:
            is_valid, response_type = self.processor.validate_triage_response(response)
            assert is_valid is True, f"Failed for: {response}"
            assert response_type == "urgent", f"Wrong type for: {response}"

    def test_valid_wait_responses(self):
        """Test valid wait triage responses."""
        wait_responses = ["no", "can wait", "not urgent", "routine"]
        for response in wait_responses:
            is_valid, response_type = self.processor.validate_triage_response(response)
            assert is_valid is True, f"Failed for: {response}"
            assert response_type == "wait", f"Wrong type for: {response}"

    def test_invalid_name_responses(self):
        """Test that names are rejected as triage responses."""
        # Names that look like they could be misinterpreted
        names = ["Thomas Crown", "Bobby", "Jennifer"]
        for name in names:
            is_valid, _ = self.processor.validate_triage_response(name)
            # Names should be flagged as invalid for triage
            assert is_valid is False, f"Should reject name: {name}"


class TestFullProcessingPipeline:
    """Tests for the full TTS processing pipeline."""

    def setup_method(self):
        """Set up test fixtures."""
        self.processor = NoraTextProcessor()

    def test_full_pipeline_with_ssml(self):
        """Test full processing pipeline with SSML."""
        text = "**Call** us at 4168189171. What's your name? Where do you live?"
        result = self.processor.process_for_tts(text, use_ssml=True)

        # Markdown should be removed
        assert "**" not in result
        # Phone should be SSML formatted
        assert '<say-as interpret-as="telephone">' in result
        # Should only have one question
        assert result.count("?") == 1

    def test_full_pipeline_without_ssml(self):
        """Test full processing pipeline without SSML."""
        text = "Call 4168189171 please."
        result = self.processor.process_for_tts(text, use_ssml=False)

        # Phone should be digit-by-digit
        assert "four one six" in result
