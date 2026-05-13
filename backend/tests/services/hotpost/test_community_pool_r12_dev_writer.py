from __future__ import annotations

from pathlib import Path

from app.services.community.community_pool_phase2_dev_writer import build_write_plan
from app.services.community.interest_tag_catalog import load_interest_tag_catalog
from app.services.hotpost.community_pool_r12_dev_writer import (
    R12_WRITE_SOURCE,
    build_r12_existing_name_sets,
    build_r12_insert_rows,
    render_r12_rollback_sql,
)


SERVICE_SOURCE = (
    Path(__file__).resolve().parents[3]
    / "app"
    / "services"
    / "hotpost"
    / "community_pool_r12_dev_writer.py"
)


def _prewrite_payload() -> dict[str, object]:
    return {
        "schema_version": "hotpost-community-pool-r12-prewrite/v1",
        "rows": [
            {
                "community": "r/TestGrowth",
                "source_scope": "business-growth-ops",
                "topic_cluster": "funnel",
                "suggested_user_tags": ["广告投放", "内容营销创作"],
                "label_review": "multi_tag_review",
                "evidence": {
                    "candidate_count": 2,
                    "published_count": 2,
                    "duplicate_count": 0,
                    "total_evidence": 4,
                },
                "value_assessment": {"score": 91, "stage": "pool_candidate"},
                "write_preview": {
                    "action": "prepare_dev_write",
                    "would_insert_pool": True,
                    "pool_insert": {
                        "name": "r/testgrowth",
                        "tier": "seed",
                        "categories": ["Ecommerce_Business"],
                        "priority": "medium",
                    },
                },
            },
            {
                "community": "r/SkipMe",
                "write_preview": {"action": "skip_existing", "would_insert_pool": False},
            },
        ],
    }


def test_build_r12_insert_rows_uses_only_prewrite_insert_rows() -> None:
    rows = build_r12_insert_rows(_prewrite_payload())

    assert [row.name for row in rows] == ["r/testgrowth"]
    assert rows[0].tier == "seed"
    assert rows[0].priority == "medium"
    assert rows[0].categories == ["Ecommerce_Business"]
    assert rows[0].description_keywords["source"] == R12_WRITE_SOURCE
    assert rows[0].description_keywords["prewrite_source"] == "hotpost_community_pool_r12_prewrite"
    assert rows[0].description_keywords["suggested_user_tags"] == ["广告投放", "内容营销创作"]


def test_build_write_plan_rechecks_existing_before_write() -> None:
    rows = build_r12_insert_rows(_prewrite_payload())
    plan = build_write_plan(rows, active_existing={"r/testgrowth"}, deleted_existing=set())

    assert plan.insert_rows == []
    assert plan.skipped_existing == ["r/testgrowth"]


def test_existing_name_sets_canonicalize_database_name_keys() -> None:
    active_existing, deleted_existing = build_r12_existing_name_sets(
        [
            ("TestGrowth", None),
            ("OldGrowth", object()),
        ]
    )
    rows = build_r12_insert_rows(_prewrite_payload())
    plan = build_write_plan(rows, active_existing=active_existing, deleted_existing=deleted_existing)

    assert active_existing == {"r/testgrowth"}
    assert deleted_existing == {"r/oldgrowth"}
    assert plan.insert_rows == []
    assert plan.skipped_existing == ["r/testgrowth"]


def test_render_r12_rollback_sql_targets_only_r12_source() -> None:
    sql = render_r12_rollback_sql(["r/testgrowth"])

    assert "DELETE FROM community_category_map" in sql
    assert "DELETE FROM community_pool" in sql
    assert "'r/testgrowth'" in sql
    assert f"description_keywords->>'source' = '{R12_WRITE_SOURCE}'" in sql


def test_r12_dev_writer_does_not_hardcode_tag_or_community_names() -> None:
    source = SERVICE_SOURCE.read_text(encoding="utf-8")
    catalog = load_interest_tag_catalog()

    assert not any(tag.display_name in source for tag in catalog.tags)
    assert "AEO" not in source
    assert "AI_UGC_Marketing" not in source
    assert "GrowthHacking" not in source
