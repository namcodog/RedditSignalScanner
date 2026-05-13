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
    build_signal_cli_shadow_client_factory,
    generate_signal_shadow_from_candidate,
    load_signal_shadow_candidates,
    write_signal_shadow_jsonl,
)


def _default_output_path() -> Path:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return ROOT / "tmp" / f"signal-cli-shadow-{ts}.jsonl"


async def _run(args: argparse.Namespace) -> dict[str, object]:
    candidates = load_signal_shadow_candidates(
        snapshot_id=args.snapshot_id,
        candidate_ids=args.candidate_id or None,
        limit=args.limit,
    )
    rows = [
        await generate_signal_shadow_from_candidate(
            candidate,
            client_factory=build_signal_cli_shadow_client_factory(
                model=args.model,
                cwd=ROOT.parent,
                min_timeout_seconds=args.timeout_seconds,
            ),
        )
        for candidate in candidates
    ]
    output_path = Path(args.output_jsonl).expanduser().resolve()
    write_signal_shadow_jsonl(output_path, rows)
    return {
        "snapshot_id": args.snapshot_id or "latest",
        "candidate_count": len(candidates),
        "generated_count": len(rows),
        "model": args.model,
        "timeout_seconds": args.timeout_seconds,
        "output_jsonl": str(output_path),
    }


def main() -> None:
    load_backend_env()
    parser = argparse.ArgumentParser(description="Run signal shadow generation through Gemini CLI without touching publish chain")
    parser.add_argument("--snapshot-id")
    parser.add_argument("--candidate-id", action="append", default=[])
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--model", default="gemini-3.1-pro-preview")
    parser.add_argument("--timeout-seconds", type=float, default=180.0)
    parser.add_argument("--output-jsonl", default=str(_default_output_path()))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    summary = asyncio.run(_run(args))
    if args.json:
        print(json.dumps(summary, ensure_ascii=False))
        return
    print(f"signal-cli-shadow model={summary['model']} generated={summary['generated_count']} output={summary['output_jsonl']}")


if __name__ == "__main__":
    main()
