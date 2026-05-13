from __future__ import annotations

from app.services.community.community_pool_phase1_planner import build_phase1_plan


def test_phase1_routes_existing_evidence_without_db_write() -> None:
    payload = {
        "counts": {
            "promote_candidate": 1,
            "keep_active": 1,
            "needs_evidence": 1,
            "stale_review": 1,
            "observation_queue": 1,
        },
        "states": {
            "promote_candidate": [
                {
                    "community": "r/PPC",
                    "evidence": {
                        "hotpost_card_count": 37,
                        "in_pool": False,
                        "in_supply": True,
                        "discovered_status": None,
                        "supply_scopes": ["business-growth-ops"],
                        "example_titles": ["PPC sample"],
                    },
                }
            ],
            "keep_active": [
                {
                    "community": "r/BuyItForLife",
                    "evidence": {
                        "hotpost_card_count": 51,
                        "in_pool": True,
                        "in_supply": True,
                        "discovered_status": None,
                        "supply_scopes": ["ecommerce-sellers"],
                        "example_titles": ["BIFL sample"],
                    },
                }
            ],
            "needs_evidence": [{"community": "r/mcp", "evidence": {}}],
            "stale_review": [{"community": "r/airfryer", "evidence": {}}],
            "observation_queue": [{"community": "r/VacuumCleaners", "evidence": {}}],
        },
    }

    plan = build_phase1_plan(payload)

    assert plan["summary"]["proposed_pool_additions"] == 1
    assert plan["summary"]["keep_pool_unchanged"] == 1
    assert plan["summary"]["review_only"]["needs_evidence"] == 1
    assert plan["summary"]["review_only"]["stale_review"] == 1
    assert plan["summary"]["review_only"]["observation_queue"] == 1
    assert plan["writes_allowed"] is False
    assert plan["future_write_preview"] == {
        "writes_allowed_in_phase1": False,
        "would_insert_pool_rows": 1,
        "would_update_pool_rows": 0,
        "fields_requiring_future_approval": [
            "community",
            "source_state",
            "role",
            "cap_required",
            "suggested_usage_policy",
            "required_evidence_fields",
            "evidence_snapshot",
        ],
    }


def test_generic_community_requires_cap_policy() -> None:
    payload = {
        "counts": {},
        "states": {
            "promote_candidate": [
                {
                    "community": "r/OpenAI",
                    "evidence": {
                        "hotpost_card_count": 30,
                        "in_pool": False,
                        "in_supply": True,
                        "discovered_status": "pending",
                        "supply_scopes": ["ai-automation"],
                        "example_titles": ["OpenAI sample"],
                    },
                }
            ],
            "keep_active": [],
            "needs_evidence": [],
            "stale_review": [],
            "observation_queue": [],
        },
    }

    plan = build_phase1_plan(payload)
    row = plan["rows"][0]

    assert row["community"] == "r/OpenAI"
    assert row["phase1_action"] == "propose_pool_addition"
    assert row["role"] == "generic_hotspot"
    assert row["cap_required"] is True
    assert row["suggested_usage_policy"]["mode"] == "capped_learning"
    assert row["suggested_usage_policy"]["regular_learning_cap_ratio"] == 0.25
    assert row["suggested_usage_policy"]["max_cap_ratio_without_human_review"] == 0.3
    assert row["hot_floor"] == {
        "must_cover_platform_hot_signal": True,
        "bypasses_regular_cap": True,
        "cap_bypass_reason_required": True,
        "allowed_cap_bypass_reason": "must_have_hot_signal",
        "scope": "hot_signal_coverage_only",
    }


def test_longtail_community_gets_evidence_fields() -> None:
    payload = {
        "counts": {},
        "states": {
            "promote_candidate": [
                {
                    "community": "r/AsianBeauty",
                    "evidence": {
                        "hotpost_card_count": 5,
                        "in_pool": False,
                        "in_supply": False,
                        "discovered_status": None,
                        "supply_scopes": [],
                        "example_titles": ["AsianBeauty sample"],
                    },
                }
            ],
            "keep_active": [],
            "needs_evidence": [],
            "stale_review": [],
            "observation_queue": [],
        },
    }

    plan = build_phase1_plan(payload)
    row = plan["rows"][0]

    assert row["role"] == "longtail_vertical"
    assert row["cap_required"] is False
    assert row["required_evidence_fields"] == [
        "activity",
        "post_quality",
        "vertical_density",
        "learnability",
    ]


def test_phase1_summary_includes_generic_cap_and_hot_floor_policy() -> None:
    payload = {
        "counts": {},
        "states": {
            "promote_candidate": [
                {
                    "community": "r/OpenAI",
                    "evidence": {"hotpost_card_count": 30},
                },
                {
                    "community": "r/AsianBeauty",
                    "evidence": {"hotpost_card_count": 5},
                },
            ],
            "keep_active": [],
            "needs_evidence": [],
            "stale_review": [],
            "observation_queue": [],
        },
    }

    plan = build_phase1_plan(payload)

    assert plan["summary"]["generic_cap_policy"] == {
        "regular_learning_cap_ratio": 0.25,
        "max_cap_ratio_without_human_review": 0.3,
        "current_generic_ratio": 0.5,
        "hot_floor_enabled": True,
        "hot_floor_bypasses_regular_cap": True,
        "allowed_cap_bypass_reason": "must_have_hot_signal",
    }
