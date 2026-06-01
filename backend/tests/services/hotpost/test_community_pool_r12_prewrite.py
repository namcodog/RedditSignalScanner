from __future__ import annotations

from pathlib import Path

from app.services.community.interest_tag_catalog import load_interest_tag_catalog
from app.services.hotpost.community_pool_r12_prewrite import build_r12_prewrite_plan


SERVICE_SOURCE = (
    Path(__file__).resolve().parents[3]
    / "app"
    / "services"
    / "hotpost"
    / "community_pool_r12_prewrite.py"
)


def _feedback_row(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "already_in_pool": False,
        "community": "r/TestGrowth",
        "evidence": {
            "candidate_count": 2,
            "draft_count": 0,
            "duplicate_count": 0,
            "published_count": 2,
            "reject_count": 0,
            "total_evidence": 4,
        },
        "feedback_action": "promote_candidate",
        "risks": [],
        "source_scope": "business-growth-ops",
        "suggested_user_tags": ["Example Tag"],
        "topic_cluster": "funnel",
        "value_assessment": {"score": 91, "stage": "pool_candidate"},
    }
    row.update(overrides)
    return row


def test_build_r12_prewrite_plan_only_accepts_pool_candidates() -> None:
    payload = build_r12_prewrite_plan(
        {
            "report_date": "2026-05-10",
            "rows": [
                _feedback_row(community="r/AEO"),
                _feedback_row(
                    community="r/CursorAI",
                    feedback_action="keep_testing",
                    value_assessment={"score": 58, "stage": "validated"},
                ),
            ],
        },
        active_pool_keys=set(),
        deleted_pool_keys=set(),
    )

    assert payload["summary"] == {
        "input_rows": 2,
        "candidate_rows": 1,
        "would_insert": 1,
        "skipped_existing": 0,
        "blocked": 0,
    }
    assert payload["rows"][0]["community"] == "r/aeo"
    assert payload["rows"][0]["write_preview"]["would_insert_pool"] is True
    assert payload["contracts"]["writes_db"] is False


def test_build_r12_prewrite_plan_skips_existing_and_deleted_conflicts() -> None:
    payload = build_r12_prewrite_plan(
        {
            "rows": [
                _feedback_row(community="r/Existing"),
                _feedback_row(community="r/Deleted"),
            ]
        },
        active_pool_keys={"existing"},
        deleted_pool_keys={"deleted"},
    )

    rows = payload["rows"]

    assert rows[0]["write_preview"]["action"] == "skip_existing"
    assert rows[1]["write_preview"]["action"] == "blocked_deleted_conflict"
    assert payload["summary"]["would_insert"] == 0
    assert payload["summary"]["blocked"] == 1


def test_r12_prewrite_plan_keeps_label_mapping_from_payload() -> None:
    payload = build_r12_prewrite_plan(
        {"rows": [_feedback_row(suggested_user_tags=["广告投放", "内容营销创作"])]},
        active_pool_keys=set(),
        deleted_pool_keys=set(),
    )

    row = payload["rows"][0]

    assert row["suggested_user_tags"] == ["广告投放", "内容营销创作"]
    assert row["label_review"] == "multi_tag_review"


def test_r12_prewrite_plan_merges_duplicate_community_candidates() -> None:
    payload = build_r12_prewrite_plan(
        {
            "rows": [
                _feedback_row(
                    community="r/eBaySellerAdvice",
                    source_scope="ecommerce-sellers",
                    suggested_user_tags=["卖家店铺运营"],
                    topic_cluster="seller-category-direction",
                ),
                _feedback_row(
                    community="r/ebayselleradvice",
                    source_scope="ecommerce-sellers",
                    suggested_user_tags=["电商平台政策与风向", "卖家店铺运营"],
                    topic_cluster="unit-economics-and-platform-risk",
                    value_assessment={"score": 100, "stage": "pool_candidate"},
                ),
            ]
        },
        active_pool_keys=set(),
        deleted_pool_keys=set(),
    )

    assert payload["summary"] == {
        "input_rows": 2,
        "candidate_rows": 1,
        "would_insert": 1,
        "skipped_existing": 0,
        "blocked": 0,
    }
    row = payload["rows"][0]
    assert row["community"] == "r/ebayselleradvice"
    assert row["suggested_user_tags"] == ["卖家店铺运营", "电商平台政策与风向"]
    assert row["label_review"] == "multi_tag_review"
    assert (
        row["topic_cluster"]
        == "seller-category-direction,unit-economics-and-platform-risk"
    )
    assert row["write_preview"]["pool_insert"]["description_keywords"][
        "suggested_user_tags"
    ] == [
        "卖家店铺运营",
        "电商平台政策与风向",
    ]


def test_r12_prewrite_service_does_not_hardcode_tag_or_community_names() -> None:
    source = SERVICE_SOURCE.read_text(encoding="utf-8")
    catalog = load_interest_tag_catalog()

    assert not any(tag.display_name in source for tag in catalog.tags)
    assert "AEO" not in source
    assert "AI_UGC_Marketing" not in source
    assert "GrowthHacking" not in source
