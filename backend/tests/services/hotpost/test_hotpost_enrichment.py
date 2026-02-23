from __future__ import annotations

from collections import Counter

from app.services.hotpost.enrichment import enrich_opportunity_payload, enrich_rant_payload
from app.services.hotpost.keywords import HotpostLexicon


def _lexicon() -> HotpostLexicon:
    return HotpostLexicon(
        rant_signals={},
        opportunity_signals={},
        discovery_signals={},
        intent_label={},
        pain_categories={
            "pricing": ["price", "pricing", "expensive"],
            "performance": ["slow"],
            "reliability": ["broken"],
            "support": ["support"],
            "ux": ["ux", "ui"],
            "other": [],
        },
    )


def test_enrich_rant_payload_fills_missing_fields() -> None:
    payload = {
        "pain_points": [
            {
                "category": "💰 定价过高",
                "sample_quotes": ["too expensive"],
                "evidence_posts": [{"body_preview": "body voice"}],
            }
        ]
    }
    enriched = enrich_rant_payload(
        payload,
        category_counts=Counter({"pricing": 5}),
        lexicon=_lexicon(),
        fallback_quotes=["fallback quote"],
        evidence_count=10,
    )
    point = enriched["pain_points"][0]
    assert point["mentions"] == 5
    assert point["category_en"] == "pricing"
    assert point["percentage"] == 0.5
    assert point["rank"] == 1
    assert point["user_voice"] == "body voice"
    assert point["business_implication"] == "需进一步验证"


def test_enrich_opportunity_payload_from_opportunities() -> None:
    payload = {"opportunities": [{"summary": "Need better automation"}]}
    enriched = enrich_opportunity_payload(payload, me_too_count=3, opportunity_strength="medium")
    assert enriched["unmet_needs"][0]["need"] == "Need better automation"
    assert enriched["unmet_needs"][0]["me_too_count"] == 3


def test_enrich_opportunity_payload_fills_user_voice_from_evidence() -> None:
    payload = {
        "unmet_needs": [
            {
                "need": "Need better automation",
                "evidence_posts": [{"body_preview": "I need this badly"}],
            }
        ]
    }
    enriched = enrich_opportunity_payload(payload, me_too_count=1, opportunity_strength="weak")
    assert enriched["unmet_needs"][0]["user_voice"] == "I need this badly"
