from __future__ import annotations

import argparse
from typing import Any

from sqlalchemy import text

from app.db.session import SessionFactory
from app.services.community.truth_source_readiness_service import (
    read_truth_source_readiness_snapshot,
)


def safe_ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(float(numerator) / float(denominator), 4)


async def read_backlog_snapshot(stale_minutes: int) -> dict[str, int]:
    async with SessionFactory() as session:
        row = (
            await session.execute(
                text(
                    """
                    SELECT
                      (SELECT COUNT(*) FROM task_outbox WHERE status = 'pending') AS task_outbox_pending,
                      (
                        SELECT COUNT(*)
                        FROM task_outbox
                        WHERE status = 'pending'
                          AND created_at < now() - make_interval(mins => :stale_minutes)
                      ) AS task_outbox_pending_stale,
                      (
                        SELECT COUNT(*)
                        FROM crawler_run_targets
                        WHERE status = 'queued'
                      ) AS crawler_run_targets_queued,
                      (
                        SELECT COUNT(*)
                        FROM crawler_run_targets
                        WHERE status = 'queued' AND enqueued_at IS NULL
                      ) AS crawler_run_targets_queued_not_enqueued,
                      (
                        SELECT COUNT(*)
                        FROM crawler_run_targets
                        WHERE status = 'queued'
                          AND enqueued_at IS NULL
                          AND started_at < now() - make_interval(mins => :stale_minutes)
                      ) AS crawler_run_targets_queued_not_enqueued_stale,
                      (
                        SELECT COUNT(*)
                        FROM crawler_run_targets
                        WHERE status = 'running'
                      ) AS crawler_run_targets_running
                    """
                ),
                {"stale_minutes": stale_minutes},
            )
        ).mappings().one()
    return {key: int(value or 0) for key, value in row.items()}


async def read_truth_source_snapshot(lookback_days: int) -> dict[str, int | float]:
    async with SessionFactory() as session:
        snapshot = await read_truth_source_readiness_snapshot(
            session,
            lookback_days=lookback_days,
        )
    return snapshot.as_dict()


def collect_violations(
    backlog_snapshot: dict[str, int],
    truth_snapshot: dict[str, int | float],
    args: argparse.Namespace,
) -> list[str]:
    violations: list[str] = []

    if backlog_snapshot["task_outbox_pending_stale"] > args.max_stale_task_outbox_pending:
        violations.append(
            "task_outbox_pending_stale={count} > {limit} (window={window}m)".format(
                count=backlog_snapshot["task_outbox_pending_stale"],
                limit=args.max_stale_task_outbox_pending,
                window=args.stale_minutes,
            )
        )
    if (
        backlog_snapshot["crawler_run_targets_queued_not_enqueued_stale"]
        > args.max_stale_crawler_targets_not_enqueued
    ):
        violations.append(
            "crawler_run_targets_queued_not_enqueued_stale={count} > {limit} (window={window}m)".format(
                count=backlog_snapshot["crawler_run_targets_queued_not_enqueued_stale"],
                limit=args.max_stale_crawler_targets_not_enqueued,
                window=args.stale_minutes,
            )
        )

    if not bool(truth_snapshot["truth_tables_ready"]):
        violations.append(
            "truth_tables_ready=false missing={tables}".format(
                tables=",".join(truth_snapshot["missing_truth_tables"]),
            )
        )
    if int(truth_snapshot["approved_registry_count"]) < args.min_active_pool:
        violations.append(
            "approved_registry_count={count} < min_active_pool={limit}".format(
                count=int(truth_snapshot["approved_registry_count"]),
                limit=args.min_active_pool,
            )
        )
    if (
        float(truth_snapshot["approved_registry_runtime_gap_ratio"])
        > args.max_active_pool_cache_gap_ratio
    ):
        violations.append(
            "approved_registry_runtime_gap_ratio={value:.4f} > max_active_pool_cache_gap_ratio={limit:.4f}".format(
                value=float(truth_snapshot["approved_registry_runtime_gap_ratio"]),
                limit=args.max_active_pool_cache_gap_ratio,
            )
        )
    if (
        int(truth_snapshot["enabled_registry_missing_membership_count"])
        > args.max_active_pool_missing_categories
    ):
        violations.append(
            "enabled_registry_missing_membership_count={count} > max_active_pool_missing_categories={limit}".format(
                count=int(truth_snapshot["enabled_registry_missing_membership_count"]),
                limit=args.max_active_pool_missing_categories,
            )
        )
    if (
        float(truth_snapshot["membership_coverage_ratio"])
        < args.min_active_pool_category_map_coverage_ratio
    ):
        violations.append(
            "membership_coverage_ratio={value:.4f} < min_active_pool_category_map_coverage_ratio={limit:.4f}".format(
                value=float(truth_snapshot["membership_coverage_ratio"]),
                limit=args.min_active_pool_category_map_coverage_ratio,
            )
        )
    if int(truth_snapshot["recent_posts_count"]) < args.min_recent_posts:
        violations.append(
            "recent_posts_count={count} < min_recent_posts={limit} (lookback={days}d)".format(
                count=int(truth_snapshot["recent_posts_count"]),
                limit=args.min_recent_posts,
                days=args.semantic_lookback_days,
            )
        )
    if (
        int(truth_snapshot["recent_posts_count"]) > 0
        and float(truth_snapshot["recent_posts_semantic_coverage_ratio"])
        < args.min_recent_posts_llm_label_coverage_ratio
    ):
        violations.append(
            "recent_posts_semantic_coverage_ratio={value:.4f} < min_recent_posts_llm_label_coverage_ratio={limit:.4f}".format(
                value=float(truth_snapshot["recent_posts_semantic_coverage_ratio"]),
                limit=args.min_recent_posts_llm_label_coverage_ratio,
            )
        )
    return violations


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Live report acceptance preflight gate")
    parser.add_argument("--stale-minutes", type=int, default=45)
    parser.add_argument("--max-stale-task-outbox-pending", type=int, default=120)
    parser.add_argument("--max-stale-crawler-targets-not-enqueued", type=int, default=200)
    parser.add_argument("--semantic-lookback-days", type=int, default=30)
    parser.add_argument("--min-active-pool", type=int, default=80)
    parser.add_argument("--max-active-pool-cache-gap-ratio", type=float, default=0.35)
    parser.add_argument("--max-active-pool-missing-categories", type=int, default=5)
    parser.add_argument("--min-active-pool-category-map-coverage-ratio", type=float, default=0.6)
    parser.add_argument("--min-recent-posts", type=int, default=800)
    parser.add_argument("--min-recent-posts-llm-label-coverage-ratio", type=float, default=0.06)
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--json-only", action="store_true")
    return parser


def format_summary(backlog_snapshot: dict[str, int], truth_snapshot: dict[str, int | float]) -> str:
    return (
        "pending={pending} stale_pending={stale_pending} queued={queued} "
        "stale_not_enqueued={stale_not_enqueued} running={running} "
        "approved_registry={approved_registry} active_runtime={active_runtime} "
        "recent_posts={recent_posts} recent_semantic_posts={recent_semantic}"
    ).format(
        pending=backlog_snapshot["task_outbox_pending"],
        stale_pending=backlog_snapshot["task_outbox_pending_stale"],
        queued=backlog_snapshot["crawler_run_targets_queued"],
        stale_not_enqueued=backlog_snapshot["crawler_run_targets_queued_not_enqueued_stale"],
        running=backlog_snapshot["crawler_run_targets_running"],
        approved_registry=int(truth_snapshot["approved_registry_count"]),
        active_runtime=int(truth_snapshot["active_runtime_count"]),
        recent_posts=int(truth_snapshot["recent_posts_count"]),
        recent_semantic=int(truth_snapshot["recent_posts_with_semantic_count"]),
    )


def build_payload(
    *,
    args: argparse.Namespace,
    backlog_snapshot: dict[str, int],
    truth_snapshot: dict[str, int | float],
    violations: list[str],
) -> dict[str, Any]:
    return {
        "ok": len(violations) == 0,
        "strict": bool(args.strict),
        "thresholds": vars(args),
        "snapshot": {"backlog": backlog_snapshot, "truth_source": truth_snapshot},
        "violations": violations,
    }
