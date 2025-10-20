"""Utility helpers for text cleaning and context-aware opportunity scoring."""

from __future__ import annotations

import re
from typing import Sequence

from app.services.analysis.opportunity_scorer import OpportunityScorer

_URL_PATTERN = re.compile(r"https?://\S+")
_CODE_BLOCK_PATTERN = re.compile(r"```[\s\S]*?```", re.MULTILINE)
_INLINE_CODE_PATTERN = re.compile(r"`{1,3}[^`]*`{1,3}")
_QUOTE_LINE_PATTERN = re.compile(r"^>.*$", re.MULTILINE)
_WHITESPACE_PATTERN = re.compile(r"\s+")

_DEFAULT_SCORER = OpportunityScorer()


def clean_text(text: str) -> str:
    """Remove URLs, code blocks, and markdown quotes while preserving content."""

    if not text:
        return ""

    cleaned = _URL_PATTERN.sub("", text)
    cleaned = _CODE_BLOCK_PATTERN.sub("", cleaned)
    cleaned = _INLINE_CODE_PATTERN.sub("", cleaned)
    cleaned = _QUOTE_LINE_PATTERN.sub("", cleaned)
    cleaned = _WHITESPACE_PATTERN.sub(" ", cleaned)
    return cleaned.strip()


def score_with_context(
    sentences: Sequence[str],
    index: int,
    scorer: OpportunityScorer | None = None,
) -> float:
    """Score a sentence using ±1 sentence context window."""

    if index < 0 or index >= len(sentences) or not sentences:
        return 0.0

    scorer = scorer or _DEFAULT_SCORER
    start = max(0, index - 1)
    end = min(len(sentences), index + 2)
    window = " ".join(sentence.strip() for sentence in sentences[start:end]).strip()
    window = clean_text(window)
    if not window:
        return 0.0

    result = scorer.score(window)
    return result.base_score


__all__ = ["clean_text", "score_with_context"]
