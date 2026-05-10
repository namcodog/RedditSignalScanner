from __future__ import annotations

import argparse
import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.scripts_support.env_loader import load_backend_env
from app.services.hotpost.signal_cli_shadow import (
    build_signal_api_shadow_client_factory,
    build_signal_cli_shadow_client_factory,
    build_signal_codex_shadow_client_factory,
    generate_signal_shadow_from_candidate,
    load_signal_shadow_candidates,
    write_signal_shadow_jsonl,
)


def _default_output_path() -> Path:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return ROOT / "tmp" / f"signal-shadow-compare-{ts}.jsonl"


def _score_flags(row: dict[str, object]) -> list[str]:
    flags: list[str] = []
    title = str(row.get("title") or "")
    summary = str(row.get("summary_line") or "")
    audience = str(row.get("audience") or "")
    why_now = str(row.get("why_now") or "")
    detail = row.get("detail") or {}
    why_test_now = ""
    if isinstance(detail, dict):
        why_test_now = str(detail.get("why_test_now") or "")

    full = "\n".join([title, summary, audience, why_now, why_test_now])
    if "..." in full:
        flags.append("ellipsis")
    if "原话里有个关键句" in full or "翻过来就是" in full:
        flags.append("translationese")
    if "尤其是" in audience or "特别是那些" in audience:
        flags.append("audience_tail")
    return flags


async def _run(args: argparse.Namespace) -> dict[str, object]:
    candidates = load_signal_shadow_candidates(
        snapshot_id=args.snapshot_id,
        candidate_ids=args.candidate_id or None,
        limit=args.limit,
    )
    api_factory = build_signal_api_shadow_client_factory()
    cli_factory = build_signal_cli_shadow_client_factory(
        model=args.cli_model,
        cwd=ROOT.parent,
        min_timeout_seconds=args.timeout_seconds,
    )
    codex_factory = (
        build_signal_codex_shadow_client_factory(
            model=args.codex_model,
            cwd=ROOT.parent,
            min_timeout_seconds=args.timeout_seconds,
        )
        if args.codex_model
        else None
    )
    rows: list[dict[str, object]] = []
    for candidate in candidates:
        api_row = await generate_signal_shadow_from_candidate(candidate, client_factory=api_factory)
        cli_row = await generate_signal_shadow_from_candidate(candidate, client_factory=cli_factory)
        codex_row = (
            await generate_signal_shadow_from_candidate(candidate, client_factory=codex_factory)
            if codex_factory is not None
            else None
        )
        rows.append(
            {
                "candidate_id": candidate.candidate_id,
                "source_scope_id": candidate.source_scope_id,
                "source_scope_name": candidate.source_scope_name,
                "topic_pack_id": candidate.topic_pack_id,
                "api_v6": api_row,
                "api_flags": _score_flags(api_row),
                "cli_v6": cli_row,
                "cli_flags": _score_flags(cli_row),
                "codex_v6": codex_row,
                "codex_flags": _score_flags(codex_row) if isinstance(codex_row, dict) else [],
            }
        )

    output_path = Path(args.output_jsonl).expanduser().resolve()
    write_signal_shadow_jsonl(output_path, rows)
    return {
        "snapshot_id": args.snapshot_id or "latest",
        "candidate_count": len(candidates),
        "generated_count": len(rows),
        "cli_model": args.cli_model,
        "codex_model": args.codex_model,
        "timeout_seconds": args.timeout_seconds,
        "output_jsonl": str(output_path),
    }


def main() -> None:
    load_backend_env()
    parser = argparse.ArgumentParser(description="Compare signal API v6 and Gemini CLI v6 on the same review queue snapshot")
    parser.add_argument("--snapshot-id")
    parser.add_argument("--candidate-id", action="append", default=[])
    parser.add_argument("--limit", type=int, default=3)
    parser.add_argument("--cli-model", default="gemini-3.1-pro-preview")
    parser.add_argument("--codex-model", default="")
    parser.add_argument("--timeout-seconds", type=float, default=180.0)
    parser.add_argument("--output-jsonl", default=str(_default_output_path()))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    summary = asyncio.run(_run(args))
    if args.json:
        print(json.dumps(summary, ensure_ascii=False))
        return
    print(
        "signal-shadow-compare "
        f"cli_model={summary['cli_model']} generated={summary['generated_count']} output={summary['output_jsonl']}"
    )


if __name__ == "__main__":
    main()
