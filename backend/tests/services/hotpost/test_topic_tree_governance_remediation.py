from __future__ import annotations


def test_rebalance_publish_list_swaps_rotation_flagged_item_when_it_improves() -> None:
    from app.services.hotpost.topic_tree_governance_remediation import rebalance_publish_list_for_governance

    class _Planner:
        def build_audit(self, *, plan_items, candidate_items):
            del candidate_items
            flagged = [
                {"item_id": item["plan_key"], "title": item["title"]}
                for item in plan_items
                if item["plan_key"] == "candidate:fatigue"
            ]
            overall = "rewrite" if flagged else "publish"
            return {
                "overall_decision": overall,
                "allocation": {"decision": "publish", "missing_pack_ids": []},
                "rotation": {"decision": overall, "flagged_items": flagged},
                "supply": {"decision": "publish", "missing_supply_packs": []},
                "source_health": {"decision": "publish", "risky_pack_ids": []},
            }

    publish_list = [
        {
            "plan_key": "candidate:stable",
            "title": "Fresh non-fatigued item",
            "source_scope_id": "business-growth-ops",
            "topic_pack_id": "organic-discovery",
        },
        {
            "plan_key": "candidate:fatigue",
            "title": "Fatigued PPC item",
            "source_scope_id": "business-growth-ops",
            "topic_pack_id": "paid-economics",
        },
    ]
    candidate_rows = [
        *publish_list,
        {
            "plan_key": "candidate:replacement",
            "title": "Fresh replacement item",
            "source_scope_id": "business-growth-ops",
            "topic_pack_id": "funnel-conversion",
        },
    ]

    updated = rebalance_publish_list_for_governance(
        publish_list=publish_list,
        planner_map={"business-growth-ops": _Planner()},
        candidate_rows=candidate_rows,
    )

    assert [item["plan_key"] for item in updated] == ["candidate:stable", "candidate:replacement"]


def test_build_governance_topic_watches_targets_new_sources_for_risky_pack() -> None:
    from app.services.hotpost.topic_tree_governance_remediation import build_governance_topic_watches

    plan_payload = {
        "publish_list": [
            {
                "plan_key": "candidate:funnel-1",
                "source_scope_id": "business-growth-ops",
                "topic_pack_id": "funnel-conversion",
                "topic_cluster_id": "funnel",
                "topic_cluster_ids": ["funnel"],
                "matched_subreddit": "shopify",
                "source_communities": ["r/shopify"],
            }
        ]
    }
    gate_summary = {
        "topic_tree_governance": {
            "scopes": {
                "business-growth-ops": {
                    "overall_decision": "rewrite",
                    "rotation": {"flagged_items": []},
                    "source_health": {"risky_pack_ids": ["funnel-conversion"]},
                }
            }
        }
    }

    watches = build_governance_topic_watches(
        plan_payload=plan_payload,
        gate_summary=gate_summary,
        scope_id="business-growth-ops",
    )

    assert len(watches) == 1
    watch = watches[0]
    assert watch.topic_pack_id == "funnel-conversion"
    assert "shopify" not in [item.lower() for item in watch.subreddits]
    assert watch.subreddits
    assert watch.time_filter == "week"
    assert watch.candidate_cap == 6
    assert watch.topic_cluster_ids == ("funnel",)


def test_build_governance_topic_watches_prefers_fresh_relief_for_rotation() -> None:
    from app.services.hotpost.topic_tree_governance_remediation import build_governance_topic_watches

    plan_payload = {
        "publish_list": [
            {
                "plan_key": "candidate:paid-1",
                "source_scope_id": "business-growth-ops",
                "topic_pack_id": "paid-economics",
                "topic_cluster_id": "ads",
                "topic_cluster_ids": ["ads"],
                "matched_subreddit": "PPC",
                "source_communities": ["r/PPC"],
            }
        ]
    }
    gate_summary = {
        "topic_tree_governance": {
            "scopes": {
                "business-growth-ops": {
                    "overall_decision": "rewrite",
                    "rotation": {
                        "flagged_items": [
                            {
                                "item_id": "candidate:paid-1",
                                "title": "Fatigued paid angle",
                            }
                        ]
                    },
                    "source_health": {"risky_pack_ids": []},
                }
            }
        }
    }

    watches = build_governance_topic_watches(
        plan_payload=plan_payload,
        gate_summary=gate_summary,
        scope_id="business-growth-ops",
    )

    assert len(watches) == 1
    watch = watches[0]
    assert watch.topic_pack_id == "paid-economics"
    assert watch.time_filter == "day"
    assert watch.candidate_cap == 1
    assert watch.topic_cluster_ids == ()
    assert "ppc" not in [item.lower() for item in watch.subreddits]


def test_rebalance_publish_list_swaps_overweight_scope_pack_item_for_visible_balance() -> None:
    from app.services.hotpost.topic_tree_governance_remediation import rebalance_publish_list_for_governance

    class _Planner:
        def build_audit(self, *, plan_items, candidate_items):
            del plan_items, candidate_items
            return {
                "overall_decision": "publish",
                "allocation": {"decision": "publish", "missing_pack_ids": []},
                "rotation": {"decision": "publish", "flagged_items": []},
                "supply": {"decision": "publish", "missing_supply_packs": []},
                "source_health": {"decision": "publish", "risky_pack_ids": []},
            }

    publish_list = [
        {
            "plan_key": "candidate:growth-1",
            "title": "Growth paid 1",
            "lane": "signal",
            "source_scope_id": "business-growth-ops",
            "topic_pack_id": "paid-economics",
            "top_community": "r/FacebookAds",
        },
        {
            "plan_key": "candidate:growth-2",
            "title": "Growth paid 2",
            "lane": "signal",
            "source_scope_id": "business-growth-ops",
            "topic_pack_id": "paid-economics",
            "top_community": "r/FacebookAds",
        },
        {
            "plan_key": "candidate:growth-3",
            "title": "Growth paid 3",
            "lane": "signal",
            "source_scope_id": "business-growth-ops",
            "topic_pack_id": "paid-economics",
            "top_community": "r/PPC",
        },
    ]
    candidate_rows = [
        *publish_list,
        {
            "plan_key": "candidate:ai-1",
            "title": "AI upstream",
            "lane": "signal",
            "source_scope_id": "ai-automation",
            "topic_pack_id": "upstream-winds",
            "topic_cluster_id": "model-platform-shifts",
            "top_community": "r/OpenAI",
        },
    ]

    updated = rebalance_publish_list_for_governance(
        publish_list=publish_list,
        planner_map={
            "business-growth-ops": _Planner(),
            "ai-automation": _Planner(),
        },
        candidate_rows=candidate_rows,
    )

    keys = [item["plan_key"] for item in updated]
    assert "candidate:ai-1" in keys
    assert keys.count("candidate:growth-1") + keys.count("candidate:growth-2") + keys.count("candidate:growth-3") == 2
