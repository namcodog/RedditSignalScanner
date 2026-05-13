from __future__ import annotations

from app.services.llm.label_prefilter import (
    allocate_domain_quotas,
    build_batch_plan,
    prefilter_comment_rows,
)


def test_prefilter_comment_rows_filters_short_dedup_and_pool() -> None:
    rows = [
        {"id": 1, "body": "Useful long comment about shipping delays", "business_pool": "core"},
        {"id": 2, "body": "short", "business_pool": "core"},
        {"id": 3, "body": "Useful   long comment about shipping delays", "business_pool": "core"},
        {"id": 4, "body": "Another useful long comment about packaging issues", "business_pool": "noise"},
    ]

    admitted, stats = prefilter_comment_rows(
        rows,
        min_chars=20,
        allowed_pools={"core", "lab"},
    )

    assert [row["id"] for row in admitted] == [1]
    assert stats.admitted == 1
    assert stats.filtered_short == 1
    assert stats.deduped == 1
    assert stats.skipped_pool == 1


def test_allocate_domain_quotas_uses_base_and_weighted_remainder() -> None:
    quotas = allocate_domain_quotas(
        candidate_counts={
            "Home_Lifestyle": 40_000,
            "Ecommerce_Business": 20_000,
            "AI_Workflow": 10_000,
        },
        weight_counts={
            "Home_Lifestyle": 30,
            "Ecommerce_Business": 20,
            "AI_Workflow": 5,
        },
        target_total=60_000,
        base_quota=8_000,
    )

    assert sum(quotas.values()) == 60_000
    assert quotas["Home_Lifestyle"] >= 8_000
    assert quotas["Ecommerce_Business"] >= 8_000
    assert quotas["AI_Workflow"] >= 8_000
    assert quotas["Home_Lifestyle"] > quotas["Ecommerce_Business"] > quotas["AI_Workflow"]


def test_build_batch_plan_starts_with_smaller_validation_batch() -> None:
    assert build_batch_plan(120_000, first_batch_size=20_000, batch_size=25_000) == [
        20_000,
        25_000,
        25_000,
        25_000,
        25_000,
    ]
