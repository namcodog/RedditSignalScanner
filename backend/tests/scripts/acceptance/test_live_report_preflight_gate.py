from __future__ import annotations

from types import SimpleNamespace

from scripts.acceptance.live_report_preflight_core import (
    build_parser,
    build_payload,
    collect_violations,
)


def _args(**overrides: object) -> SimpleNamespace:
    base = {
        "stale_minutes": 45,
        "max_stale_task_outbox_pending": 120,
        "max_stale_crawler_targets_not_enqueued": 200,
        "semantic_lookback_days": 30,
        "min_active_pool": 80,
        "max_active_pool_cache_gap_ratio": 0.35,
        "max_active_pool_missing_categories": 5,
        "min_active_pool_category_map_coverage_ratio": 0.6,
        "min_recent_posts": 800,
        "min_recent_posts_llm_label_coverage_ratio": 0.06,
        "strict": True,
        "json_only": True,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def test_collect_violations_passes_on_healthy_snapshot() -> None:
    backlog_snapshot = {
        "task_outbox_pending": 9,
        "task_outbox_pending_stale": 0,
        "crawler_run_targets_queued": 12,
        "crawler_run_targets_queued_not_enqueued": 2,
        "crawler_run_targets_queued_not_enqueued_stale": 0,
        "crawler_run_targets_running": 4,
    }
    truth_snapshot = {
        "truth_tables_ready": True,
        "missing_truth_tables": [],
        "enabled_registry_count": 140,
        "registry_with_current_membership_count": 132,
        "approved_registry_count": 120,
        "active_runtime_count": 118,
        "enabled_registry_missing_membership_count": 4,
        "membership_coverage_ratio": 0.9429,
        "approval_coverage_ratio": 0.8571,
        "approved_registry_runtime_gap_count": 2,
        "approved_registry_runtime_gap_ratio": 0.0167,
        "recent_posts_count": 4200,
        "recent_posts_with_semantic_count": 520,
        "recent_posts_semantic_coverage_ratio": 0.1238,
    }

    violations = collect_violations(backlog_snapshot, truth_snapshot, _args())
    assert violations == []


def test_collect_violations_flags_truth_source_drift() -> None:
    backlog_snapshot = {
        "task_outbox_pending": 12,
        "task_outbox_pending_stale": 0,
        "crawler_run_targets_queued": 20,
        "crawler_run_targets_queued_not_enqueued": 1,
        "crawler_run_targets_queued_not_enqueued_stale": 0,
        "crawler_run_targets_running": 3,
    }
    truth_snapshot = {
        "truth_tables_ready": False,
        "missing_truth_tables": ["community_registry"],
        "enabled_registry_count": 9,
        "registry_with_current_membership_count": 2,
        "approved_registry_count": 5,
        "active_runtime_count": 1,
        "enabled_registry_missing_membership_count": 7,
        "membership_coverage_ratio": 0.2222,
        "approval_coverage_ratio": 0.5556,
        "approved_registry_runtime_gap_count": 4,
        "approved_registry_runtime_gap_ratio": 0.8,
        "recent_posts_count": 100,
        "recent_posts_with_semantic_count": 1,
        "recent_posts_semantic_coverage_ratio": 0.01,
    }

    violations = collect_violations(backlog_snapshot, truth_snapshot, _args())
    assert any("truth_tables_ready" in item for item in violations)
    assert any("approved_registry_count" in item for item in violations)
    assert any("approved_registry_runtime_gap_ratio" in item for item in violations)
    assert any("recent_posts_count" in item for item in violations)
    assert any("recent_posts_semantic_coverage_ratio" in item for item in violations)


def test_build_payload_keeps_new_truth_source_section() -> None:
    parser = build_parser()
    args = parser.parse_args([])
    payload = build_payload(
        args=args,
        backlog_snapshot={"task_outbox_pending": 1},
        truth_snapshot={"approved_registry_count": 88},
        violations=[],
    )
    assert payload["ok"] is True
    assert "truth_source" in payload["snapshot"]
