from __future__ import annotations

from app.services.llm.label_contract import (
    normalize_comment_analysis,
    normalize_post_analysis,
    score_comment_analysis,
    score_post_analysis,
)


def test_normalize_comment_analysis_applies_defaults() -> None:
    normalized = normalize_comment_analysis(
        {
            "main_intent": "Complain ",
            "pain_tags": " shipping ",
            "entities": {"known": ["  amazon  "]},
            "crossborder_signals": {"mentions_shipping": "yes"},
        }
    )

    assert normalized == {
        "content_type": "other",
        "main_intent": "complain",
        "sentiment": 0.0,
        "pain_tags": ["shipping"],
        "aspect_tags": [],
        "entities": {"known": ["amazon"], "new": []},
        "crossborder_signals": {
            "mentions_shipping": True,
            "mentions_tax": False,
        },
        "purchase_intent_score": 0.0,
        "actor_type": "other",
    }


def test_score_post_analysis_promotes_core_pool_for_high_value() -> None:
    score = score_post_analysis(
        normalize_post_analysis(
            {
                "content_type": "user_review",
                "main_intent": "share_solution",
                "pain_tags": ["price", "shipping", "quality"],
                "crossborder_signals": {"mentions_shipping": True},
                "purchase_intent_score": 0.85,
            }
        )
    )

    assert score.business_pool == "core"
    assert score.value_score >= 8.0
    assert score.opportunity_score > 0


def test_score_comment_analysis_demotes_offtopic_to_noise() -> None:
    score = score_comment_analysis(
        normalize_comment_analysis(
            {
                "actor_type": "other",
                "main_intent": "offtopic",
                "pain_tags": [],
                "purchase_intent_score": 0,
            }
        )
    )

    assert score.business_pool == "noise"
    assert score.value_score <= 3.9
