from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = ROOT.parent
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from app.services.community.community_pool_phase1_planner import build_phase1_plan
from scripts.community.community_governance_audit import run_audit

DEFAULT_JSON_OUTPUT = PROJECT_ROOT / "reports" / "community-governance" / "phase1-dry-run.json"
DEFAULT_MD_OUTPUT = PROJECT_ROOT / "reports" / "community-governance" / "phase1-dry-run.md"


def format_ratio(value: float) -> str:
    return f"{value:.0%}"


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    review = summary["review_only"]
    cap_policy = summary["generic_cap_policy"]
    lines = [
        "# Phase 1 Community Pool Dry-Run",
        "",
        "- DB writes: `false`",
        f"- existing_evidence_communities: `{summary['existing_evidence_communities']}`",
        f"- proposed_pool_additions: `{summary['proposed_pool_additions']}`",
        f"- keep_pool_unchanged: `{summary['keep_pool_unchanged']}`",
        f"- generic_cap_required: `{summary['generic_cap_required']}`",
        (
            "- review_only: "
            f"`needs_evidence={review['needs_evidence']} / "
            f"stale_review={review['stale_review']} / "
            f"observation_queue={review['observation_queue']}`"
        ),
        "",
        "## Generic Community Budget",
        "",
        f"- regular_learning_cap_ratio: `{format_ratio(cap_policy['regular_learning_cap_ratio'])}`",
        (
            "- max_cap_ratio_without_human_review: "
            f"`{format_ratio(cap_policy['max_cap_ratio_without_human_review'])}`"
        ),
        f"- current_generic_ratio: `{format_ratio(cap_policy['current_generic_ratio'])}`",
        "- hot_floor: `enabled`",
        (
            "- allowed_cap_bypass_reason: "
            f"`{cap_policy['allowed_cap_bypass_reason']}`"
        ),
        "- must-have hot signals bypass the regular generic cap, but only for hot signal coverage.",
        "",
        "## Existing Evidence Rows",
        "",
        "| Community | Source State | Phase 1 Action | Role | Cap | Cards |",
        "|---|---|---|---|---|---:|",
    ]
    for row in payload["rows"]:
        evidence = row.get("evidence") or {}
        lines.append(
            "| "
            + row["community"]
            + " | "
            + row["source_state"]
            + " | "
            + row["phase1_action"]
            + " | "
            + row["role"]
            + " | "
            + ("Y" if row["cap_required"] else "N")
            + " | "
            + str(evidence.get("hotpost_card_count", 0))
            + " |"
        )
    lines.extend(
        [
            "",
            "## Write Gate",
            "",
            "This report is a dry-run gate. It does not authorize DB writes.",
            "A later write step needs explicit human approval and a row-level rollback plan.",
        ]
    )
    future_write = payload.get("future_write_preview") or {}
    fields = future_write.get("fields_requiring_future_approval") or []
    lines.extend(
        [
            f"- would_insert_pool_rows: `{future_write.get('would_insert_pool_rows', 0)}`",
            f"- would_update_pool_rows: `{future_write.get('would_update_pool_rows', 0)}`",
            f"- fields_requiring_future_approval: `{', '.join(fields)}`",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


async def build() -> dict[str, Any]:
    return build_phase1_plan(await run_audit())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate community pool Phase 1 dry-run reports.")
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON_OUTPUT)
    parser.add_argument("--md-output", type=Path, default=DEFAULT_MD_OUTPUT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = asyncio.run(build())
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    args.md_output.write_text(render_markdown(payload), encoding="utf-8")
    print(json.dumps(payload["summary"], ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
