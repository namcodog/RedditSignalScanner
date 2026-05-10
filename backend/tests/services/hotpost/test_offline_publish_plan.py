from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json


def _candidate(candidate_id: str, *, lane_hint: str, scope: str, pack: str, title: str) -> dict:
    query = "pricing update" if lane_hint == "hot" else "switching tool because context loss"
    return {
        "candidate_id": candidate_id,
        "signal_id": f"sig-{candidate_id}",
        "source_scope_id": scope,
        "source_scope_name": scope,
        "topic_pack_id": pack,
        "topic_cluster_id": "platform-policy-shifts" if pack == "upstream-winds" else "agent-incidents",
        "topic_cluster_ids": ["platform-policy-shifts"] if pack == "upstream-winds" else ["agent-incidents"],
        "named_topic_ids": [],
        "query": query,
        "matched_subreddit": "OpenAI",
        "post_id": f"post-{candidate_id}",
        "title": title,
        "score": 600 if lane_hint == "hot" else 120,
        "num_comments": 90 if lane_hint == "hot" else 25,
        "created_at": datetime.now(timezone.utc),
        "collected_at": datetime.now(timezone.utc),
        "collect_batch_id": "batch-1",
        "time_window": "24h",
        "signal_level": "hot" if lane_hint == "hot" else "rising",
        "why_now_reason": "new_threads_24h",
        "listing_source": "listing:hot:day",
        "primary_reason": f"{pack}:listing_hot",
        "matched_keywords": ["pricing update"] if lane_hint == "hot" else ["context loss"],
        "top_communities": ["r/OpenAI"],
        "thread_count": 1,
        "community_count": 1,
        "quote_count": 2,
        "intent_tags": ["趋势变化"],
        "evidence_quotes": [
            {
                "text": "Everyone in this thread unsubscribed after the pricing update rolled out.",
                "community": "r/OpenAI",
                "permalink": "https://www.reddit.com/r/OpenAI/comments/post-1/q1",
            },
            {
                "text": "We all switched tools after the rollout and several teams canceled their plans.",
                "community": "r/OpenAI",
                "permalink": "https://www.reddit.com/r/OpenAI/comments/post-1/q2",
            },
        ],
    }


def test_offline_publish_plan_returns_local_json_shape(monkeypatch) -> None:
    from app.schemas.hotpost_card_candidates import CandidatePack
    from app.schemas.hotpost_card_drafts import WritingCardDraft
    from app.services.hotpost.offline_publish_plan import build_offline_publish_plan

    candidates = [
        CandidatePack.model_validate(_candidate("cand-ai-hot-1", lane_hint="hot", scope="ai-automation", pack="upstream-winds", title="OpenAI pricing thread exploded")),
        CandidatePack.model_validate(_candidate("cand-ai-signal-1", lane_hint="signal", scope="ai-automation", pack="agent-builder", title="Teams are replacing agent steps with simpler workflows")),
    ]

    write_draft = WritingCardDraft.model_validate(
        {
            "draft_id": "draft-group-ai-1",
            "candidate_id": "group-ai-1",
            "candidate_ids": ["cand-ai-hot-1", "cand-ai-signal-1"],
            "card_id": "card-group-ai-1",
            "signal_id": "sig-group-ai-1",
            "topic_pack_id": "upstream-winds",
            "topic_cluster_id": "platform-policy-shifts",
            "topic_cluster_ids": ["platform-policy-shifts"],
            "named_topic_ids": [],
            "card_type": "write",
            "lane": "breakdown",
            "category_id": "write",
            "title": "Breakdown draft",
            "source_scope_id": "ai-automation",
            "source_scope_name": "AI",
            "matched_subreddit": "OpenAI",
            "post_id": "post-group-ai-1",
            "source_event_at": datetime.now(timezone.utc),
            "score": 500,
            "num_comments": 80,
            "time_window": "24h",
            "signal_level": "hot",
            "why_now_reason": "new_threads_24h",
            "thread_count": 2,
            "community_count": 2,
            "quote_count": 2,
            "intent_tags": ["趋势变化"],
            "evidence_quotes": [
                {
                    "text": "First strong quote from one thread.",
                    "community": "r/OpenAI",
                    "permalink": "https://www.reddit.com/r/OpenAI/comments/post-group-ai-1/q1",
                },
                {
                    "text": "Second strong quote from another thread.",
                    "community": "r/ClaudeAI",
                    "permalink": "https://www.reddit.com/r/ClaudeAI/comments/post-group-ai-1/q2",
                },
            ],
            "summary_line": "Two threads now point at the same shift.",
            "audience": "关注模型路线的人",
            "why_now": "放在一起看，判断升级了。",
            "source_link": "https://www.reddit.com/r/OpenAI/comments/post-group-ai-1",
            "source_links": ["https://www.reddit.com/r/OpenAI/comments/post-group-ai-1"],
            "source_communities": ["r/OpenAI", "r/ClaudeAI"],
            "draft_status": "draft",
            "draft_note": "ready",
            "detail": {
                "thesis": "Teams are changing how they evaluate model releases.",
                "writing_angle_or_perspective": "The decision rule changed, not just the tool list.",
                "tension_point_or_why_it_matters": "The trade-off is shifting toward reliability over hype.",
                "title_hooks": ["hook-1"],
                "quote_pack": ["quote-1", "quote-2"],
            },
        }
    )

    monkeypatch.setattr("app.services.hotpost.offline_publish_plan.load_published_cards", lambda: [])
    monkeypatch.setattr(
        "app.services.hotpost.offline_publish_plan.list_candidates",
        lambda source_scope_id=None: [item for item in candidates if source_scope_id is None or item.source_scope_id == source_scope_id],
    )
    monkeypatch.setattr(
        "app.services.hotpost.offline_publish_plan.list_drafts",
        lambda source_scope_id=None: [draft for draft in [write_draft] if source_scope_id is None or draft.source_scope_id == source_scope_id],
    )
    monkeypatch.setattr("app.services.hotpost.offline_publish_plan.list_breakdown_suggestions", lambda source_scope_id=None, limit=30: [])

    payload = build_offline_publish_plan(limit=3, scope="ai-automation")

    assert payload["targets"]["total"] == 3
    assert payload["publish_list"]
    assert any(item["lane"] == "breakdown" for item in payload["publish_list"])
    assert any(item["source_type"] == "draft" for item in payload["publish_list"])
    assert all("topic_pack_id" in item for item in payload["publish_list"])
    assert all("topic_cluster_ids" in item for item in payload["publish_list"])
    assert payload["topic_tree_governance"]["overall_decision"] in {"publish", "rewrite"}
    assert payload["publish_contract_summary"]["version"] == "unified-contract-v1"
    assert payload["publish_contract_summary"]["achieved"]["rules_layer_established"] is True


def test_offline_publish_plan_includes_contract_summary_with_trend_status(monkeypatch, tmp_path: Path) -> None:
    from app.schemas.hotpost_card_candidates import CandidatePack
    from app.services.hotpost.offline_publish_plan import build_offline_publish_plan
    import app.services.hotpost.publish_contract_summary as summary_mod

    trend_path = tmp_path / "mini-release-trend-audit-latest.json"
    trend_path.write_text(
        json.dumps(
            {
                "latest_release_id": "release-demo",
                "latest_status": "stable",
                "stable_streak": 6,
                "remaining_new_releases": 0,
                "release_summaries": [
                    {
                        "front30": {"alerts": []},
                        "full": {
                            "alerts": [],
                            "watched_communities": {
                                "r/FacebookAds": 5,
                                "r/PPC": 5,
                                "r/BuyItForLife": 5,
                            },
                            "watched_packs": {"paid-economics": 14},
                        },
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(summary_mod, "TREND_AUDIT_PATH", trend_path)

    candidates = [
        CandidatePack.model_validate(
            _candidate(
                "cand-upstream",
                lane_hint="signal",
                scope="ai-automation",
                pack="upstream-winds",
                title="Model route changes again",
            )
        ),
        CandidatePack.model_validate(
            _candidate(
                "cand-tools",
                lane_hint="signal",
                scope="ai-automation",
                pack="tools-efficiency",
                title="Teams replace bloated workflows",
            )
        ),
    ]

    monkeypatch.setattr("app.services.hotpost.offline_publish_plan.load_published_cards", lambda: [])
    monkeypatch.setattr("app.services.hotpost.offline_publish_plan.list_candidates", lambda source_scope_id=None: candidates)
    monkeypatch.setattr("app.services.hotpost.offline_publish_plan.list_drafts", lambda source_scope_id=None: [])
    monkeypatch.setattr("app.services.hotpost.offline_publish_plan.list_breakdown_suggestions", lambda source_scope_id=None, limit=30: [])

    payload = build_offline_publish_plan(limit=3)

    summary = payload["publish_contract_summary"]
    assert summary["achieved"]["visible_layer_improved"] is True
    assert summary["current_metrics"]["latest_trend_status"]["latest_status"] == "stable"
    assert "key-people-and-route" in summary["not_yet_reached"]["blank_priority_clusters"]
    assert "funnel-conversion" in summary["priority_next_steps"]["thin_packs_first"]


def test_resolve_lane_targets_scales_to_window_contract() -> None:
    from app.services.hotpost.offline_publish_plan import _resolve_lane_targets

    configured = {"signal": 18, "hot": 8, "breakdown": 5}

    assert _resolve_lane_targets(30, configured) == {"signal": 17, "hot": 8, "breakdown": 5}
    assert _resolve_lane_targets(15, configured) == {"signal": 9, "hot": 4, "breakdown": 2}
    assert _resolve_lane_targets(10, configured) == {"signal": 5, "hot": 3, "breakdown": 2}


def test_offline_publish_plan_blank_priority_clusters_respects_topic_cluster_ids(monkeypatch) -> None:
    from app.schemas.hotpost_card_candidates import CandidatePack
    from app.services.hotpost.offline_publish_plan import build_offline_publish_plan

    payload = _candidate(
        "cand-ai-signal-merged",
        lane_hint="signal",
        scope="ai-automation",
        pack="upstream-winds",
        title="Merged route + pricing signal",
    )
    payload["topic_cluster_id"] = "key-people-and-route"
    payload["topic_cluster_ids"] = ["key-people-and-route", "platform-policy-shifts"]
    candidates = [CandidatePack.model_validate(payload)]

    monkeypatch.setattr("app.services.hotpost.offline_publish_plan.load_published_cards", lambda: [])
    monkeypatch.setattr("app.services.hotpost.offline_publish_plan.list_candidates", lambda source_scope_id=None: candidates)
    monkeypatch.setattr("app.services.hotpost.offline_publish_plan.list_drafts", lambda source_scope_id=None: [])
    monkeypatch.setattr("app.services.hotpost.offline_publish_plan.list_breakdown_suggestions", lambda source_scope_id=None, limit=30: [])

    summary = build_offline_publish_plan(limit=3)["publish_contract_summary"]

    assert "platform-policy-shifts" not in summary["not_yet_reached"]["blank_priority_clusters"]


def test_offline_publish_plan_caps_single_named_topic(monkeypatch) -> None:
    from app.schemas.hotpost_card_candidates import CandidatePack
    from app.services.hotpost.offline_publish_plan import build_offline_publish_plan

    def _with_named_topic(candidate_id: str, *, topic_id: str, score: int) -> CandidatePack:
        payload = _candidate(
            candidate_id,
            lane_hint="signal",
            scope="business-growth-ops",
            pack="funnel-conversion",
            title=f"Checkout thread {candidate_id}",
        )
        payload["named_topic_ids"] = [topic_id]
        payload["score"] = score
        payload["num_comments"] = 18
        return CandidatePack.model_validate(payload)

    candidates = [
        _with_named_topic("cand-1", topic_id="checkout-conversion", score=180),
        _with_named_topic("cand-2", topic_id="checkout-conversion", score=175),
        _with_named_topic("cand-3", topic_id="category-demand-shift", score=170),
    ]

    monkeypatch.setattr("app.services.hotpost.offline_publish_plan.load_published_cards", lambda: [])
    monkeypatch.setattr(
        "app.services.hotpost.offline_publish_plan.list_candidates",
        lambda source_scope_id=None: [item for item in candidates if source_scope_id is None or item.source_scope_id == source_scope_id],
    )
    monkeypatch.setattr("app.services.hotpost.offline_publish_plan.list_drafts", lambda source_scope_id=None: [])
    monkeypatch.setattr("app.services.hotpost.offline_publish_plan.list_breakdown_suggestions", lambda source_scope_id=None, limit=30: [])

    payload = build_offline_publish_plan(limit=3, scope="business-growth-ops")
    named_topic_rows = [item for item in payload["publish_list"] if item.get("named_topic_ids")]

    assert len(named_topic_rows) == 2
    assert [item["named_topic_ids"][0] for item in named_topic_rows].count("checkout-conversion") == 1


def test_offline_publish_plan_does_not_force_same_named_topic_to_fill_lane(monkeypatch) -> None:
    from app.schemas.hotpost_card_candidates import CandidatePack
    from app.services.hotpost.offline_publish_plan import build_offline_publish_plan

    def _with_named_topic(candidate_id: str, *, score: int) -> CandidatePack:
        payload = _candidate(
            candidate_id,
            lane_hint="signal",
            scope="business-growth-ops",
            pack="funnel-conversion",
            title=f"Same topic thread {candidate_id}",
        )
        payload["named_topic_ids"] = ["checkout-conversion"]
        payload["score"] = score
        payload["num_comments"] = 18
        return CandidatePack.model_validate(payload)

    candidates = [
        _with_named_topic("cand-1", score=180),
        _with_named_topic("cand-2", score=175),
        _with_named_topic("cand-3", score=170),
    ]

    monkeypatch.setattr("app.services.hotpost.offline_publish_plan.load_published_cards", lambda: [])
    monkeypatch.setattr(
        "app.services.hotpost.offline_publish_plan.list_candidates",
        lambda source_scope_id=None: [item for item in candidates if source_scope_id is None or item.source_scope_id == source_scope_id],
    )
    monkeypatch.setattr("app.services.hotpost.offline_publish_plan.list_drafts", lambda source_scope_id=None: [])
    monkeypatch.setattr("app.services.hotpost.offline_publish_plan.list_breakdown_suggestions", lambda source_scope_id=None, limit=30: [])

    payload = build_offline_publish_plan(limit=3, scope="business-growth-ops")
    named_topic_rows = [item for item in payload["publish_list"] if item.get("named_topic_ids")]

    assert len(named_topic_rows) == 1
    assert named_topic_rows[0]["named_topic_ids"] == ["checkout-conversion"]


def test_offline_publish_plan_keeps_governance_named_topics_out_of_publish_surface(monkeypatch) -> None:
    from app.schemas.hotpost_card_candidates import CandidatePack
    from app.services.hotpost.offline_publish_plan import build_offline_publish_plan

    regular = _candidate(
        "cand-regular",
        lane_hint="hot",
        scope="ai-automation",
        pack="upstream-winds",
        title="OpenAI pricing thread exploded",
    )
    governance = _candidate(
        "cand-governance",
        lane_hint="hot",
        scope="ai-automation",
        pack="upstream-winds",
        title="Off-topic governance probe",
    )
    governance["named_topic_ids"] = ["governance-upstream-winds-source_health"]

    candidates = [
        CandidatePack.model_validate(governance),
        CandidatePack.model_validate(regular),
    ]

    monkeypatch.setattr("app.services.hotpost.offline_publish_plan.load_published_cards", lambda: [])
    monkeypatch.setattr(
        "app.services.hotpost.offline_publish_plan.list_candidates",
        lambda source_scope_id=None: [item for item in candidates if source_scope_id is None or item.source_scope_id == source_scope_id],
    )
    monkeypatch.setattr("app.services.hotpost.offline_publish_plan.list_drafts", lambda source_scope_id=None: [])
    monkeypatch.setattr("app.services.hotpost.offline_publish_plan.list_breakdown_suggestions", lambda source_scope_id=None, limit=30: [])

    payload = build_offline_publish_plan(limit=1, scope="ai-automation")

    assert [item["candidate_id"] for item in payload["publish_list"]] == ["cand-regular"]


def test_offline_publish_plan_filters_weak_publish_surface_candidates_early(monkeypatch) -> None:
    from app.schemas.hotpost_card_candidates import CandidatePack
    from app.services.hotpost.offline_publish_plan import build_offline_publish_plan

    weak = _candidate(
        "cand-weak",
        lane_hint="signal",
        scope="business-growth-ops",
        pack="funnel-conversion",
        title="Need advice",
    )
    weak["quote_count"] = 1
    weak["evidence_quotes"] = [
        {
            "text": "ok",
            "community": "r/OpenAI",
            "permalink": "https://www.reddit.com/r/OpenAI/comments/post-weak/q1",
        }
    ]
    weak["thread_count"] = 1
    weak["community_count"] = 1

    strong = _candidate(
        "cand-strong",
        lane_hint="signal",
        scope="business-growth-ops",
        pack="funnel-conversion",
        title="Landing page change exposed a real checkout leak",
    )

    candidates = [
        CandidatePack.model_validate(weak),
        CandidatePack.model_validate(strong),
    ]

    monkeypatch.setattr("app.services.hotpost.offline_publish_plan.load_published_cards", lambda: [])
    monkeypatch.setattr(
        "app.services.hotpost.offline_publish_plan.list_candidates",
        lambda source_scope_id=None: [item for item in candidates if source_scope_id is None or item.source_scope_id == source_scope_id],
    )
    monkeypatch.setattr("app.services.hotpost.offline_publish_plan.list_drafts", lambda source_scope_id=None: [])
    monkeypatch.setattr("app.services.hotpost.offline_publish_plan.list_breakdown_suggestions", lambda source_scope_id=None, limit=30: [])

    payload = build_offline_publish_plan(limit=2, scope="business-growth-ops")

    assert [item["candidate_id"] for item in payload["publish_list"]] == ["cand-strong"]
    assert payload["inventory_summary"]["candidate_count"] == 2
    assert payload["inventory_summary"]["candidate_publish_surface_count"] == 1
    assert payload["inventory_summary"]["weak_candidate_count"] == 1


def test_offline_publish_plan_allows_exploration_tier_candidate_for_thin_pack(monkeypatch) -> None:
    from app.schemas.hotpost_card_candidates import CandidatePack
    from app.services.hotpost.offline_publish_plan import build_offline_publish_plan

    thin = _candidate(
        "cand-thin",
        lane_hint="signal",
        scope="business-growth-ops",
        pack="funnel-conversion",
        title="A single strong checkout thread now points at the same leak",
    )
    thin["quote_count"] = 2
    thin["thread_count"] = 1
    thin["community_count"] = 1

    strong = _candidate(
        "cand-strong-pack",
        lane_hint="signal",
        scope="business-growth-ops",
        pack="paid-economics",
        title="A single strong checkout thread now points at the same leak",
    )
    strong["quote_count"] = 2
    strong["thread_count"] = 1
    strong["community_count"] = 1

    candidates = [
        CandidatePack.model_validate(thin),
        CandidatePack.model_validate(strong),
    ]

    monkeypatch.setattr("app.services.hotpost.offline_publish_plan.load_published_cards", lambda: [])
    monkeypatch.setattr(
        "app.services.hotpost.offline_publish_plan.list_candidates",
        lambda source_scope_id=None: [item for item in candidates if source_scope_id is None or item.source_scope_id == source_scope_id],
    )
    monkeypatch.setattr("app.services.hotpost.offline_publish_plan.list_drafts", lambda source_scope_id=None: [])
    monkeypatch.setattr("app.services.hotpost.offline_publish_plan.list_breakdown_suggestions", lambda source_scope_id=None, limit=30: [])

    payload = build_offline_publish_plan(limit=2, scope="business-growth-ops")

    assert [item["candidate_id"] for item in payload["publish_list"]] == ["cand-thin"]
    assert payload["inventory_summary"]["candidate_publish_surface_count"] == 1
    assert payload["inventory_summary"]["weak_candidate_count"] == 1
    assert payload["publish_list"][0]["publish_surface_tier"] == "exploration"


def test_offline_publish_plan_does_not_reserve_candidate_for_incomplete_draft(monkeypatch) -> None:
    from app.schemas.hotpost_card_candidates import CandidatePack
    from app.services.hotpost.card_draft_builder import seed_validation_draft
    from app.services.hotpost.offline_publish_plan import build_offline_publish_plan

    candidate = CandidatePack.model_validate(
        _candidate(
            "cand-recoverable",
            lane_hint="signal",
            scope="business-growth-ops",
            pack="funnel-conversion",
            title="A strong checkout thread now points at the same leak",
        )
    )
    incomplete_draft = seed_validation_draft(candidate)

    monkeypatch.setattr("app.services.hotpost.offline_publish_plan.load_published_cards", lambda: [])
    monkeypatch.setattr(
        "app.services.hotpost.offline_publish_plan.list_candidates",
        lambda source_scope_id=None: [candidate],
    )
    monkeypatch.setattr(
        "app.services.hotpost.offline_publish_plan.list_drafts",
        lambda source_scope_id=None: [incomplete_draft],
    )
    monkeypatch.setattr("app.services.hotpost.offline_publish_plan.list_breakdown_suggestions", lambda source_scope_id=None, limit=30: [])

    payload = build_offline_publish_plan(limit=1, scope="business-growth-ops")

    assert [item["candidate_id"] for item in payload["publish_list"]] == ["cand-recoverable"]
    assert payload["inventory_summary"]["ready_validate_drafts"] == 0
    assert payload["inventory_summary"]["candidate_publish_surface_count"] == 1


def test_take_from_pool_prefers_distinct_breakdown_packs() -> None:
    from collections import Counter

    from app.services.hotpost.offline_publish_plan import _take_from_pool

    pool = [
        {
            "plan_key": "a",
            "lane": "breakdown",
            "title": "Selection A",
            "source_scope_id": "ecommerce-sellers",
            "topic_pack_id": "selection-signals",
            "score_hint": 100.0,
            "named_topic_ids": [],
        },
        {
            "plan_key": "b",
            "lane": "breakdown",
            "title": "Selection B",
            "source_scope_id": "ecommerce-sellers",
            "topic_pack_id": "selection-signals",
            "score_hint": 90.0,
            "named_topic_ids": [],
        },
        {
            "plan_key": "c",
            "lane": "breakdown",
            "title": "Organic",
            "source_scope_id": "business-growth-ops",
            "topic_pack_id": "organic-discovery",
            "score_hint": 80.0,
            "named_topic_ids": [],
        },
    ]

    selected = _take_from_pool(
        pool,
        need=2,
        target_total=12,
        lane_counts=Counter(),
        lane_targets={"breakdown": 2},
        named_topic_counts=Counter(),
        used_keys=set(),
        planner_map={},
    )

    assert {_item["topic_pack_id"] for _item in selected} == {"selection-signals", "organic-discovery"}


def test_take_from_pool_prefers_cross_scope_relief_when_growth_pack_is_overweight() -> None:
    from collections import Counter

    from app.services.hotpost.offline_publish_plan import _take_from_pool
    from app.services.hotpost.topic_tree_publish_surface_planner import TopicTreePublishSurfacePlanner

    history_items = [
        {
            "card_id": f"hist-growth-{index}",
            "lane": "signal",
            "title": f"Growth ads history {index}",
            "source_scope_id": "business-growth-ops",
            "topic_pack_id": "paid-economics",
            "topic_cluster_id": "ads",
            "matched_subreddit": "FacebookAds" if index % 2 else "PPC",
            "published_at": "2026-04-16T10:00:00Z",
        }
        for index in range(1, 9)
    ]
    pool = [
        {
            "plan_key": "growth-1",
            "lane": "signal",
            "title": "Another Meta ads swing",
            "source_scope_id": "business-growth-ops",
            "topic_pack_id": "paid-economics",
            "topic_cluster_id": "ads",
            "matched_subreddit": "FacebookAds",
            "score_hint": 140.0,
            "named_topic_ids": [],
        },
        {
            "plan_key": "growth-2",
            "lane": "signal",
            "title": "Another PPC budget panic",
            "source_scope_id": "business-growth-ops",
            "topic_pack_id": "paid-economics",
            "topic_cluster_id": "ads",
            "matched_subreddit": "PPC",
            "score_hint": 135.0,
            "named_topic_ids": [],
        },
        {
            "plan_key": "ai-1",
            "lane": "signal",
            "title": "Open-source model builders now swap orchestration later",
            "source_scope_id": "ai-automation",
            "topic_pack_id": "agent-builder",
            "topic_cluster_id": "agent-incidents",
            "matched_subreddit": "LLM",
            "score_hint": 118.0,
            "named_topic_ids": [],
        },
        {
            "plan_key": "ecom-1",
            "lane": "signal",
            "title": "Pet sellers now read category turns before reordering",
            "source_scope_id": "ecommerce-sellers",
            "topic_pack_id": "selection-signals",
            "topic_cluster_id": "pet",
            "matched_subreddit": "Frugal",
            "score_hint": 116.0,
            "named_topic_ids": [],
        },
    ]

    publish_surface_planner = TopicTreePublishSurfacePlanner(
        history_items=history_items,
        candidate_items=pool,
    )
    selected = _take_from_pool(
        pool,
        need=3,
        target_total=15,
        lane_counts=Counter(),
        lane_targets={"signal": 3},
        named_topic_counts=Counter(),
        used_keys=set(),
        planner_map={},
        publish_surface_planner=publish_surface_planner,
    )

    assert {item["source_scope_id"] for item in selected} == {
        "business-growth-ops",
        "ai-automation",
        "ecommerce-sellers",
    }


def test_take_from_pool_prefers_new_source_relief_for_risky_pack(monkeypatch) -> None:
    from collections import Counter

    from app.services.hotpost.offline_publish_plan import _take_from_pool
    from app.services.hotpost.topic_tree_governance_planner import TopicTreeGovernancePlanner

    history_items = [
        {
            "card_id": f"hist-funnel-{index}",
            "lane": "signal",
            "title": f"Checkout friction history {index}",
            "source_scope_id": "business-growth-ops",
            "topic_pack_id": "funnel-conversion",
            "topic_cluster_id": "funnel",
            "matched_subreddit": "ecommerce",
            "published_at": "2026-04-16T12:00:00Z",
        }
        for index in range(1, 5)
    ]
    pool = [
        {
            "plan_key": "old-source",
            "lane": "signal",
            "title": "Another checkout leak thread from the same old community",
            "source_scope_id": "business-growth-ops",
            "topic_pack_id": "funnel-conversion",
            "topic_cluster_id": "funnel",
            "matched_subreddit": "ecommerce",
            "score_hint": 140.0,
            "named_topic_ids": [],
        },
        {
            "plan_key": "new-source",
            "lane": "signal",
            "title": "Shopify teams now ask where booking flow leaks leads",
            "source_scope_id": "business-growth-ops",
            "topic_pack_id": "funnel-conversion",
            "topic_cluster_id": "funnel",
            "matched_subreddit": "shopify",
            "score_hint": 130.0,
            "named_topic_ids": [],
        },
    ]

    planner = TopicTreeGovernancePlanner(
        scope_id="business-growth-ops",
        history_items=history_items,
        candidate_items=pool,
        reference_time=datetime(2026, 4, 17, 12, 0, tzinfo=timezone.utc),
    )
    selected = _take_from_pool(
        pool,
        need=1,
        target_total=15,
        lane_counts=Counter(),
        lane_targets={"signal": 1},
        named_topic_counts=Counter(),
        used_keys=set(),
        planner_map={"business-growth-ops": planner},
    )

    assert selected[0]["plan_key"] == "new-source"


def test_offline_publish_plan_keeps_breakdown_suggestions_out_of_publish_list_until_materialized(monkeypatch) -> None:
    from types import SimpleNamespace

    from app.schemas.hotpost_card_candidates import CandidatePack
    from app.services.hotpost.offline_publish_plan import build_offline_publish_plan

    candidate_a = CandidatePack.model_validate(
        _candidate(
            "cand-bg-1",
            lane_hint="hot",
            scope="business-growth-ops",
            pack="paid-economics",
            title="Sales down over 50% from last year",
        )
    )
    candidate_b = CandidatePack.model_validate(
        _candidate(
            "cand-bg-2",
            lane_hint="signal",
            scope="business-growth-ops",
            pack="paid-economics",
            title="Google emails me to remind me it sells me junk clicks",
        )
    )
    suggestion = SimpleNamespace(
        suggestion_id="suggestion-1",
        candidate_ids=[candidate_a.candidate_id, candidate_b.candidate_id],
        hypothesis="这些讨论背后都卡在同一种投放经济账。",
        source_scope_id="business-growth-ops",
        evidence_score=0.9,
        thread_count=2,
        community_count=2,
    )

    monkeypatch.setattr("app.services.hotpost.offline_publish_plan.list_breakdown_suggestions", lambda source_scope_id=None, limit=30: [suggestion])

    monkeypatch.setattr("app.services.hotpost.offline_publish_plan.load_published_cards", lambda: [])
    monkeypatch.setattr(
        "app.services.hotpost.offline_publish_plan.list_candidates",
        lambda source_scope_id=None: [candidate_a, candidate_b] if source_scope_id in {None, "business-growth-ops"} else [],
    )
    monkeypatch.setattr("app.services.hotpost.offline_publish_plan.list_drafts", lambda source_scope_id=None: [])

    payload = build_offline_publish_plan(limit=5, scope="business-growth-ops")

    assert payload["inventory_summary"]["breakdown_suggestion_count"] == 1
    assert all(item["source_type"] != "breakdown_suggestion" for item in payload["publish_list"])


def test_plan_sort_key_prefers_hot_draft_over_candidate_when_governance_equal() -> None:
    from collections import Counter

    from app.services.hotpost.offline_publish_plan import _plan_sort_key

    class _Planner:
        def sort_key(self, item, *, lane_counts, lane_targets):
            del item, lane_counts, lane_targets
            return (0, 1, 1, 1, 1, 1, 0, -100.0, "same")

    draft_key = _plan_sort_key(
        {
            "lane": "hot",
            "source_type": "draft",
            "source_scope_id": "ai-automation",
            "topic_pack_id": "upstream-winds",
            "score_hint": 80.0,
            "title": "draft",
        },
        lane_counts=Counter(),
        lane_targets={"hot": 2},
        planner_map={"ai-automation": _Planner()},
    )
    candidate_key = _plan_sort_key(
        {
            "lane": "hot",
            "source_type": "candidate",
            "source_scope_id": "ai-automation",
            "topic_pack_id": "agent-builder",
            "score_hint": 100.0,
            "title": "candidate",
        },
        lane_counts=Counter(),
        lane_targets={"hot": 2},
        planner_map={"ai-automation": _Planner()},
    )

    assert draft_key < candidate_key


def test_lane_selection_order_prefers_signal_before_breakdown_for_baseline_window() -> None:
    from app.services.hotpost.offline_publish_plan import _lane_selection_order

    assert _lane_selection_order(15) == ("hot", "signal", "breakdown")
    assert _lane_selection_order(18) == ("hot", "signal", "breakdown")
    assert _lane_selection_order(30) == ("hot", "breakdown", "signal")


def test_offline_publish_plan_filters_to_requested_scope(monkeypatch) -> None:
    from app.schemas.hotpost_card_candidates import CandidatePack
    from app.services.hotpost.offline_publish_plan import build_offline_publish_plan

    candidates = [
        CandidatePack.model_validate(_candidate("cand-ai-hot-1", lane_hint="hot", scope="ai-automation", pack="upstream-winds", title="OpenAI pricing thread exploded")),
        CandidatePack.model_validate(_candidate("cand-bg-signal-1", lane_hint="signal", scope="business-growth-ops", pack="paid-economics", title="Meta daily swings now get read weekly first")),
    ]

    monkeypatch.setattr("app.services.hotpost.offline_publish_plan.load_published_cards", lambda: [])
    monkeypatch.setattr("app.services.hotpost.offline_publish_plan.list_candidates", lambda source_scope_id=None: [item for item in candidates if source_scope_id is None or item.source_scope_id == source_scope_id])
    monkeypatch.setattr("app.services.hotpost.offline_publish_plan.list_drafts", lambda source_scope_id=None: [])
    monkeypatch.setattr("app.services.hotpost.offline_publish_plan.list_breakdown_suggestions", lambda source_scope_id=None, limit=30: [])

    payload = build_offline_publish_plan(limit=2, scope="business-growth-ops")

    assert payload["scope"] == "business-growth-ops"
    assert all(item["source_scope_id"] == "business-growth-ops" for item in payload["publish_list"])


def test_growth_purity_cleanup_swaps_stale_organic_breakdown_for_content_marketing_candidate() -> None:
    from app.services.hotpost.offline_publish_plan import _apply_growth_purity_cleanup

    publish_list = [
        {
            "plan_key": "draft:old-organic",
            "source_type": "draft",
            "lane": "breakdown",
            "candidate_id": "group-business-growth-ops-old",
            "source_scope_id": "business-growth-ops",
            "topic_pack_id": "organic-discovery",
            "title": "Old organic breakdown",
        },
        {
            "plan_key": "candidate:funnel-live",
            "source_type": "candidate",
            "lane": "signal",
            "candidate_id": "cand-funnel-live",
            "source_scope_id": "business-growth-ops",
            "topic_pack_id": "funnel-conversion",
            "title": "Funnel card",
        },
    ]
    candidate_rows = [
        {
            "plan_key": "candidate:new-organic",
            "source_type": "candidate",
            "lane": "hot",
            "candidate_id": "cand-new-organic",
            "source_scope_id": "business-growth-ops",
            "topic_pack_id": "organic-discovery",
            "title": "Content marketing feels broken",
            "score_hint": 16.7,
            "primary_reason": "organic-discovery:listing_keyword_bridge",
            "matched_subreddit": "content_marketing",
        },
        {
            "plan_key": "candidate:emailmarketing",
            "source_type": "candidate",
            "lane": "signal",
            "candidate_id": "cand-email",
            "source_scope_id": "business-growth-ops",
            "topic_pack_id": "organic-discovery",
            "title": "Email list thread",
            "score_hint": 10.0,
            "primary_reason": "organic-discovery:listing_keyword_bridge",
            "matched_subreddit": "Emailmarketing",
        },
    ]

    updated = _apply_growth_purity_cleanup(publish_list=publish_list, candidate_rows=candidate_rows)

    assert updated[0]["candidate_id"] == "cand-new-organic"
    assert updated[0]["matched_subreddit"] == "content_marketing"
    assert updated[1]["candidate_id"] == "cand-funnel-live"


def test_signal_freshness_repair_replaces_old_signal_with_fresh_candidate() -> None:
    from datetime import timedelta

    from app.services.hotpost.offline_publish_plan import _repair_signal_target_freshness

    now = datetime(2026, 5, 3, 10, 0, tzinfo=timezone.utc)
    publish_list = [
        {
            "plan_key": "candidate:old-signal-1",
            "source_type": "candidate",
            "lane": "signal",
            "candidate_id": "old-signal-1",
            "title": "Old signal 1",
            "source_event_at": (now - timedelta(hours=108)).isoformat().replace("+00:00", "Z"),
        },
        {
            "plan_key": "candidate:old-signal-2",
            "source_type": "candidate",
            "lane": "signal",
            "candidate_id": "old-signal-2",
            "title": "Old signal 2",
            "source_event_at": (now - timedelta(hours=96)).isoformat().replace("+00:00", "Z"),
        },
        {
            "plan_key": "candidate:fresh-signal-1",
            "source_type": "candidate",
            "lane": "signal",
            "candidate_id": "fresh-signal-1",
            "title": "Fresh signal 1",
            "source_event_at": (now - timedelta(hours=24)).isoformat().replace("+00:00", "Z"),
        },
    ]
    candidate_rows = [
        *publish_list,
        {
            "plan_key": "candidate:fresh-signal-2",
            "source_type": "candidate",
            "lane": "signal",
            "candidate_id": "fresh-signal-2",
            "title": "Fresh signal 2",
            "score_hint": 10.0,
            "source_event_at": (now - timedelta(hours=36)).isoformat().replace("+00:00", "Z"),
        },
    ]

    repaired = _repair_signal_target_freshness(
        publish_list=publish_list,
        candidate_rows=candidate_rows,
        reference_time=now,
    )

    assert [item["candidate_id"] for item in repaired] == [
        "fresh-signal-2",
        "old-signal-2",
        "fresh-signal-1",
    ]


def test_topic_tree_governance_audit_counts_ready_drafts_in_supply_pool(monkeypatch) -> None:
    from app.schemas.hotpost_card_drafts import WritingCardDraft
    from app.services.hotpost.offline_publish_plan import build_offline_publish_plan

    now = datetime.now(timezone.utc)
    write_draft = WritingCardDraft.model_validate(
        {
            "draft_id": "draft-group-bg-1",
            "candidate_id": "group-bg-1",
            "candidate_ids": ["cand-bg-1", "cand-bg-2"],
            "card_id": "card-group-bg-1",
            "signal_id": "sig-group-bg-1",
            "topic_pack_id": "organic-discovery",
            "topic_cluster_id": "seo-content-ops",
            "topic_cluster_ids": ["seo-content-ops"],
            "named_topic_ids": [],
            "card_type": "write",
            "lane": "breakdown",
            "category_id": "write",
            "title": "Organic growth breakdown",
            "source_scope_id": "business-growth-ops",
            "source_scope_name": "Growth",
            "matched_subreddit": "content_marketing",
            "post_id": "post-group-bg-1",
            "source_event_at": now,
            "score": 500,
            "num_comments": 80,
            "time_window": "24h",
            "signal_level": "hot",
            "why_now_reason": "new_threads_24h",
            "thread_count": 2,
            "community_count": 2,
            "quote_count": 2,
            "intent_tags": ["趋势变化"],
            "evidence_quotes": [
                {
                    "text": "Organic teams now say content velocity is no longer enough.",
                    "community": "r/content_marketing",
                    "permalink": "https://www.reddit.com/r/content_marketing/comments/post-group-bg-1/q1",
                },
                {
                    "text": "SEO threads keep pointing at the same conversion bottleneck.",
                    "community": "r/SEO",
                    "permalink": "https://www.reddit.com/r/SEO/comments/post-group-bg-1/q2",
                },
            ],
            "summary_line": "Organic teams are changing how they judge content output.",
            "audience": "增长团队",
            "why_now": "多个社区开始给出同一种判断。",
            "source_link": "https://www.reddit.com/r/content_marketing/comments/post-group-bg-1",
            "source_links": ["https://www.reddit.com/r/content_marketing/comments/post-group-bg-1"],
            "source_communities": ["r/content_marketing", "r/SEO"],
            "draft_status": "draft",
            "draft_note": "ready",
            "detail": {
                "thesis": "Organic teams are moving from output goals to conversion goals.",
                "writing_angle_or_perspective": "The shift is in the evaluation rule, not the content calendar.",
                "tension_point_or_why_it_matters": "Teams are discovering content volume no longer hides weak conversion.",
                "title_hooks": ["hook-1"],
                "quote_pack": ["quote-1", "quote-2"],
            },
        }
    )

    monkeypatch.setattr("app.services.hotpost.offline_publish_plan.load_published_cards", lambda: [])
    monkeypatch.setattr("app.services.hotpost.offline_publish_plan.list_candidates", lambda source_scope_id=None: [])
    monkeypatch.setattr(
        "app.services.hotpost.offline_publish_plan.list_drafts",
        lambda source_scope_id=None: [write_draft] if source_scope_id in {None, "business-growth-ops"} else [],
    )
    monkeypatch.setattr("app.services.hotpost.offline_publish_plan.list_breakdown_suggestions", lambda source_scope_id=None, limit=30: [])

    payload = build_offline_publish_plan(limit=1, scope="business-growth-ops")

    supply = payload["topic_tree_governance"]["scopes"]["business-growth-ops"]["supply"]
    assert supply["pool_pack_counts"]["organic-discovery"] == 1
