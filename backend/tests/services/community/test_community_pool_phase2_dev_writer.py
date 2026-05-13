from __future__ import annotations

from app.services.community.community_pool_phase2_dev_writer import (
    build_pool_insert_rows,
    build_write_plan,
    normalize_key,
    render_rollback_sql,
)
from app.services.community.business_category_config import phase2_category_for


def _phase1_payload() -> dict[str, object]:
    return {
        "phase": "community-pool-phase1-dry-run",
        "rows": [
            {
                "community": "r/OpenAI",
                "phase1_action": "propose_pool_addition",
                "role": "generic_hotspot",
                "cap_required": True,
                "hot_floor": {
                    "must_cover_platform_hot_signal": True,
                    "allowed_cap_bypass_reason": "must_have_hot_signal",
                },
                "evidence": {
                    "hotpost_card_count": 30,
                    "promotion_band": "strong",
                    "supply_scopes": ["ai-automation"],
                    "example_titles": ["OpenAI sample"],
                },
                "write_preview": {"would_insert_pool": True},
            },
            {
                "community": "r/CampingGear",
                "phase1_action": "propose_pool_addition",
                "role": "longtail_vertical",
                "cap_required": False,
                "hot_floor": {"must_cover_platform_hot_signal": False},
                "evidence": {
                    "hotpost_card_count": 6,
                    "promotion_band": "strong",
                    "supply_scopes": ["ecommerce-sellers"],
                    "example_titles": ["Camping sample"],
                },
                "write_preview": {"would_insert_pool": True},
            },
            {
                "community": "r/BuyItForLife",
                "phase1_action": "keep_pool_unchanged",
                "role": "longtail_vertical",
                "cap_required": False,
                "evidence": {"hotpost_card_count": 51},
                "write_preview": {"would_insert_pool": False},
            },
        ],
    }


def test_build_pool_insert_rows_only_uses_phase1_additions() -> None:
    rows = build_pool_insert_rows(_phase1_payload())

    assert [row.name for row in rows] == ["r/openai", "r/campinggear"]
    assert rows[0].tier == "seed"
    assert rows[0].priority == "medium"
    assert rows[0].categories == [
        phase2_category_for(
            key=normalize_key(rows[0].name),
            role="generic_hotspot",
            scopes=["ai-automation"],
        )
    ]
    assert rows[0].description_keywords["source"] == "community_pool_phase2_dev_write"
    assert rows[0].description_keywords["display_name"] == "r/OpenAI"
    assert rows[0].description_keywords["cap_required"] is True
    assert rows[0].description_keywords["hot_floor"]["allowed_cap_bypass_reason"] == (
        "must_have_hot_signal"
    )
    assert rows[1].categories == [
        phase2_category_for(
            key=normalize_key(rows[1].name),
            role="longtail_vertical",
            scopes=["ecommerce-sellers"],
        )
    ]


def test_build_write_plan_skips_existing_and_blocks_deleted_conflicts() -> None:
    rows = build_pool_insert_rows(_phase1_payload())

    plan = build_write_plan(
        rows,
        active_existing={"r/openai"},
        deleted_existing={"r/campinggear"},
    )

    assert plan.insert_rows == []
    assert plan.skipped_existing == ["r/openai"]
    assert plan.blocked_deleted_conflicts == ["r/campinggear"]
    assert plan.summary == {
        "input_rows": 2,
        "would_insert": 0,
        "skipped_existing": 1,
        "blocked_deleted_conflicts": 1,
    }


def test_render_rollback_sql_only_targets_inserted_phase2_rows() -> None:
    sql = render_rollback_sql(["r/openai", "r/campinggear"])

    assert "DELETE FROM community_category_map" in sql
    assert "DELETE FROM community_pool" in sql
    assert "'r/openai'" in sql
    assert "'r/campinggear'" in sql
    assert "description_keywords->>'source' = 'community_pool_phase2_dev_write'" in sql
