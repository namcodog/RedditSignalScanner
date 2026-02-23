from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone

from app.services.ops.contract_health import (
    ContractHealthAlertThresholds,
    ContractHealthRow,
    compute_contract_health,
    evaluate_contract_health_alerts,
)


def _row_base(*, now: datetime) -> ContractHealthRow:
    return ContractHealthRow(
        task_id="00000000-0000-0000-0000-000000000000",
        status="completed",
        created_at=now - timedelta(minutes=10),
        started_at=now - timedelta(minutes=9),
        completed_at=now - timedelta(minutes=1),
        failure_category=None,
        sources=None,
    )


def test_compute_contract_health_aggregates_tiers_blocked_and_remediation() -> None:
    now = datetime(2025, 12, 29, 0, 0, 0, tzinfo=timezone.utc)

    row_ok = replace(
        _row_base(now=now),
        task_id="11111111-1111-1111-1111-111111111111",
        sources={
            "report_tier": "B_trimmed",
            "analysis_blocked": "",
            "facts_v2_quality": {"tier": "B_trimmed", "flags": [], "metrics": {}},
            "counts_analyzed": {"posts": 180, "comments": 50},
            "counts_db": {"posts_current": 500, "comments_total": 1000, "comments_eligible": 800},
            "comments_pipeline_status": "ok",
        },
    )

    row_scouting = replace(
        _row_base(now=now),
        task_id="22222222-2222-2222-2222-222222222222",
        sources={
            "report_tier": "C_scouting",
            "analysis_blocked": "scouting_brief",
            "facts_v2_quality": {"tier": "C_scouting", "flags": ["comments_not_used"], "metrics": {}},
            "counts_analyzed": {"posts": 80, "comments": 0},
            "counts_db": {"posts_current": 200, "comments_total": 300, "comments_eligible": 250},
            "comments_pipeline_status": "missing_scores",
            "remediation_actions": [
                {
                    "type": "backfill_comments",
                    "queue": "backfill_queue",
                    "targets": 5,
                    "outbox_enqueued": 3,
                    "outbox_deduped": 2,
                }
            ],
        },
    )

    row_blocked = replace(
        _row_base(now=now),
        task_id="33333333-3333-3333-3333-333333333333",
        sources={
            "report_tier": "X_blocked",
            "analysis_blocked": "quality_gate_blocked",
            "facts_v2_quality": {"tier": "X_blocked", "flags": ["topic_mismatch"], "metrics": {}},
            "counts_analyzed": {"posts": 0, "comments": 0},
            "counts_db": {"posts_current": 0, "comments_total": 0, "comments_eligible": 0},
            "comments_pipeline_status": "disabled",
        },
    )

    row_failed = replace(
        _row_base(now=now),
        task_id="44444444-4444-4444-4444-444444444444",
        status="failed",
        failure_category="data_validation_error",
        sources=None,
        completed_at=now - timedelta(minutes=2),
    )

    report = compute_contract_health(
        rows=[row_ok, row_scouting, row_blocked, row_failed],
        now=now,
        window=timedelta(hours=24),
    )

    assert report["tasks"]["total"] == 4
    assert report["tasks"]["by_status"]["completed"] == 3
    assert report["tasks"]["by_status"]["failed"] == 1

    assert report["reports"]["by_tier"]["B_trimmed"] == 1
    assert report["reports"]["by_tier"]["C_scouting"] == 1
    assert report["reports"]["by_tier"]["X_blocked"] == 1

    assert report["blocked"]["by_reason"]["scouting_brief"] == 1
    assert report["blocked"]["by_reason"]["quality_gate_blocked"] == 1

    remediation = report["remediation"]
    assert remediation["actions"] == 1
    assert remediation["targets_attempted"] == 5
    assert remediation["outbox_enqueued"] == 3
    assert remediation["outbox_deduped"] == 2

    comments = report["comments"]
    assert comments["comments_not_used_count"] == 1
    assert comments["comments_not_used_rate"] > 0

    failures = report["failures"]
    assert failures["by_category"]["data_validation_error"] == 1


def test_evaluate_contract_health_alerts_flags_comments_not_used() -> None:
    now = datetime(2025, 12, 29, 0, 0, 0, tzinfo=timezone.utc)
    report = compute_contract_health(
        rows=[
            replace(
                _row_base(now=now),
                task_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                sources={
                    "report_tier": "C_scouting",
                    "analysis_blocked": "scouting_brief",
                    "facts_v2_quality": {"tier": "C_scouting", "flags": ["comments_not_used"], "metrics": {}},
                    "counts_analyzed": {"posts": 10, "comments": 0},
                    "counts_db": {"posts_current": 50, "comments_total": 100, "comments_eligible": 80},
                    "comments_pipeline_status": "ok",
                },
            )
        ],
        now=now,
        window=timedelta(hours=24),
    )
    thresholds = ContractHealthAlertThresholds(comments_not_used_rate_warn=0.0)
    alerts = evaluate_contract_health_alerts(report, thresholds=thresholds)
    assert any(alert.code == "comments_not_used_rate_high" for alert in alerts)

