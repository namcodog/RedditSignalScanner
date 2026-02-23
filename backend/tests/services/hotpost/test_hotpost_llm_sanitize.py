from __future__ import annotations

from app.services.hotpost.report_llm import sanitize_llm_report


def test_sanitize_llm_report_drops_unknown_fields() -> None:
    payload = {
        "summary": "ok",
        "topics": [
            {
                "rank": 1,
                "topic": "Topic A",
                "evidence_post_ids": ["p1"],
                "extra_field": "drop me",
            }
        ],
        "post_annotations": {
            "p1": {"why_relevant": "important", "extra": "drop me"}
        },
        "unknown_top": "drop me",
    }

    cleaned = sanitize_llm_report(payload)
    assert "unknown_top" not in cleaned
    assert "extra_field" not in cleaned["topics"][0]
    assert cleaned["topics"][0]["evidence_post_ids"] == ["p1"]
    assert cleaned["post_annotations"]["p1"] == {"why_relevant": "important"}
