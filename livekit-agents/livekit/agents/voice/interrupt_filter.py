"""
Intelligent Interruption Filter for LiveKit Agents.

This module provides context-aware filtering to distinguish between passive
acknowledgements (like "yeah", "ok", "hmm") and active interruptions based
on whether the agent is currently speaking or silent.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


@dataclass
class InterruptFilterConfig:
    """Configuration for the interrupt filter."""

    # Words to ignore when agent is speaking (passive acknowledgements)
    ignore_words: frozenset[str] = field(
        default_factory=lambda: frozenset(
            [
                "yeah",
                "yes",
                "yep",
                "yup",
                "ok",
                "okay",
                "hmm",
                "hm",
                "uh-huh",
                "uh huh",
                "right",
                "aha",
                "mhm",
                "mm-hmm",
                "mm hmm",
                "sure",
                "alright",
                "got it",
                "i see",
            ]
        )
    )

    # Words that always trigger an interrupt (commands)
    command_words: frozenset[str] = field(
        default_factory=lambda: frozenset(
            [
                "stop",
                "wait",
                "no",
                "hold",
                "hold on",
                "pause",
                "quiet",
                "shut up",
                "be quiet",
                "stop talking",
                "hang on",
                "one moment",
                "one second",
                "just a moment",
                "just a second",
            ]
        )
    )

    # Whether to enable the intelligent interruption filtering
    enabled: bool = True


class InterruptFilter:
    """
    Context-aware filter for distinguishing passive acknowledgements from active interruptions.

    This filter analyzes speech transcripts to determine whether user input should:
    - IGNORE: Continue speaking (when input is just filler words while agent speaks)
    - INTERRUPT: Stop immediately (when input contains command words)
    - RESPOND: Process as normal input (when agent is silent)
    """

    def __init__(self, config: InterruptFilterConfig | None = None) -> None:
        self._config = config or InterruptFilterConfig()
        # Pre-compile patterns for efficiency
        self._word_pattern = re.compile(r"[a-zA-Z]+(?:[-'][a-zA-Z]+)*")

    @property
    def config(self) -> InterruptFilterConfig:
        return self._config

    @property
    def enabled(self) -> bool:
        return self._config.enabled

    def _normalize_text(self, text: str) -> str:
        """Normalize text for comparison."""
        return text.lower().strip()

    def _extract_words(self, text: str) -> list[str]:
        """Extract individual words from text."""
        return self._word_pattern.findall(text.lower())

    def _is_only_ignore_words(self, text: str) -> bool:
        """Check if the text contains only ignore words."""
        normalized = self._normalize_text(text)

        # First check if entire phrase matches an ignore word/phrase
        if normalized in self._config.ignore_words:
            return True

        # Then check if all individual words are ignore words
        words = self._extract_words(text)
        if not words:
            return True  # Empty text is considered ignorable

        return all(word in self._config.ignore_words for word in words)

    def has_command_word(self, text: str) -> bool:
        """
        Check if transcript contains any command word.

        This checks for both single command words and command phrases.

        Args:
            text: The transcript text to analyze

        Returns:
            True if the text contains a command word/phrase
        """
        if not text:
            return False

        normalized = self._normalize_text(text)

        # Check for command phrases first (multi-word commands)
        for phrase in self._config.command_words:
            if " " in phrase and phrase in normalized:
                return True

        # Check for individual command words
        words = self._extract_words(text)
        for word in words:
            if word in self._config.command_words:
                return True

        return False

    def should_ignore(self, transcript: str, agent_is_speaking: bool) -> bool:
        """
        Determine if this input should be ignored (agent continues speaking).

        This implements the core logic matrix:
        - Agent speaking + filler words only → IGNORE (return True)
        - Agent speaking + command word → INTERRUPT (return False)
        - Agent silent → RESPOND (return False)

        Args:
            transcript: The transcribed user input
            agent_is_speaking: Whether the agent is currently speaking

        Returns:
            True if the input should be ignored (agent continues speaking)
            False if the input should be processed (interrupt or respond)
        """
        if not self._config.enabled:
            return False

        if not transcript or not transcript.strip():
            # Empty transcript - don't interrupt for nothing
            return agent_is_speaking

        # If agent is not speaking, never ignore - treat as normal input
        if not agent_is_speaking:
            return False

        # Agent IS speaking - check if we should ignore or interrupt

        # First check for command words - always interrupt for these
        if self.has_command_word(transcript):
            return False  # Don't ignore, process the interrupt

        # Check if it's only filler/acknowledgement words
        if self._is_only_ignore_words(transcript):
            return True  # Ignore, let agent continue

        # Mixed or unknown content - treat as potential interruption
        return False

    def classify_input(
        self, transcript: str, agent_is_speaking: bool
    ) -> str:
        """
        Classify the user input into an action category.

        Args:
            transcript: The transcribed user input
            agent_is_speaking: Whether the agent is currently speaking

        Returns:
            One of: "ignore", "interrupt", "respond"
        """
        if not self._config.enabled:
            return "interrupt" if agent_is_speaking else "respond"

        if not transcript or not transcript.strip():
            return "ignore" if agent_is_speaking else "respond"

        if not agent_is_speaking:
            return "respond"

        # Agent is speaking
        if self.has_command_word(transcript):
            return "interrupt"

        if self._is_only_ignore_words(transcript):
            return "ignore"

        # Unknown content while speaking - default to interrupt
        return "interrupt"
