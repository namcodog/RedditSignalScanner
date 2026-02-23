from __future__ import annotations

from app.services.hotpost.keywords import HotpostLexicon
from app.services.hotpost.rules import (
    classify_intent_label,
    classify_pain_category,
    compute_signal_score,
    count_resonance,
    detect_discovery_signals,
    detect_rant_signals,
    normalize_pain_category_label,
    normalize_text,
)


def _lexicon() -> HotpostLexicon:
    return HotpostLexicon(
        rant_signals={
            "strong": ["worst purchase"],
            "medium": ["broken"],
            "weak": ["not great"],
        },
        opportunity_signals={
            "seeking": ["looking for"],
            "unmet_need": ["i wish there was"],
            "resonance": ["me too", "+1"],
        },
        discovery_signals={
            "positive": ["love this"],
            "hidden_gem": ["hidden gem"],
        },
        intent_label={
            "already_left": ["switched from"],
            "considering": ["thinking of switching"],
        },
        pain_categories={
            "pricing": ["expensive"],
            "performance": ["slow"],
            "reliability": ["broken"],
            "support": ["support"],
            "ux": ["confusing"],
            "other": [],
        },
    )


def test_detect_rant_signals_and_score() -> None:
    lexicon = _lexicon()
    text = normalize_text("This was the worst purchase and it is broken.")
    matches = detect_rant_signals(text, lexicon)

    assert matches["strong"] == ["worst purchase"]
    assert matches["medium"] == ["broken"]

    score = compute_signal_score(matches, score=100, num_comments=10)
    assert score > 0


def test_classify_intent_and_category() -> None:
    lexicon = _lexicon()
    text = normalize_text("I am thinking of switching because it is expensive.")

    assert classify_intent_label(text, lexicon) == "considering"
    assert classify_pain_category(text, lexicon) == "pricing"
    assert normalize_pain_category_label("💰 Pricing pain", lexicon) == "pricing"


def test_classify_pain_category_prefers_most_matches() -> None:
    lexicon = _lexicon()
    text = normalize_text("This is confusing and very confusing but also expensive.")

    assert classify_pain_category(text, lexicon) == "ux"


def test_count_resonance() -> None:
    lexicon = _lexicon()
    comments = [
        {"body": "me too, same issue"},
        {"body": "+1 on this"},
        {"body": "no resonance here"},
    ]

    assert count_resonance(comments, lexicon) == 2


def test_detect_discovery_signals() -> None:
    lexicon = _lexicon()
    text = normalize_text("This is a hidden gem and I love this product.")
    matches = detect_discovery_signals(text, lexicon)

    assert matches["positive"] == ["love this"]
    assert matches["hidden_gem"] == ["hidden gem"]
