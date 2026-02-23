"""Utility helpers for text cleaning and context-aware opportunity scoring."""

from __future__ import annotations

import hashlib
import re
from typing import Callable, Sequence

from app.services.analysis.opportunity_scorer import OpportunityScorer

_URL_PATTERN = re.compile(r"https?://\S+")
_EMAIL_PATTERN = re.compile(r"\b[\w.\-+]+@[\w\-.]+\.\w+\b")
_CODE_BLOCK_PATTERN = re.compile(r"```[\s\S]*?```", re.MULTILINE)
_INLINE_CODE_PATTERN = re.compile(r"`{1,3}[^`]*`{1,3}")
_MARKDOWN_LINK_PATTERN = re.compile(r"\[([^\]]+)\]\([^)]+\)")
_QUOTE_LINE_PATTERN = re.compile(r"^>.*$", re.MULTILINE)
_WHITESPACE_PATTERN = re.compile(r"\s+")
_SENTENCE_SPLIT_PATTERN = re.compile(r"[.!?\n]+")

_DEFAULT_SCORER = OpportunityScorer()


def clean_text(text: str) -> str:
    """Remove URLs, code blocks, and markdown quotes while preserving content."""

    if not text:
        return ""

    cleaned = _URL_PATTERN.sub("", text)
    cleaned = _CODE_BLOCK_PATTERN.sub("", cleaned)
    cleaned = _INLINE_CODE_PATTERN.sub("", cleaned)
    cleaned = _MARKDOWN_LINK_PATTERN.sub(r"\1", cleaned)
    cleaned = _EMAIL_PATTERN.sub("", cleaned)
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


def split_sentences(text: str) -> list[str]:
    if not text:
        return []
    return [segment.strip() for segment in _SENTENCE_SPLIT_PATTERN.split(text) if segment.strip()]


def _normalized_sentence(sentence: str) -> str:
    lowered = sentence.lower().strip()
    alpha_numeric = re.sub(r"[^a-z0-9\s]", " ", lowered)
    squashed = _WHITESPACE_PATTERN.sub(" ", alpha_numeric)
    return squashed.strip()


def sentence_hash(sentence: str) -> str:
    normalized = _normalized_sentence(sentence)
    if not normalized:
        return ""
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def clean_template_sentences(
    text: str,
    *,
    df_lookup: Callable[[str], float] | None = None,
    seen_hashes: set[str] | None = None,
) -> str:
    """
    Remove template-like sentences using DF and exact-match safeguards.

    - Long sentences (>10 words) are dropped when document frequency > 0.3
    - Short sentences (<=10 words) are deduped via normalized hash
    """

    df_func = df_lookup or (lambda _s: 0.0)
    seen = seen_hashes if seen_hashes is not None else set()
    cleaned: list[str] = []

    for sent in split_sentences(text):
        word_count = len(sent.split())
        if word_count > 10:
            try:
                df_value = float(df_func(sent))
            except Exception:
                df_value = 0.0
            if df_value > 0.3:
                continue
        else:
            digest = sentence_hash(sent)
            if digest and digest in seen:
                continue
            if digest:
                seen.add(digest)
        cleaned.append(sent.strip())

    return " ".join(cleaned).strip()


__all__ = ["clean_text", "score_with_context", "split_sentences", "sentence_hash", "clean_template_sentences"]
