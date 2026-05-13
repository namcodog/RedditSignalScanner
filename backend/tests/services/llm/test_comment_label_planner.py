from __future__ import annotations

from app.services.llm.comment_label_planner import (
    build_comment_activation_export_plan,
    build_incremental_comment_label_plan_from_rows,
    interleave_selected_rows_by_domain,
)


def _row(
    *,
    comment_id: int,
    body: str,
    category: str,
    business_pool: str = "unscored",
    value_score: float = 0.0,
    score: int = 10,
) -> dict[str, object]:
    return {
        "id": comment_id,
        "body": body,
        "subreddit": "r/test",
        "post_title": f"post-{comment_id}",
        "categories": [category],
        "business_pool": business_pool,
        "value_score": value_score,
        "score": score,
        "post_score": score + 5,
        "post_num_comments": score + 3,
    }


def test_build_incremental_comment_label_plan_from_rows_applies_rules() -> None:
    body = "This product is amazing and solved my problem completely"
    plan = build_incremental_comment_label_plan_from_rows(
        [
            _row(
                comment_id=1,
                body=body,
                category="Home_Lifestyle",
                business_pool="core",
                value_score=9.0,
            ),
            _row(
                comment_id=2,
                body=body,
                category="Home_Lifestyle",
                business_pool="lab",
                value_score=6.0,
            ),
            _row(
                comment_id=3,
                body="short",
                category="AI_Workflow",
                business_pool="core",
                value_score=8.0,
            ),
            _row(
                comment_id=4,
                body="This should be skipped because it is noise but still long enough",
                category="AI_Workflow",
                business_pool="noise",
                value_score=8.0,
            ),
        ]
    )

    assert plan.raw_candidate_count == 4
    assert len(plan.candidates) == 1
    assert plan.prefilter_stats.filtered_short == 1
    assert plan.prefilter_stats.deduped == 1
    assert plan.prefilter_stats.skipped_pool == 1


def test_build_comment_activation_export_plan_applies_domain_quota_and_batches() -> None:
    rows = [
        _row(comment_id=1, body="A" * 30, category="Home_Lifestyle", business_pool="core", value_score=9.0),
        _row(comment_id=2, body="B" * 30, category="Home_Lifestyle", business_pool="lab", value_score=6.0),
        _row(comment_id=3, body="C" * 30, category="Ecommerce_Business", business_pool="lab", value_score=5.0),
        _row(comment_id=4, body="D" * 30, category="AI_Workflow", business_pool="unscored", value_score=0.0),
        _row(comment_id=5, body="short", category="AI_Workflow", business_pool="core", value_score=8.0),
        _row(comment_id=6, body="A" * 30, category="Home_Lifestyle", business_pool="core", value_score=8.0),
    ]

    plan = build_comment_activation_export_plan(
        rows=rows,
        max_body_chars=120,
        effective_domain_weights={
            "Home_Lifestyle": 30,
            "Ecommerce_Business": 21,
            "AI_Workflow": 5,
        },
        target_total=4,
        base_quota=1,
        first_batch_size=2,
        batch_size=2,
    )

    assert sum(batch.size for batch in plan.batches) == 4
    assert [batch.size for batch in plan.batches] == [2, 2]
    assert plan.summary["eligible_comment_pool"] == 4
    assert plan.summary["rule_stats"]["filtered_short"] == 1
    assert plan.summary["rule_stats"]["deduped"] == 1
    assert plan.summary["domain_distribution"]["Home_Lifestyle"] == 2
    assert plan.summary["domain_distribution"]["Ecommerce_Business"] == 1
    assert plan.summary["domain_distribution"]["AI_Workflow"] == 1
    assert plan.summary["batch_plan"] == [{"batch": 1, "size": 2}, {"batch": 2, "size": 2}]


def test_interleave_selected_rows_by_domain_rotates_domains() -> None:
    rows_by_domain = {
        "Home_Lifestyle": [
            {"id": 1, "domain": "Home_Lifestyle"},
            {"id": 2, "domain": "Home_Lifestyle"},
        ],
        "Ecommerce_Business": [
            {"id": 3, "domain": "Ecommerce_Business"},
        ],
        "AI_Workflow": [
            {"id": 4, "domain": "AI_Workflow"},
            {"id": 5, "domain": "AI_Workflow"},
        ],
    }

    rows = interleave_selected_rows_by_domain(rows_by_domain)

    assert [row["domain"] for row in rows] == [
        "Home_Lifestyle",
        "AI_Workflow",
        "Ecommerce_Business",
        "Home_Lifestyle",
        "AI_Workflow",
    ]
