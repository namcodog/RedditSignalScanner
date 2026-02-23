from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass(frozen=True)
class DbSnapshot:
    now: datetime

    posts_raw_newest_fetched_at: datetime | None
    posts_hot_newest_cached_at: datetime | None
    comments_newest_fetched_at: datetime | None

    posts_raw_fetched_24h: int
    posts_hot_cached_24h: int
    comments_fetched_24h: int

    community_cache_total: int
    community_cache_active_total: int
    community_cache_never_crawled: int
    community_cache_stale_24h: int

    pool_total: int
    pool_active_total: int
    pool_missing_cache: int

    crawler_runs_total: int
    crawler_run_targets_total: int

    discovered_communities_total: int
    evidence_posts_total: int

    def newest_supply_at(self) -> datetime | None:
        """Newest timestamp proving the crawler is still 'feeding' the DB."""
        candidates: list[datetime] = []
        if self.posts_raw_newest_fetched_at is not None:
            candidates.append(self.posts_raw_newest_fetched_at)
        if self.posts_hot_newest_cached_at is not None:
            candidates.append(self.posts_hot_newest_cached_at)
        return max(candidates) if candidates else None

    def supply_gap(self) -> timedelta | None:
        newest = self.newest_supply_at()
        if newest is None:
            return None
        return self.now - newest


@dataclass(frozen=True)
class EnvFlags:
    probe_hot_beat_enabled: bool
    probe_auto_evaluate_enabled: bool
    cron_discovery_enabled: bool
    comments_backfill_subs_configured: bool


@dataclass(frozen=True)
class WorkflowDecision:
    start_beat: bool
    start_patrol_worker: bool
    start_bulk_worker: bool
    start_probe_worker: bool

    supply_gap: timedelta | None
    notes: tuple[str, ...]


@dataclass(frozen=True)
class WorkflowPolicy:
    """Tunable guardrails for auto recommendations."""

    # How stale is considered 'broken supply' (used for messaging / probe gating).
    supply_stale_after: timedelta = timedelta(hours=6)


def decide_workflow(*, snapshot: DbSnapshot, flags: EnvFlags, policy: WorkflowPolicy | None = None) -> WorkflowDecision:
    effective_policy = policy or WorkflowPolicy()
    gap = snapshot.supply_gap()

    notes: list[str] = []
    if snapshot.crawler_runs_total == 0 and snapshot.crawler_run_targets_total == 0:
        notes.append("这套库里还没跑起来 run/targets（新口径）——先把巡航供货跑通。")

    if gap is None:
        notes.append("没拿到供货时间（posts_raw/posts_hot 都没有 newest 时间），当作断供处理。")
    else:
        gap_hours = gap.total_seconds() / 3600.0
        notes.append(f"供货断档约 {gap_hours:.1f} 小时（看 posts_raw/posts_hot 的最新时间）。")

    if snapshot.pool_missing_cache > 0:
        notes.append(
            f"community_pool 里有 {snapshot.pool_missing_cache} 个社区还没进 community_cache（首轮巡航会补齐）。"
        )

    start_beat = True
    start_patrol_worker = True
    start_bulk_worker = True  # backfill/maintenance/crawler_queue 都靠它

    # Probe worker 只在“确实要跑 probe 相关任务”时启动
    probe_required_by_flags = flags.probe_hot_beat_enabled or flags.cron_discovery_enabled
    supply_is_stale = (gap is None) or (gap >= effective_policy.supply_stale_after)
    if supply_is_stale and not probe_required_by_flags:
        start_probe_worker = False
        notes.append("当前先不建议开 probe（先把供货跑起来；probe 以后再开）。")
    else:
        start_probe_worker = probe_required_by_flags

    if start_probe_worker and not flags.probe_auto_evaluate_enabled:
        notes.append("probe 自动触发 evaluator 目前是关的（PROBE_AUTO_EVALUATE_ENABLED=0）。")

    if flags.comments_backfill_subs_configured:
        notes.append("你现在配置了 comments 夜间回填（COMMENTS_BACKFILL_SUBS 非空），bulk worker 需要常驻。")

    return WorkflowDecision(
        start_beat=start_beat,
        start_patrol_worker=start_patrol_worker,
        start_bulk_worker=start_bulk_worker,
        start_probe_worker=start_probe_worker,
        supply_gap=gap,
        notes=tuple(notes),
    )

