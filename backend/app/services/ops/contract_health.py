from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Iterable, Mapping


VALID_FACTS_TIERS = {"A_full", "B_trimmed", "C_scouting", "X_blocked"}


@dataclass(frozen=True, slots=True)
class ContractHealthRow:
    """A lightweight join row for contract health aggregation (Task + optional Analysis.sources)."""

    task_id: str
    status: str
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    failure_category: str | None
    sources: dict[str, Any] | None


@dataclass(frozen=True, slots=True)
class ContractHealthAlert:
    level: str  # "warn" | "error"
    code: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ContractHealthAlertThresholds:
    """Alert thresholds for ops dashboards (Phase106-2)."""

    comments_not_used_rate_warn: float = 0.10
    x_blocked_rate_warn: float = 0.15
    data_validation_error_count_warn: int = 1


def _as_int(value: Any, *, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _as_str(value: Any) -> str:
    return str(value or "").strip()


def _as_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _percentile(values: list[float], p: float) -> float | None:
    if not values:
        return None
    if p <= 0:
        return float(min(values))
    if p >= 100:
        return float(max(values))
    sorted_values = sorted(values)
    k = (len(sorted_values) - 1) * (p / 100.0)
    f = int(k)
    c = min(f + 1, len(sorted_values) - 1)
    if f == c:
        return float(sorted_values[f])
    d0 = sorted_values[f] * (c - k)
    d1 = sorted_values[c] * (k - f)
    return float(d0 + d1)


def compute_contract_health(
    *,
    rows: Iterable[ContractHealthRow],
    now: datetime,
    window: timedelta,
) -> dict[str, Any]:
    """
    Phase106-2: Aggregate "contract health" metrics from Task/Analysis sources.

    Human goal:
    - Turn Phase105 'contract fields' into an ops dashboard payload.
    - Must be safe: tolerate legacy/missing fields; never crash the monitoring loop.
    """
    rows_list = list(rows)
    status_counts: Counter[str] = Counter()
    failure_counts: Counter[str] = Counter()

    tier_counts: Counter[str] = Counter()
    blocked_reasons: Counter[str] = Counter()

    remediation_actions = 0
    remediation_targets_attempted = 0
    remediation_outbox_enqueued = 0
    remediation_outbox_deduped = 0

    auto_rerun_runs = 0
    auto_rerun_upgraded = 0

    comments_not_used_count = 0
    tiered_total = 0

    queue_seconds: list[float] = []
    end_to_end_seconds: list[float] = []
    processing_seconds: list[float] = []
    analysis_seconds: list[float] = []

    examples: dict[str, list[str]] = {
        "comments_not_used": [],
        "sources_missing": [],
        "x_blocked": [],
        "data_validation_error": [],
    }

    for row in rows_list:
        status = _as_str(row.status) or "unknown"
        status_counts[status] += 1

        if row.failure_category:
            category = _as_str(row.failure_category) or "unknown"
            failure_counts[category] += 1
            if category == "data_validation_error" and len(examples["data_validation_error"]) < 5:
                examples["data_validation_error"].append(row.task_id)

        if row.started_at and row.created_at:
            try:
                queue_seconds.append(
                    max(0.0, (row.started_at - row.created_at).total_seconds())
                )
            except Exception:
                pass
        if row.completed_at and row.created_at:
            try:
                end_to_end_seconds.append(
                    max(0.0, (row.completed_at - row.created_at).total_seconds())
                )
            except Exception:
                pass
        if row.completed_at and row.started_at:
            try:
                processing_seconds.append(
                    max(0.0, (row.completed_at - row.started_at).total_seconds())
                )
            except Exception:
                pass

        sources = row.sources
        if not isinstance(sources, dict):
            if status == "completed" and len(examples["sources_missing"]) < 5:
                examples["sources_missing"].append(row.task_id)
            continue

        tier_raw = _as_str(sources.get("report_tier"))
        if tier_raw not in VALID_FACTS_TIERS:
            tier_raw = _as_str(_as_dict(sources.get("facts_v2_quality")).get("tier"))
        tier = tier_raw if tier_raw in VALID_FACTS_TIERS else "unknown"
        if tier != "unknown":
            tier_counts[tier] += 1
            tiered_total += 1

        blocked_reason = _as_str(sources.get("analysis_blocked"))
        if not blocked_reason and tier == "C_scouting":
            blocked_reason = "scouting_brief"
        if not blocked_reason and tier == "X_blocked":
            blocked_reason = "quality_gate_blocked"
        if blocked_reason:
            blocked_reasons[blocked_reason] += 1
            if tier == "X_blocked" and len(examples["x_blocked"]) < 5:
                examples["x_blocked"].append(row.task_id)

        auto_rerun = _as_dict(sources.get("auto_rerun"))
        if _as_str(auto_rerun.get("trigger")) == "warmup_auto_rerun":
            auto_rerun_runs += 1
            if tier in {"A_full", "B_trimmed"}:
                auto_rerun_upgraded += 1

        actions = _as_list(sources.get("remediation_actions"))
        for action in actions:
            if not isinstance(action, Mapping):
                continue
            remediation_actions += 1
            remediation_targets_attempted += max(0, _as_int(action.get("targets")))
            remediation_outbox_enqueued += max(0, _as_int(action.get("outbox_enqueued")))
            remediation_outbox_deduped += max(0, _as_int(action.get("outbox_deduped")))

        facts_quality = _as_dict(sources.get("facts_v2_quality"))
        flags = _as_list(facts_quality.get("flags"))
        has_flag = "comments_not_used" in {str(x) for x in flags if x is not None}
        if has_flag:
            comments_not_used_count += 1
            if len(examples["comments_not_used"]) < 5:
                examples["comments_not_used"].append(row.task_id)
        else:
            # Defensive detection for legacy/partial sources.
            counts_db = _as_dict(sources.get("counts_db"))
            counts_analyzed = _as_dict(sources.get("counts_analyzed"))
            db_comments = _as_int(counts_db.get("comments_total"))
            analyzed_comments = _as_int(counts_analyzed.get("comments"))
            if db_comments > 0 and analyzed_comments <= 0:
                comments_not_used_count += 1
                if len(examples["comments_not_used"]) < 5:
                    examples["comments_not_used"].append(row.task_id)

        analysis_duration = sources.get("analysis_duration_seconds")
        if isinstance(analysis_duration, (int, float)):
            analysis_seconds.append(float(max(0.0, analysis_duration)))

    remediation_dedupe_rate: float | None = None
    if remediation_targets_attempted > 0:
        remediation_dedupe_rate = remediation_outbox_deduped / remediation_targets_attempted

    x_blocked_count = int(tier_counts.get("X_blocked", 0))
    x_blocked_rate: float | None = None
    if tiered_total > 0:
        x_blocked_rate = x_blocked_count / tiered_total

    comments_not_used_rate: float | None = None
    if tiered_total > 0:
        comments_not_used_rate = comments_not_used_count / tiered_total

    auto_rerun_upgrade_rate: float | None = None
    if auto_rerun_runs > 0:
        auto_rerun_upgrade_rate = auto_rerun_upgraded / auto_rerun_runs

    return {
        "window": {
            "now": now.isoformat(),
            "seconds": int(window.total_seconds()),
        },
        "tasks": {
            "total": len(rows_list),
            "by_status": dict(status_counts),
        },
        "reports": {
            "total": tiered_total,
            "by_tier": dict(tier_counts),
            "x_blocked_rate": x_blocked_rate,
        },
        "blocked": {
            "total": sum(blocked_reasons.values()),
            "by_reason": dict(blocked_reasons),
        },
        "remediation": {
            "actions": remediation_actions,
            "targets_attempted": remediation_targets_attempted,
            "outbox_enqueued": remediation_outbox_enqueued,
            "outbox_deduped": remediation_outbox_deduped,
            "dedupe_rate": remediation_dedupe_rate,
        },
        "auto_rerun": {
            "runs": auto_rerun_runs,
            "upgraded_to_A_or_B": auto_rerun_upgraded,
            "upgrade_rate": auto_rerun_upgrade_rate,
        },
        "comments": {
            "comments_not_used_count": comments_not_used_count,
            "comments_not_used_rate": comments_not_used_rate,
        },
        "latency": {
            "queue_seconds_p50": _percentile(queue_seconds, 50),
            "queue_seconds_p95": _percentile(queue_seconds, 95),
            "end_to_end_seconds_p50": _percentile(end_to_end_seconds, 50),
            "end_to_end_seconds_p95": _percentile(end_to_end_seconds, 95),
            "processing_seconds_p50": _percentile(processing_seconds, 50),
            "analysis_duration_seconds_p50": _percentile(analysis_seconds, 50),
        },
        "failures": {
            "by_category": dict(failure_counts),
        },
        "examples": examples,
    }


def evaluate_contract_health_alerts(
    report: Mapping[str, Any],
    *,
    thresholds: ContractHealthAlertThresholds | None = None,
) -> list[ContractHealthAlert]:
    thresholds = thresholds or ContractHealthAlertThresholds()
    alerts: list[ContractHealthAlert] = []

    comments = _as_dict(report.get("comments"))
    comments_not_used_rate = comments.get("comments_not_used_rate")
    if isinstance(comments_not_used_rate, (int, float)) and comments_not_used_rate > float(
        thresholds.comments_not_used_rate_warn
    ):
        examples = _as_dict(report.get("examples")).get("comments_not_used") or []
        alerts.append(
            ContractHealthAlert(
                level="warn",
                code="comments_not_used_rate_high",
                message="评论在库里有，但分析没吃到：可能是评论评分/过滤链路断了，或阈值太严。",
                details={
                    "rate": float(comments_not_used_rate),
                    "threshold": float(thresholds.comments_not_used_rate_warn),
                    "example_task_ids": list(examples)[:5] if isinstance(examples, list) else [],
                },
            )
        )

    reports = _as_dict(report.get("reports"))
    x_blocked_rate = reports.get("x_blocked_rate")
    if isinstance(x_blocked_rate, (int, float)) and x_blocked_rate > float(
        thresholds.x_blocked_rate_warn
    ):
        examples = _as_dict(report.get("examples")).get("x_blocked") or []
        alerts.append(
            ContractHealthAlert(
                level="warn",
                code="x_blocked_rate_high",
                message="X_blocked 比例偏高：质量门禁在大量拦截，先看 topic_profile/样本供给/过滤是否过严。",
                details={
                    "rate": float(x_blocked_rate),
                    "threshold": float(thresholds.x_blocked_rate_warn),
                    "example_task_ids": list(examples)[:5] if isinstance(examples, list) else [],
                },
            )
        )

    failures = _as_dict(report.get("failures"))
    data_validation_error_count = _as_int(
        _as_dict(failures.get("by_category")).get("data_validation_error")
    )
    if data_validation_error_count >= int(thresholds.data_validation_error_count_warn):
        examples = _as_dict(report.get("examples")).get("data_validation_error") or []
        alerts.append(
            ContractHealthAlert(
                level="error",
                code="sources_ledger_validation_failed",
                message="sources 强校验失败：任务会失败但不能假死。需要立刻定位是哪条链路没写账本字段。",
                details={
                    "count": int(data_validation_error_count),
                    "threshold": int(thresholds.data_validation_error_count_warn),
                    "example_task_ids": list(examples)[:5] if isinstance(examples, list) else [],
                },
            )
        )

    return alerts


__all__ = [
    "ContractHealthAlert",
    "ContractHealthAlertThresholds",
    "ContractHealthRow",
    "compute_contract_health",
    "evaluate_contract_health_alerts",
]

