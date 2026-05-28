"""Output length predictors for LTR-based request scheduling.

Implements the core insight from "Efficient LLM Scheduling by Learning to Rank"
(NeurIPS 2024): accurate relative ranking of output lengths is sufficient for
SJF-like scheduling — exact length predictions are not required.
"""
import re
from abc import ABC, abstractmethod

_SHORT_KEYWORDS = re.compile(
    r"(?:简短|简答|一句话|简述|列出|list|brief|short|one\s+sentence|summarize|summary|tl;dr)",
    re.IGNORECASE,
)
_LONG_KEYWORDS = re.compile(
    r"(?:详细|全面|深入|解释|论述|阐述|essay|detailed|comprehensive|explain|thorough|in\s+depth|elaborate)",
    re.IGNORECASE,
)

_DEFAULT_MAX_TOKENS = 512
_DEFAULT_MAX_CAP = 2048


class LengthPredictor(ABC):
    """Abstract base for output-length predictors."""

    @abstractmethod
    def predict(self, body: dict) -> float:
        """Return an estimated output token count for *body*.

        Lower values indicate shorter expected output (higher scheduling priority).
        The absolute value does not need to be accurate — only the relative
        ordering matters for SJF approximation.
        """


class HeuristicPredictor(LengthPredictor):
    """Rule-based predictor using readily-available request metadata.

    Features used:
    - ``max_tokens`` from the request body (hard upper bound)
    - Prompt character / word count
    - Conversation turn count
    - Keyword detection (short vs long intent)
    - Last message length
    """

    def predict(self, body: dict) -> float:
        messages = body.get("messages", [])
        max_tokens = body.get("max_tokens", _DEFAULT_MAX_TOKENS)
        if max_tokens is None:
            max_tokens = _DEFAULT_MAX_TOKENS
        max_tokens = min(max_tokens, _DEFAULT_MAX_CAP)

        # --- prompt text ---
        all_text = " ".join(m.get("content", "") for m in messages)
        last_msg = messages[-1].get("content", "") if messages else ""
        char_count = len(all_text)
        word_count = len(all_text.split())
        turn_count = len(messages)

        # --- base estimate ---
        base: float = max_tokens

        # --- keyword adjustment ---
        if _SHORT_KEYWORDS.search(last_msg):
            base = min(max_tokens, max_tokens * 0.3)
        elif _LONG_KEYWORDS.search(last_msg):
            base = min(max_tokens, max_tokens * 1.5)

        # --- conversation turn factor ---
        # Multi-turn conversations tend to produce longer outputs
        if turn_count > 2:
            turn_factor = 1.0 + 0.1 * (turn_count - 2)
            base *= turn_factor

        # --- prompt length signal ---
        # Very short prompts (< 20 chars) often get short answers
        if char_count < 20:
            base *= 0.7
        # Very long prompts tend to request proportionally long outputs
        elif word_count > 500:
            base *= 1.2

        # --- max_tokens hint ---
        # If client explicitly set a low max_tokens, trust it
        effective_max = body.get("max_tokens")
        if effective_max is not None and effective_max < base:
            base = float(effective_max)

        return base


class PassthroughPredictor(LengthPredictor):
    """Returns a constant so all requests have equal priority (FCFS).

    Useful as a baseline when benchmarking.
    """

    def predict(self, body: dict) -> float:
        return 1.0
