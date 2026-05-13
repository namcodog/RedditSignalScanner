from __future__ import annotations

from app.services.hotpost.signal_eval_review_packet_builder import (
    build_signal_failure_taxonomy,
    build_signal_review_packet,
)


def _case(eval_case_id: str, scope_id: str, pack_id: str) -> dict:
    return {
        "eval_case_id": eval_case_id,
        "sample_origin": "published_validate",
        "input_bundle": {
            "source_scope_id": scope_id,
            "source_scope_name": scope_id,
            "topic_pack_id": pack_id,
            "signal_level": "rising",
            "why_now_reason": "recurring_7d",
            "intent_tags": ["趋势变化"],
            "thread_count": 1,
            "community_count": 1,
            "quote_count": 2,
            "source_communities": ["r/test"],
            "evidence_quotes": [{"text": "quote", "community": "r/test"}],
        },
        "baseline_output": {
            "title": "title",
            "summary_line": "summary",
            "audience": "谁在聊",
            "why_now": "为什么值得看",
            "detail": {},
        },
        "metadata": {"case_polarity": "published"},
    }


def test_build_signal_review_packet_includes_case_fields() -> None:
    packet = build_signal_review_packet(
        [_case("case-1", "ai-automation", "agent-builder")],
        [{"eval_case_id": "case-1", "overall_pass": None, "field_passes": {"title": None}, "failure_tags": [], "review_notes": ""}],
    )

    assert "# Signal Eval Review Packet V1" in packet
    assert "Case 1" in packet
    assert "ai-automation" in packet
    assert "title：title" in packet
    assert "summary_line：summary" in packet


def test_build_signal_failure_taxonomy_lists_seed_tags_and_coverage() -> None:
    taxonomy = build_signal_failure_taxonomy(
        [_case("case-1", "ai-automation", "agent-builder"), _case("case-2", "ecommerce-sellers", "selection-signals")]
    )

    assert "# Signal Failure Taxonomy V1" in taxonomy
    assert "`ai-automation / agent-builder`: `1`" in taxonomy
    assert "`ecommerce-sellers / selection-signals`: `1`" in taxonomy
    assert "`reddit_restatement`" in taxonomy
