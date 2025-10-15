from __future__ import annotations

import pytest

from app.services.analysis.keyword_extraction import (
    KeywordExtractionResult,
    _preprocess_text,
    extract_keywords,
)


pytestmark = pytest.mark.anyio


async def test_extract_keywords_basic() -> None:
    result = await extract_keywords(
        (
            "AI-powered note-taking app for researchers and product managers. "
            "Automatically organises findings and surfaces related insights."
        ),
        max_keywords=8,
    )

    assert isinstance(result, KeywordExtractionResult)
    assert 0 < len(result.keywords) <= 8
    assert result.total_keywords == len(result.keywords)
    keywords_blob = " ".join(result.keywords)
    assert "ai" in keywords_blob or "note" in keywords_blob


async def test_extract_keywords_weights_are_normalised() -> None:
    result = await extract_keywords(
        "machine learning machine learning deep learning automation automation ai",
        max_keywords=5,
    )

    assert any(value == pytest.approx(1.0) for value in result.weights.values())
    assert all(0.0 <= value <= 1.0 for value in result.weights.values())


async def test_extract_keywords_supports_bigrams() -> None:
    result = await extract_keywords(
        (
            "Machine learning enables smarter automation. "
            "Deep learning extends machine learning workflows."
        ),
        max_keywords=10,
    )

    assert any(" " in keyword for keyword in result.keywords)


async def test_extract_keywords_input_validation() -> None:
    with pytest.raises(ValueError):
        await extract_keywords("")

    with pytest.raises(ValueError):
        await extract_keywords("short")


async def test_extract_keywords_rejects_noise_only_text() -> None:
    with pytest.raises(ValueError):
        await extract_keywords("!@#$%^&*() _-+= {}[]")


def test_preprocess_text_cleans_noise() -> None:
    cleaned = _preprocess_text(
        "AI-powered! Visit https://example.com or email test@example.com <div>Now</div>"
    )
    assert "http" not in cleaned
    assert "example.com" not in cleaned
    assert "@" not in cleaned
    assert "<div>" not in cleaned
    assert "ai powered" in cleaned


def test_preprocess_text_handles_unicode() -> None:
    cleaned = _preprocess_text("AI 应用 машинное обучение automation")
    assert all(ord(char) < 128 for char in cleaned if char != " ")
