from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, cast

from app.schemas.hotpost_signal import SourceScopeId
from app.services.hotpost.community_discovery_audit import (
    build_current_community_discovery_audit,
)
from app.services.hotpost.community_pool_feedback_dry_run import (
    build_pool_feedback_dry_run,
)
from app.services.hotpost.community_probe_collect import (
    collect_experimental_scope_probe,
)


@dataclass(frozen=True)
class ExplorationProbe:
    scope_id: str
    max_candidates: int | None = None
    mode: str = "safe"
    direction: str = ""


def parse_probe_arg(value: str) -> ExplorationProbe:
    parts = [part.strip() for part in value.split(":")]
    if not parts or not parts[0]:
        raise ValueError("probe must use scope[:max_candidates[:direction]]")
    max_candidates = int(parts[1]) if len(parts) >= 2 and parts[1] else None
    direction = parts[2] if len(parts) >= 3 else ""
    return ExplorationProbe(
        scope_id=parts[0], max_candidates=max_candidates, direction=direction
    )


async def run_exploration_pre_stage(
    *,
    probes: list[ExplorationProbe],
    report_date: str | None = None,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for probe in probes:
        summary = await collect_experimental_scope_probe(
            cast(SourceScopeId, probe.scope_id),
            max_candidates=probe.max_candidates,
            mode=probe.mode,
        )
        store = dict(summary.get("experimental_candidate_store") or {})
        rows.append(
            {
                "scope_id": probe.scope_id,
                "direction": probe.direction,
                "max_candidates": probe.max_candidates,
                "mode": probe.mode,
                "experimental_candidate_count": int(store.get("candidate_count") or 0),
                "experimental_candidate_path": str(store.get("path") or ""),
                "persisted_to_formal_candidates": bool(
                    summary.get("persisted_to_formal_candidates")
                ),
            }
        )
    return {
        "schema_version": "hotpost-community-exploration-loop/v1",
        "stage": "pre",
        "report_date": report_date or date.today().isoformat(),
        "contracts": {
            "probe_only": True,
            "writes_formal_candidates": False,
            "writes_db": False,
            "auto_promote": False,
        },
        "summary": {
            "probe_count": len(rows),
            "experimental_candidate_count": sum(
                int(row["experimental_candidate_count"]) for row in rows
            ),
        },
        "probes": rows,
    }


async def run_exploration_post_stage(
    *,
    report_date: str | None = None,
    pool_community_keys: set[str],
) -> dict[str, Any]:
    parsed_date = date.fromisoformat(report_date) if report_date else None
    audit = build_current_community_discovery_audit(report_date=parsed_date)
    feedback = build_pool_feedback_dry_run(
        audit, pool_community_keys=pool_community_keys
    )
    feedback_summary = dict(feedback.get("summary") or {})
    return {
        "schema_version": "hotpost-community-exploration-loop/v1",
        "stage": "post",
        "report_date": report_date or date.today().isoformat(),
        "contracts": {
            "probe_only": True,
            "writes_formal_candidates": False,
            "writes_db": False,
            "auto_promote": False,
            "requires_human_review": True,
        },
        "summary": {
            "audit_rows": len(list(audit.get("rows") or [])),
            "already_in_pool": int(feedback_summary.get("already_in_pool") or 0),
            "promote_candidate": int(feedback_summary.get("promote_candidate") or 0),
            "keep_testing": int(feedback_summary.get("keep_testing") or 0),
            "reject": int(feedback_summary.get("reject") or 0),
        },
        "audit": audit,
        "feedback": feedback,
    }


__all__ = [
    "ExplorationProbe",
    "parse_probe_arg",
    "run_exploration_pre_stage",
    "run_exploration_post_stage",
]
