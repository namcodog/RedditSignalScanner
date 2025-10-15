"""
TF-IDF based keyword extraction aligned with PRD/PRD-03-分析引擎.md §3.1.

This module is responsible for turning a free-form product description into a
weighted keyword list that subsequent analysis steps (e.g. community discovery)
can consume. The implementation mirrors the Day 6 Backend A deliverables:
    1. Rigorous text normalisation (strip noise, URLs, emails, HTML, unicode).
    2. Support for 1-2 gram feature extraction.
    3. Deterministic weighting so the top keyword always has weight 1.0.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

import re

from sklearn.feature_extraction.text import TfidfVectorizer


_URL_PATTERN = re.compile(r"(https?://\S+|www\.\S+)", flags=re.IGNORECASE)
_EMAIL_PATTERN = re.compile(r"\b[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}\b")
_HTML_TAG_PATTERN = re.compile(r"<[^>]+>")
_NON_ASCII_PATTERN = re.compile(r"[^\x00-\x7F]+")
_SPECIAL_CHAR_PATTERN = re.compile(r"[^a-z0-9\s-]+")
_HYPHEN_UNDERSCORE_PATTERN = re.compile(r"[-_]+")


@dataclass(frozen=True)
class KeywordExtractionResult:
    """Structured result for downstream analysis steps."""

    keywords: List[str]
    weights: Dict[str, float]
    total_keywords: int


async def extract_keywords(
    text: str,
    *,
    max_keywords: int = 20,
    min_keyword_length: int = 3,
) -> KeywordExtractionResult:
    """
    Extract weighted keywords from a product description using TF-IDF.

    Args:
        text: Raw product description supplied by the user.
        max_keywords: Maximum number of keywords to return.
        min_keyword_length: Minimum length for a keyword to be considered.

    Returns:
        KeywordExtractionResult: Weighted keywords sorted by relevance.

    Raises:
        ValueError: If the input is empty/too short or no keywords can be found.
    """

    if not text or len(text.strip()) < 10:
        raise ValueError("Input text must be at least 10 characters long.")

    cleaned_text = _preprocess_text(text)
    if len(cleaned_text) < 10:
        raise ValueError("Text became too short after preprocessing.")

    vectorizer = TfidfVectorizer(
        max_features=max_keywords * 2,
        stop_words="english",
        lowercase=True,
        min_df=1,
        ngram_range=(1, 2),
        token_pattern=r"(?u)\b[a-z]{2,}\b",
    )

    try:
        tfidf_matrix = vectorizer.fit_transform([cleaned_text])
    except ValueError as exc:
        raise ValueError(f"TF-IDF extraction failed: {exc}") from exc

    feature_names = vectorizer.get_feature_names_out()
    if not feature_names.size:
        raise ValueError("TF-IDF vocabulary is empty after preprocessing.")

    scores = tfidf_matrix.toarray()[0]
    keyword_scores = [
        (feature_names[index], float(scores[index]))
        for index in range(len(feature_names))
        if len(feature_names[index]) >= min_keyword_length
    ]

    if not keyword_scores:
        raise ValueError(
            "No keywords extracted. Text may contain only stop words or very short tokens."
        )

    keyword_scores.sort(key=lambda item: item[1], reverse=True)
    top_keywords = keyword_scores[:max_keywords]

    max_score = max(score for _, score in top_keywords)
    if max_score <= 0.0:
        weights: Dict[str, float] = {keyword: 0.0 for keyword, _ in top_keywords}
    else:
        weights = {
            keyword: round(score / max_score, 6) for keyword, score in top_keywords
        }

    keywords = [keyword for keyword, _ in top_keywords]
    return KeywordExtractionResult(
        keywords=keywords,
        weights=weights,
        total_keywords=len(keywords),
    )


def _preprocess_text(text: str) -> str:
    """Normalise text so TF-IDF operates on clean ASCII tokens."""

    lowered = text.lower()
    without_html = _HTML_TAG_PATTERN.sub(" ", lowered)
    without_urls = _URL_PATTERN.sub(" ", without_html)
    without_emails = _EMAIL_PATTERN.sub(" ", without_urls)
    ascii_only = _NON_ASCII_PATTERN.sub(" ", without_emails)
    normalised_hyphen = _HYPHEN_UNDERSCORE_PATTERN.sub(" ", ascii_only)
    cleaned = _SPECIAL_CHAR_PATTERN.sub(" ", normalised_hyphen)
    collapsed = re.sub(r"\s+", " ", cleaned).strip()
    return collapsed


__all__ = ["KeywordExtractionResult", "extract_keywords"]
