"""Tests for the InterruptFilter class."""

from __future__ import annotations

import pytest

from livekit.agents.voice.interrupt_filter import InterruptFilter, InterruptFilterConfig


class TestInterruptFilter:
    """Test suite for InterruptFilter."""

    def test_default_config(self) -> None:
        """Test that default config has expected ignore and command words."""
        config = InterruptFilterConfig()
        filter = InterruptFilter(config)

        assert filter.enabled is True
        assert "yeah" in filter.config.ignore_words
        assert "ok" in filter.config.ignore_words
        assert "stop" in filter.config.command_words
        assert "wait" in filter.config.command_words

    def test_should_ignore_filler_words_while_speaking(self) -> None:
        """Test that filler words are ignored when agent is speaking."""
        filter = InterruptFilter()

        # Single filler words
        assert filter.should_ignore("yeah", agent_is_speaking=True) is True
        assert filter.should_ignore("ok", agent_is_speaking=True) is True
        assert filter.should_ignore("hmm", agent_is_speaking=True) is True
        assert filter.should_ignore("uh-huh", agent_is_speaking=True) is True
        assert filter.should_ignore("right", agent_is_speaking=True) is True
        assert filter.should_ignore("mhm", agent_is_speaking=True) is True

        # Multiple filler words
        assert filter.should_ignore("yeah ok", agent_is_speaking=True) is True
        assert filter.should_ignore("ok ok ok", agent_is_speaking=True) is True

    def test_should_not_ignore_filler_words_while_silent(self) -> None:
        """Test that filler words are NOT ignored when agent is silent."""
        filter = InterruptFilter()

        # Single filler words when agent is NOT speaking - should NOT ignore
        assert filter.should_ignore("yeah", agent_is_speaking=False) is False
        assert filter.should_ignore("ok", agent_is_speaking=False) is False
        assert filter.should_ignore("hmm", agent_is_speaking=False) is False

    def test_command_words_interrupt(self) -> None:
        """Test that command words trigger interruption even when speaking."""
        filter = InterruptFilter()

        # Command words should never be ignored
        assert filter.should_ignore("stop", agent_is_speaking=True) is False
        assert filter.should_ignore("wait", agent_is_speaking=True) is False
        assert filter.should_ignore("no", agent_is_speaking=True) is False
        assert filter.should_ignore("hold on", agent_is_speaking=True) is False
        assert filter.should_ignore("be quiet", agent_is_speaking=True) is False

    def test_mixed_input_with_command(self) -> None:
        """Test that mixed input containing command words is not ignored."""
        filter = InterruptFilter()

        # Mixed input with command word should NOT be ignored
        assert filter.should_ignore("yeah okay but wait", agent_is_speaking=True) is False
        assert filter.should_ignore("ok stop", agent_is_speaking=True) is False
        assert filter.should_ignore("hmm no", agent_is_speaking=True) is False

    def test_real_sentences_interrupt(self) -> None:
        """Test that real sentences (not just filler) cause interruption."""
        filter = InterruptFilter()

        # Full sentences should not be ignored
        assert filter.should_ignore("I have a question", agent_is_speaking=True) is False
        assert filter.should_ignore("What about the weather", agent_is_speaking=True) is False
        assert filter.should_ignore("Tell me more", agent_is_speaking=True) is False

    def test_case_insensitivity(self) -> None:
        """Test that filtering is case-insensitive."""
        filter = InterruptFilter()

        assert filter.should_ignore("YEAH", agent_is_speaking=True) is True
        assert filter.should_ignore("Yeah", agent_is_speaking=True) is True
        assert filter.should_ignore("OK", agent_is_speaking=True) is True
        assert filter.should_ignore("STOP", agent_is_speaking=True) is False

    def test_has_command_word(self) -> None:
        """Test the has_command_word method."""
        filter = InterruptFilter()

        assert filter.has_command_word("stop") is True
        assert filter.has_command_word("wait") is True
        assert filter.has_command_word("yeah but wait") is True
        assert filter.has_command_word("hold on a second") is True
        assert filter.has_command_word("yeah") is False
        assert filter.has_command_word("ok") is False

    def test_classify_input(self) -> None:
        """Test the classify_input method."""
        filter = InterruptFilter()

        # Agent speaking
        assert filter.classify_input("yeah", agent_is_speaking=True) == "ignore"
        assert filter.classify_input("stop", agent_is_speaking=True) == "interrupt"
        assert filter.classify_input("what time is it", agent_is_speaking=True) == "interrupt"

        # Agent silent
        assert filter.classify_input("yeah", agent_is_speaking=False) == "respond"
        assert filter.classify_input("stop", agent_is_speaking=False) == "respond"

    def test_empty_transcript(self) -> None:
        """Test handling of empty transcripts."""
        filter = InterruptFilter()

        # Empty or whitespace should be ignored when speaking
        assert filter.should_ignore("", agent_is_speaking=True) is True
        assert filter.should_ignore("   ", agent_is_speaking=True) is True
        assert filter.should_ignore("", agent_is_speaking=False) is False

    def test_disabled_filter(self) -> None:
        """Test that disabled filter never ignores."""
        config = InterruptFilterConfig(enabled=False)
        filter = InterruptFilter(config)

        assert filter.enabled is False
        assert filter.should_ignore("yeah", agent_is_speaking=True) is False
        assert filter.should_ignore("ok", agent_is_speaking=True) is False

    def test_custom_ignore_words(self) -> None:
        """Test custom ignore words configuration."""
        config = InterruptFilterConfig(
            ignore_words=frozenset(["custom", "words"]),
            command_words=frozenset(["halt"]),
        )
        filter = InterruptFilter(config)

        # Custom words should be ignored
        assert filter.should_ignore("custom", agent_is_speaking=True) is True
        assert filter.should_ignore("words", agent_is_speaking=True) is True
        # Default words should NOT be ignored anymore
        assert filter.should_ignore("yeah", agent_is_speaking=True) is False

        # Custom command word
        assert filter.has_command_word("halt") is True
        assert filter.has_command_word("stop") is False

    def test_phrase_matching(self) -> None:
        """Test that multi-word phrases are matched correctly."""
        filter = InterruptFilter()

        # Phrases that should be matched
        assert filter.should_ignore("got it", agent_is_speaking=True) is True
        assert filter.should_ignore("i see", agent_is_speaking=True) is True

        # Command phrases
        assert filter.has_command_word("hold on") is True
        assert filter.has_command_word("one moment please") is True


class TestInterruptFilterIntegration:
    """Integration tests for interrupt filter behavior."""

    def test_scenario_agent_explaining(self) -> None:
        """Scenario: Agent is explaining something, user says 'yeah', 'ok', 'uh-huh'."""
        filter = InterruptFilter()

        # All should be ignored - agent continues speaking
        responses = ["yeah", "ok", "uh-huh", "right", "mhm"]
        for response in responses:
            assert filter.should_ignore(response, agent_is_speaking=True) is True, (
                f"Expected '{response}' to be ignored while agent speaking"
            )

    def test_scenario_agent_asks_question(self) -> None:
        """Scenario: Agent asks a question, user responds with 'yeah'."""
        filter = InterruptFilter()

        # Agent is NOT speaking (waiting for answer)
        assert filter.should_ignore("yeah", agent_is_speaking=False) is False
        assert filter.classify_input("yeah", agent_is_speaking=False) == "respond"

    def test_scenario_user_says_stop(self) -> None:
        """Scenario: Agent is speaking, user explicitly says 'stop'."""
        filter = InterruptFilter()

        # Should NOT be ignored - agent should stop
        assert filter.should_ignore("stop", agent_is_speaking=True) is False
        assert filter.classify_input("stop", agent_is_speaking=True) == "interrupt"

    def test_scenario_mixed_input(self) -> None:
        """Scenario: User says 'Yeah okay but wait'."""
        filter = InterruptFilter()

        # Contains 'wait' command word - should NOT be ignored
        assert filter.should_ignore("yeah okay but wait", agent_is_speaking=True) is False
        assert filter.classify_input("yeah okay but wait", agent_is_speaking=True) == "interrupt"
