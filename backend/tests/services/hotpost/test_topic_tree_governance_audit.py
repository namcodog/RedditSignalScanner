from __future__ import annotations

from datetime import datetime, timedelta, timezone


def _record(
    item_id: str,
    *,
    title: str,
    pack: str,
    cluster: str,
    community: str,
    published_hours_ago: float,
    scope: str = "business-growth-ops",
    cluster_ids: list[str] | None = None,
    named_topic_ids: list[str] | None = None,
    score_hint: float = 120.0,
) -> dict:
    now = datetime(2026, 4, 17, 12, 0, tzinfo=timezone.utc)
    published_at = now - timedelta(hours=published_hours_ago)
    return {
        "plan_key": item_id,
        "card_id": f"card-{item_id}",
        "lane": "signal",
        "title": title,
        "source_scope_id": scope,
        "topic_pack_id": pack,
        "topic_cluster_id": cluster,
        "topic_cluster_ids": cluster_ids or [cluster],
        "named_topic_ids": named_topic_ids or [],
        "matched_subreddit": community,
        "published_at": published_at.isoformat().replace("+00:00", "Z"),
        "source_event_at": published_at.isoformat().replace("+00:00", "Z"),
        "score_hint": score_hint,
    }


def test_topic_tree_governance_flags_missing_visible_pack() -> None:
    from app.services.hotpost.topic_tree_governance_audit import build_topic_tree_governance_audit
    from app.services.hotpost.topic_tree_governance_common import build_topic_tree_records

    reference_time = datetime(2026, 4, 17, 12, 0, tzinfo=timezone.utc)
    history = build_topic_tree_records(
        [
            _record("hist-1", title="Meta weekly swings", pack="paid-economics", cluster="ads", community="PPC", published_hours_ago=12),
        ],
        reference_time=reference_time,
        treat_as_published=False,
    )
    planned = build_topic_tree_records(
        [
            _record("plan-1", title="Meta weekly swings again", pack="paid-economics", cluster="ads", community="PPC", published_hours_ago=0),
        ],
        reference_time=reference_time,
        treat_as_published=True,
    )
    candidates = build_topic_tree_records(
        [
            _record("cand-1", title="SEO visibility moved to citation-ready pages", pack="organic-discovery", cluster="seo-geo", community="content_marketing", published_hours_ago=0),
        ],
        reference_time=reference_time,
        treat_as_published=True,
    )

    audit = build_topic_tree_governance_audit(
        scope_id="business-growth-ops",
        history_records=history,
        planned_records=planned,
        candidate_records=candidates,
        reference_time=reference_time,
    )

    assert audit["allocation"]["decision"] == "rewrite"
    assert "organic-discovery" in audit["allocation"]["missing_pack_ids"]


def test_topic_tree_governance_flags_rotation_fatigue_without_override() -> None:
    from app.services.hotpost.topic_tree_governance_audit import build_topic_tree_governance_audit
    from app.services.hotpost.topic_tree_governance_common import build_topic_tree_records

    reference_time = datetime(2026, 4, 17, 12, 0, tzinfo=timezone.utc)
    repeated = _record(
        "hist-1",
        title="Meta 投手现在先看周级波动，不再先怀疑单日翻车",
        pack="paid-economics",
        cluster="ads",
        community="PPC",
        published_hours_ago=18,
        score_hint=120.0,
    )
    history = build_topic_tree_records([repeated], reference_time=reference_time, treat_as_published=False)
    planned = build_topic_tree_records(
        [
            _record(
                "plan-1",
                title="Meta 投手现在先看周级波动，不再先怀疑单日翻车",
                pack="paid-economics",
                cluster="ads",
                community="PPC",
                published_hours_ago=0,
                score_hint=130.0,
            )
        ],
        reference_time=reference_time,
        treat_as_published=True,
    )

    audit = build_topic_tree_governance_audit(
        scope_id="business-growth-ops",
        history_records=history,
        planned_records=planned,
        candidate_records=[],
        reference_time=reference_time,
    )

    assert audit["rotation"]["decision"] == "rewrite"
    assert audit["rotation"]["flagged_items"]


def test_topic_tree_governance_identifies_old_source_concentration() -> None:
    from app.services.hotpost.topic_tree_governance_audit import build_topic_tree_governance_audit
    from app.services.hotpost.topic_tree_governance_common import build_topic_tree_records

    reference_time = datetime(2026, 4, 17, 12, 0, tzinfo=timezone.utc)
    history = build_topic_tree_records(
        [
            _record("hist-1", title="Ad account swings again", pack="paid-economics", cluster="ads", community="PPC", published_hours_ago=24),
            _record("hist-2", title="Another ads thread", pack="paid-economics", cluster="ads", community="PPC", published_hours_ago=36),
            _record("hist-3", title="Budget thread", pack="paid-economics", cluster="ads", community="PPC", published_hours_ago=48),
        ],
        reference_time=reference_time,
        treat_as_published=False,
    )
    candidate_records = build_topic_tree_records(
        [
            _record("cand-1", title="Agency thread", pack="paid-economics", cluster="ads", community="agency", published_hours_ago=0),
        ],
        reference_time=reference_time,
        treat_as_published=True,
    )

    audit = build_topic_tree_governance_audit(
        scope_id="business-growth-ops",
        history_records=history,
        planned_records=[],
        candidate_records=candidate_records,
        reference_time=reference_time,
    )

    assert audit["source_health"]["decision"] == "rewrite"
    assert "paid-economics" in audit["source_health"]["risky_pack_ids"]
    assert audit["source_health"]["new_source_credit_count"] >= 1


def test_topic_tree_governance_counts_merged_cluster_ids_in_candidate_pool() -> None:
    from app.services.hotpost.topic_tree_governance_audit import build_topic_tree_governance_audit
    from app.services.hotpost.topic_tree_governance_common import build_topic_tree_records

    reference_time = datetime(2026, 4, 17, 12, 0, tzinfo=timezone.utc)
    candidates = build_topic_tree_records(
        [
            _record(
                "cand-1",
                title="OpenAI pricing route changed again",
                pack="upstream-winds",
                cluster="key-people-and-route",
                cluster_ids=["key-people-and-route", "platform-policy-shifts"],
                community="OpenAI",
                published_hours_ago=0,
                scope="ai-automation",
            ),
        ],
        reference_time=reference_time,
        treat_as_published=True,
    )

    audit = build_topic_tree_governance_audit(
        scope_id="ai-automation",
        history_records=[],
        planned_records=[],
        candidate_records=candidates,
        reference_time=reference_time,
    )

    assert audit["allocation"]["candidate_cluster_counts"]["key-people-and-route"] == 1
    assert audit["allocation"]["candidate_cluster_counts"]["platform-policy-shifts"] == 1
    assert audit["supply"]["pool_cluster_counts"]["platform-policy-shifts"] == 1
