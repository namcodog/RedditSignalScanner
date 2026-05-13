from __future__ import annotations

from scripts.community.community_pool_phase1_dry_run import render_markdown


def test_render_markdown_states_no_db_writes() -> None:
    payload = {
        "summary": {
            "existing_evidence_communities": 2,
            "proposed_pool_additions": 1,
            "keep_pool_unchanged": 1,
            "generic_cap_required": 1,
            "generic_cap_policy": {
                "regular_learning_cap_ratio": 0.25,
                "max_cap_ratio_without_human_review": 0.3,
                "current_generic_ratio": 0.5,
                "hot_floor_enabled": True,
                "hot_floor_bypasses_regular_cap": True,
                "allowed_cap_bypass_reason": "must_have_hot_signal",
            },
            "review_only": {
                "needs_evidence": 31,
                "stale_review": 115,
                "observation_queue": 10,
            },
        },
        "rows": [
            {
                "community": "r/OpenAI",
                "source_state": "promote_candidate",
                "phase1_action": "propose_pool_addition",
                "role": "generic_hotspot",
                "cap_required": True,
                "suggested_usage_policy": {"mode": "capped_learning"},
                "write_preview": {
                    "would_insert_pool": True,
                    "would_update_pool": False,
                    "writes_allowed_in_phase1": False,
                },
                "hot_floor": {
                    "must_cover_platform_hot_signal": True,
                    "bypasses_regular_cap": True,
                    "cap_bypass_reason_required": True,
                    "allowed_cap_bypass_reason": "must_have_hot_signal",
                    "scope": "hot_signal_coverage_only",
                },
                "evidence": {"hotpost_card_count": 30},
            }
        ],
        "future_write_preview": {
            "writes_allowed_in_phase1": False,
            "would_insert_pool_rows": 1,
            "would_update_pool_rows": 0,
            "fields_requiring_future_approval": ["community", "role"],
        },
    }

    markdown = render_markdown(payload)

    assert "Phase 1 Community Pool Dry-Run" in markdown
    assert "DB writes: `false`" in markdown
    assert (
        "| r/OpenAI | promote_candidate | propose_pool_addition | generic_hotspot | Y |"
        in markdown
    )
    assert "needs_evidence=31 / stale_review=115 / observation_queue=10" in markdown
    assert "regular_learning_cap_ratio: `25%`" in markdown
    assert "hot_floor: `enabled`" in markdown
    assert "allowed_cap_bypass_reason: `must_have_hot_signal`" in markdown
    assert "must-have hot signals bypass the regular generic cap" in markdown
    assert "would_insert_pool_rows: `1`" in markdown
    assert "fields_requiring_future_approval: `community, role`" in markdown
