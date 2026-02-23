from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone

from app.services.ops.smart_crawler_workflow import DbSnapshot, EnvFlags, decide_workflow


def _snapshot_base(*, now: datetime) -> DbSnapshot:
    return DbSnapshot(
        now=now,
        posts_raw_newest_fetched_at=None,
        posts_hot_newest_cached_at=None,
        comments_newest_fetched_at=None,
        posts_raw_fetched_24h=0,
        posts_hot_cached_24h=0,
        comments_fetched_24h=0,
        community_cache_total=0,
        community_cache_active_total=0,
        community_cache_never_crawled=0,
        community_cache_stale_24h=0,
        pool_total=0,
        pool_active_total=0,
        pool_missing_cache=0,
        crawler_runs_total=0,
        crawler_run_targets_total=0,
        discovered_communities_total=0,
        evidence_posts_total=0,
    )


def test_decide_workflow_supply_stale_probe_off_by_default() -> None:
    now = datetime(2025, 12, 19, 0, 0, 0, tzinfo=timezone.utc)
    oldest = now - timedelta(days=3)
    snapshot = _snapshot_base(now=now)
    snapshot = replace(
        snapshot,
        posts_raw_newest_fetched_at=oldest,
        posts_hot_newest_cached_at=oldest,
    )
    flags = EnvFlags(
        probe_hot_beat_enabled=False,
        probe_auto_evaluate_enabled=False,
        cron_discovery_enabled=False,
        comments_backfill_subs_configured=False,
    )

    decision = decide_workflow(snapshot=snapshot, flags=flags)
    assert decision.start_beat is True
    assert decision.start_patrol_worker is True
    assert decision.start_bulk_worker is True
    assert decision.start_probe_worker is False


def test_decide_workflow_probe_required_by_hot_beat_even_if_supply_stale() -> None:
    now = datetime(2025, 12, 19, 0, 0, 0, tzinfo=timezone.utc)
    oldest = now - timedelta(days=3)
    snapshot = _snapshot_base(now=now)
    snapshot = replace(
        snapshot,
        posts_raw_newest_fetched_at=oldest,
        posts_hot_newest_cached_at=oldest,
    )
    flags = EnvFlags(
        probe_hot_beat_enabled=True,
        probe_auto_evaluate_enabled=False,
        cron_discovery_enabled=False,
        comments_backfill_subs_configured=False,
    )

    decision = decide_workflow(snapshot=snapshot, flags=flags)
    assert decision.start_probe_worker is True


def test_decide_workflow_notes_mentions_comments_backfill_subs() -> None:
    now = datetime(2025, 12, 19, 0, 0, 0, tzinfo=timezone.utc)
    snapshot = _snapshot_base(now=now)
    flags = EnvFlags(
        probe_hot_beat_enabled=False,
        probe_auto_evaluate_enabled=False,
        cron_discovery_enabled=False,
        comments_backfill_subs_configured=True,
    )

    decision = decide_workflow(snapshot=snapshot, flags=flags)
    assert any("COMMENTS_BACKFILL_SUBS" in note for note in decision.notes)
