from __future__ import annotations

from app.services.analysis.quote_extractor import QuoteExtractor


def _mk_pain(description: str, user_examples: list[str] | None = None, posts: list[dict[str, str]] | None = None) -> dict:
    return {
        "description": description,
        "user_examples": user_examples or [],
        "example_posts": posts or [],
    }


def test_quote_extractor_basic_ranking_and_limits() -> None:
    pain = _mk_pain(
        "Shipping integration setup is too complex and error-prone for small teams",
        user_examples=[
            "I can't believe we still have to manually map carriers and it's breaking every week! This makes onboarding new ops really painful.",
            "Docs are outdated and the setup wizard fails with unknown errors — anyone else facing this recently? Our team is stuck troubleshooting instead of shipping.",
        ],
        posts=[{"content": "Integration cost is higher than subscription; manual labels again this quarter. Why is it so broken?"}],
    )

    ext = QuoteExtractor()
    out = ext.extract_from_pain_points([pain], quotes_per_pain=2)
    assert len(out) == 1
    quotes = out[0]["quotes"]
    assert 0 < len(quotes) <= 2
    # 长度约束 & 排序
    last_score = 1.1
    for q in quotes:
        assert 50 <= q["length"] <= 150
        assert 0.0 <= q["score"] <= 1.0
        assert q["score"] <= last_score
        last_score = q["score"]


def test_quote_extractor_cleans_url_and_mentions() -> None:
    pain = _mk_pain(
        "Payment gateway errors",
        user_examples=[
            "Check this https://example.com @john — we get 'Error 500' every Friday! It blocks payouts for the whole team and causes manual re-runs.",
        ],
    )
    ext = QuoteExtractor()
    out = ext.extract_from_pain_points([pain], quotes_per_pain=1)
    quotes = out[0]["quotes"]
    assert len(quotes) == 1
    text = quotes[0]["text"]
    assert "http" not in text
    assert "@john" not in text
    assert "`" not in text


def test_quote_extractor_handles_empty_and_short_inputs() -> None:
    pain = _mk_pain("Short text", user_examples=["ok", "bad"], posts=[{"content": "fine"}])
    ext = QuoteExtractor()
    out = ext.extract_from_pain_points([pain], quotes_per_pain=2)
    assert len(out) == 1
    assert out[0]["quotes"] == []

