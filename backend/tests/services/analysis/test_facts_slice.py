from __future__ import annotations

from app.services.facts_v2.slice import build_facts_slice_for_report


def test_build_facts_slice_for_report_trims_payload() -> None:
    facts_v2_package = {
        "schema_version": "2.0",
        "meta": {"topic": "test-topic"},
        "data_lineage": {"source_range": {"posts": 120, "comments": 400}},
        "aggregates": {
            "communities": [
                {"name": f"r/test{i}", "posts": i + 1, "comments": i} for i in range(12)
            ]
        },
        "business_signals": {
            "high_value_pains": [{"description": "fee too high"}],
            "brand_pain": [{"brand": "BrandX"}],
            "solutions": [{"description": "reduce fees"}],
        },
        "sample_posts_db": [{"id": i, "title": f"post {i}"} for i in range(25)],
        "sample_comments_db": [{"id": i, "body": f"comment {i}"} for i in range(40)],
    }
    facts_quality = {"passed": True, "tier": "A_full", "flags": []}

    facts_slice = build_facts_slice_for_report(
        facts_v2_package=facts_v2_package,
        facts_v2_quality=facts_quality,
    )

    assert facts_slice["facts_v2_quality"]["tier"] == "A_full"
    assert len(facts_slice["aggregates"]["communities"]) == 8
    assert len(facts_slice["sample_posts_db"]) == 20
    assert len(facts_slice["sample_comments_db"]) == 30
