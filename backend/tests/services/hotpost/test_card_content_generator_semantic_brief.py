from __future__ import annotations

from app.services.hotpost.card_content_generator import _semantic_brief_json_schema


def test_semantic_brief_schema_has_quality_contract_fields() -> None:
    schema = _semantic_brief_json_schema()
    props = schema["properties"]

    assert props["confidence_level"]["enum"] == ["high", "medium", "low"]
    assert props["publish_risk"]["enum"] == [
        "pass",
        "needs_human_review",
        "block",
    ]
    assert props["claim_type"]["enum"] == [
        "channel_test",
        "market_validation",
        "tool_adoption",
        "platform_risk",
        "generic_advice",
        "unknown",
    ]
    assert "evidence_strength" in props
    assert "writer_constraints" in props
    assert "confidence_level" in schema["required"]
    assert "publish_risk" in schema["required"]
