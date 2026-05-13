from __future__ import annotations

import json

from app.services.llm.label_persistence import (
    build_comment_label_row,
    build_post_label_row,
)


def test_build_comment_label_row_serializes_analysis_and_score() -> None:
    row = build_comment_label_row(
        comment_id=12,
        llm_version="v-test",
        model_name="codex-test",
        prompt_version="p1",
        analysis={
            "sentiment": 0.4,
            "purchase_intent_score": 0.7,
            "entities": {"known": ["roborock"], "new": []},
        },
        score={
            "value_score": 8.5,
            "opportunity_score": 6.2,
            "business_pool": "core",
        },
        input_chars=11,
        output_chars=22,
    )

    assert row["comment_id"] == 12
    assert row["business_pool"] == "core"
    assert row["input_chars"] == 11
    assert json.loads(row["tags_analysis"])["purchase_intent_score"] == 0.7
    assert json.loads(row["entities_extracted"])["known"] == ["roborock"]


def test_build_post_label_row_keeps_text_hash_and_serializes_entities() -> None:
    row = build_post_label_row(
        post_id=34,
        text_norm_hash="hash-34",
        llm_version="v-test",
        model_name="codex-test",
        prompt_version="p1",
        analysis={
            "sentiment": -0.2,
            "purchase_intent_score": 0.0,
            "entities": {"known": [], "new": ["shopify"]},
        },
        score={
            "value_score": 5.1,
            "opportunity_score": 4.2,
            "business_pool": "lab",
        },
        input_chars=33,
        output_chars=44,
    )

    assert row["post_id"] == 34
    assert row["text_norm_hash"] == "hash-34"
    assert row["business_pool"] == "lab"
    assert json.loads(row["entities_extracted"])["new"] == ["shopify"]
