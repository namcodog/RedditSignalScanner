from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
import sys

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.scripts_support.env_loader import load_backend_env
from app.services.hotpost.workflow_dry_run import run_hotpost_workflow_dry_run


async def main() -> None:
    load_backend_env()
    parser = argparse.ArgumentParser(description="Hotpost workflow dry-run")
    parser.add_argument("--mode", choices=["safe", "harvest"], default="harvest")
    parser.add_argument("--max-candidates", type=int, default=None)
    parser.add_argument("--queue-limit", type=int, default=None)
    parser.add_argument("--materialize-limit", type=int, default=None)
    args = parser.parse_args()
    payload = await run_hotpost_workflow_dry_run(
        max_candidates=args.max_candidates,
        queue_limit=args.queue_limit,
        materialize_limit=args.materialize_limit,
        mode=args.mode,
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
