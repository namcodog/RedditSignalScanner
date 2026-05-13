from __future__ import annotations

from app.services.hotpost.breakdown_eval_review_packet_builder import (
    build_breakdown_failure_taxonomy,
    build_breakdown_review_packet,
)


def _case(eval_case_id: str, scope_id: str, pack_id: str) -> dict:
    return {
        "eval_case_id": eval_case_id,
        "sample_origin": "suggestion_write",
        "input_bundle": {
            "source_scope_id": scope_id,
            "topic_pack_id": pack_id,
            "suggestion_id": "sug-1",
            "candidate_ids": ["cand-1", "cand-2"],
            "thread_count": 2,
            "community_count": 2,
            "intent_tags": ["趋势变化"],
            "hypothesis": "surface A but really B",
            "reason_codes": ["shared_object"],
            "source_communities": ["r/OpenAI", "r/ClaudeAI"],
            "evidence_quotes": [{"text": "quote", "community": "r/OpenAI"}],
        },
        "baseline_output": {
            "title": "title",
            "summary_line": "summary",
            "audience": "谁在聊",
            "why_now": "为什么值得看",
            "detail": {"thesis": "thesis", "tension_point_or_why_it_matters": "tension", "quote_pack": ["q1", "q2"]},
        },
        "metadata": {"case_polarity": "pending_review"},
    }


def test_build_breakdown_review_packet_includes_case_fields() -> None:
    packet = build_breakdown_review_packet(
        [_case("case-1", "ai-automation", "agent-builder")],
        [{"eval_case_id": "case-1", "overall_pass": None, "field_passes": {"title": None}, "failure_tags": [], "review_notes": ""}],
    )

    assert "# Breakdown Eval Review Packet V1" in packet
    assert "Case 1" in packet
    assert "agent-builder" in packet
    assert "hypothesis" in packet
    assert "thesis：thesis" in packet


def test_build_breakdown_failure_taxonomy_lists_seed_tags_and_coverage() -> None:
    taxonomy = build_breakdown_failure_taxonomy(
        [_case("case-1", "ai-automation", "agent-builder"), _case("case-2", "ecommerce-sellers", "selection-signals")]
    )

    assert "# Breakdown Failure Taxonomy V1" in taxonomy
    assert "`ai-automation / agent-builder`: `1`" in taxonomy
    assert "`ecommerce-sellers / selection-signals`: `1`" in taxonomy
    assert "`weak_thesis`" in taxonomy
