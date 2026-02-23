#!/usr/bin/env python3
"""
Generate a standalone analysis JSON for a given product description.

Usage:
    python backend/scripts/generate_analysis_json.py "<product_description>" [--outfile path]

This runs the analysis engine against live Reddit (cache-first) when
REDDIT_CLIENT_ID/SECRET are configured in backend/.env and writes a
compact JSON file with insights, sources and key metadata.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

try:
    # Load backend/.env so run_analysis can access Reddit credentials
    from dotenv import load_dotenv  # type: ignore
    load_dotenv(dotenv_path=Path(__file__).parents[1] / ".env")
except Exception:
    pass

from app.schemas.task import TaskStatus, TaskSummary
from app.services.analysis_engine import run_analysis


def _now() -> datetime:
    return datetime.now(timezone.utc)


def generate(description: str) -> dict[str, Any]:
    # Build a minimal TaskSummary for the engine (no DB writes)
    summary = TaskSummary(
        id=uuid4(),
        status=TaskStatus.PROCESSING,
        product_description=description,
        created_at=_now(),
        updated_at=_now(),
        completed_at=None,
        retry_count=0,
        failure_category=None,
    )

    result = __import__("asyncio").get_event_loop().run_until_complete(run_analysis(summary))
    payload: dict[str, Any] = {
        "task_id": str(summary.id),
        "description": description,
        "generated_at": _now().isoformat(),
        "insights": result.insights,
        "sources": result.sources,
    }
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate analysis JSON from description")
    parser.add_argument("description", help="Product description text")
    parser.add_argument("--outfile", dest="outfile", help="Output JSON file path", default=None)
    args = parser.parse_args()

    output = generate(args.description)
    out_path = (
        Path(args.outfile)
        if args.outfile
        else Path("backend/reports") / f"analysis-output-{output['task_id']}.json"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output, ensure_ascii=False, indent=2))
    print(str(out_path))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
