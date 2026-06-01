from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.scripts_support.env_loader import load_backend_env
from app.services.hotpost.hotpost_supply_contract import get_supply_collect_profile, get_supply_operation_defaults
from app.services.hotpost.intake_freshness_gate import evaluate_publish_plan, should_escalate_named_topic_collect
from app.services.hotpost.named_topic_candidate_collector import collect_named_topic_candidates
from app.services.hotpost.named_topic_watchlist import get_default_named_topic_preset, resolve_named_topic_watchlist
from app.services.hotpost.offline_publish_plan import build_offline_publish_plan
from app.services.hotpost.quota_aware_collect_runner import run_quota_aware_collect
from app.services.hotpost.topic_tree_governance_remediation import build_governance_topic_watches_for_gate
from scripts.hotpost.sync_topic_metadata import sync_topic_metadata

def _resolve_collect_scope(args: argparse.Namespace) -> str | None:
    if getattr(args, "all_scope", False):
        return None
    return getattr(args, "scope", None)


async def _run(args: argparse.Namespace) -> dict[str, Any]:
    load_backend_env()
    target_total = int(args.limit or get_supply_operation_defaults()["min_cards_per_run"])
    collect_scope = _resolve_collect_scope(args)

    sync_runs: list[dict[str, Any]] = []
    triggered_actions: list[str] = []

    collect_summary: dict[str, Any] | None = None
    named_topic_summary: dict[str, Any] | None = None
    governance_collect_summary: dict[str, Any] | None = None
    governance_preview: dict[str, Any] | None = None

    if not args.no_collect:
        triggered_actions.append("daily_collect")
        _progress("daily_collect", "started", mode=args.collect_mode, scope=collect_scope)
        collect_summary = await _run_daily_collect(mode=args.collect_mode, scope=collect_scope)
        _progress("daily_collect", "completed", summary=collect_summary)

    sync_step = "post_collect_sync" if collect_summary is not None else "initial_sync"
    _progress(sync_step, "started")
    sync_runs.append({"step": sync_step, "summary": sync_topic_metadata()})
    _progress(sync_step, "completed", summary=sync_runs[-1]["summary"])
    _progress("publish_plan", "started", target_total=target_total, scope=collect_scope)
    payload = _write_plan(target_total, scope=collect_scope, output_path=args.output_plan)
    initial = evaluate_publish_plan(payload, target_total=target_total)
    _progress("publish_plan", "completed", decision=initial.get("decision"))
    final = initial

    if final["decision"] != "publish" and not args.no_named_topics and _should_collect_named_topics(final):
        triggered_actions.append("collect_named_topics")
        _progress("collect_named_topics", "started", mode=args.collect_mode)
        named_topic_summary = await _run_named_topic_collect(mode=args.collect_mode)
        _progress("collect_named_topics", "completed", summary=named_topic_summary)
        _progress("post_named_topic_sync", "started")
        sync_runs.append({"step": "post_named_topic_sync", "summary": sync_topic_metadata()})
        _progress("post_named_topic_sync", "completed", summary=sync_runs[-1]["summary"])
        payload = _write_plan(target_total, scope=collect_scope, output_path=args.output_plan)
        final = evaluate_publish_plan(payload, target_total=target_total)
        _progress("publish_plan", "completed", decision=final.get("decision"))

    if (
        final["decision"] == "publish"
        and int(final.get("actual_total") or 0) > 0
        and not args.no_named_topics
    ):
        governance_watches = build_governance_topic_watches_for_gate(
            plan_payload=payload,
            gate_summary=final,
            scope_id=collect_scope,
        )
        if governance_watches:
            triggered_actions.append("collect_governance_topics")
            _progress("collect_governance_topics", "started", count=len(governance_watches))
            governance_collect_summary = await _run_named_topic_collect(mode=args.collect_mode, watches=governance_watches)
            _progress("collect_governance_topics", "completed", summary=governance_collect_summary)
            _progress("post_governance_collect_sync", "started")
            sync_runs.append({"step": "post_governance_collect_sync", "summary": sync_topic_metadata()})
            _progress("post_governance_collect_sync", "completed", summary=sync_runs[-1]["summary"])
            governance_preview_payload = _write_plan(target_total, scope=collect_scope, output_path=None)
            governance_preview = evaluate_publish_plan(governance_preview_payload, target_total=target_total)
            _progress("governance_preview", "completed", decision=governance_preview.get("decision"))

    summary = {
        "workflow": "reddit-signal-scanner-intake-freshness-gate",
        "target_total": target_total,
        "scope": collect_scope,
        "output_plan": str(args.output_plan) if args.output_plan else None,
        "triggered_actions": triggered_actions,
        "sync_runs": sync_runs,
        "initial": initial,
        "final": final,
        "daily_collect_summary": collect_summary,
        "named_topic_collect_summary": named_topic_summary,
        "governance_collect_summary": governance_collect_summary,
        "governance_preview": governance_preview,
        "publish_ready": final["decision"] == "publish" and int(final.get("actual_total") or 0) > 0,
    }
    return summary


def _write_plan(target_total: int, *, scope: str | None, output_path: Path | None) -> dict[str, Any]:
    payload = build_offline_publish_plan(
        limit=target_total,
        scope=scope,
    )
    if output_path is not None:
        text = json.dumps(payload, ensure_ascii=False, indent=2)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(text, encoding="utf-8")
    return payload


async def _run_daily_collect(*, mode: str, scope: str | None) -> dict[str, int]:
    collect_defaults = get_supply_collect_profile(mode)
    return await run_quota_aware_collect(
        scope=scope,
        mode=mode,
        max_candidates=collect_defaults["max_candidates_per_scope"],
        dry_cycle_limit=int(collect_defaults.get("dry_cycle") or 3),
    )


async def _run_named_topic_collect(*, mode: str, watches=None) -> dict[str, Any]:
    resolved_watches = (
        list(watches)
        if watches is not None
        else resolve_named_topic_watchlist(preset=get_default_named_topic_preset())
    )
    items = await collect_named_topic_candidates(resolved_watches, mode=mode, persist=True)
    return {
        "watch_count": len(resolved_watches),
        "candidate_count": len(items),
        "candidate_ids": [item.candidate_id for item in items],
        "topic_ids": [getattr(item, "topic_id", None) for item in resolved_watches],
    }


def _should_collect_named_topics(summary: dict[str, Any]) -> bool:
    return should_escalate_named_topic_collect(
        decision=str(summary.get("decision") or "publish"),
        rewrite_reasons=list(summary.get("rewrite_reasons") or []),
        fail_reasons=list(summary.get("fail_reasons") or []),
        lane_counts=dict(summary.get("lane_counts") or {}),
        candidate_freshness_by_lane=dict(summary.get("candidate_freshness_by_lane") or {}),
    )


def _progress(stage: str, status: str, **extra: object) -> None:
    print(
        json.dumps({"stage": stage, "status": status, **extra}, ensure_ascii=False),
        file=sys.stderr,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run one collect-until-exhausted -> sync -> plan -> freshness gate cycle before publish."
    )
    parser.add_argument("--limit", type=int, default=None, help="Publish window size. Defaults to operation default.")
    parser.add_argument("--scope", default=None, help="Restrict collect to a single scope. Omit to use the product default: all-scope.")
    parser.add_argument("--all-scope", action="store_true", help="Explicitly collect every configured scope before gating.")
    parser.add_argument(
        "--output-plan",
        type=Path,
        default=Path("backend/tmp/offline-publish-plan.json"),
        help="Path to write the current offline publish plan JSON.",
    )
    parser.add_argument("--summary-json", type=Path, default=None, help="Optional path to write the gate summary JSON.")
    parser.add_argument("--collect-mode", choices=["safe", "harvest"], default="safe")
    parser.add_argument("--no-collect", action="store_true", help="Skip the regular collect rerun even if the gate fails.")
    parser.add_argument("--no-named-topics", action="store_true", help="Skip named-topic escalation even if the gate still fails.")
    args = parser.parse_args()

    summary = asyncio.run(_run(args))
    text = json.dumps(summary, ensure_ascii=False, indent=2)
    if args.summary_json is not None:
        args.summary_json.parent.mkdir(parents=True, exist_ok=True)
        args.summary_json.write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
