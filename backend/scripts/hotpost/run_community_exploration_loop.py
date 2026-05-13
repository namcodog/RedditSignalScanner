from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = ROOT.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.db.session import SessionFactory
from app.scripts_support.env_loader import load_backend_env
from app.services.hotpost.community_exploration_orchestrator import (
    parse_probe_arg,
    run_exploration_post_stage,
    run_exploration_pre_stage,
)
from app.services.hotpost.community_pool_feedback_dry_run import (
    load_active_pool_community_keys,
)
from app.services.hotpost.community_pool_feedback_markdown import (
    render_pool_feedback_markdown,
)


async def _run(args: argparse.Namespace) -> dict[str, Any]:
    if args.stage == "pre":
        return await run_exploration_pre_stage(
            probes=[parse_probe_arg(item) for item in args.probe],
            report_date=args.date,
        )
    async with SessionFactory() as session:
        pool_keys = await load_active_pool_community_keys(session)
    return await run_exploration_post_stage(
        report_date=args.date, pool_community_keys=pool_keys
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Hotpost community exploration pre/post loop."
    )
    parser.add_argument("--stage", choices=["pre", "post"], required=True)
    parser.add_argument(
        "--date",
        default=None,
        help="Report date in YYYY-MM-DD format. Defaults to today.",
    )
    parser.add_argument(
        "--probe",
        action="append",
        default=[],
        help="scope[:max_candidates[:direction]]",
    )
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument(
        "--skip-standard-reports",
        action="store_true",
        help="Only write --output. Intended for smoke tests.",
    )
    args = parser.parse_args()
    if args.stage == "pre" and not args.probe:
        parser.error(
            "--stage pre requires at least one --probe scope[:max_candidates[:direction]]"
        )
    return args


def main() -> None:
    load_backend_env()
    args = parse_args()
    payload = asyncio.run(_run(args))
    output = args.output or (
        PROJECT_ROOT
        / "reports"
        / "community-governance"
        / f"community-exploration-{payload['stage']}-{payload['report_date']}.json"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    standard_reports = (
        _write_standard_reports(payload)
        if args.stage == "post" and not args.skip_standard_reports
        else {}
    )
    if standard_reports:
        payload["standard_reports"] = standard_reports
        output.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    print(
        json.dumps(
            {"output": str(output), "summary": payload["summary"]},
            ensure_ascii=False,
            sort_keys=True,
        )
    )


def _write_standard_reports(payload: dict[str, Any]) -> dict[str, str]:
    report_date = str(payload["report_date"])
    report_dir = PROJECT_ROOT / "reports" / "community-governance"
    report_dir.mkdir(parents=True, exist_ok=True)
    audit_path = report_dir / f"community-discovery-audit-{report_date}.json"
    feedback_json_path = (
        report_dir / f"community-pool-feedback-dry-run-{report_date}.json"
    )
    feedback_md_path = report_dir / f"community-pool-feedback-dry-run-{report_date}.md"
    audit_path.write_text(
        json.dumps(payload["audit"], ensure_ascii=False, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    feedback = dict(payload["feedback"])
    feedback_json_path.write_text(
        json.dumps(feedback, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    feedback_md_path.write_text(
        render_pool_feedback_markdown(feedback), encoding="utf-8"
    )
    return {
        "audit_json": str(audit_path),
        "feedback_json": str(feedback_json_path),
        "feedback_md": str(feedback_md_path),
    }


if __name__ == "__main__":
    main()
