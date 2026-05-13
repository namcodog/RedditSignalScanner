from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.hotpost.offline_publish_plan import build_offline_publish_plan

def main() -> None:
    parser = argparse.ArgumentParser(description="Build today's publish list from local hotpost inventory only.")
    parser.add_argument("--limit", type=int, default=None, help="Maximum number of planned cards.")
    parser.add_argument("--scope", default=None, help="Restrict plan building to one scope. Omit to use the product default: all-scope.")
    parser.add_argument("--all-scope", action="store_true", help="Explicitly build plan across every scope.")
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional path to write JSON output.",
    )
    args = parser.parse_args()
    payload = build_offline_publish_plan(
        limit=args.limit,
        scope=None if args.all_scope else args.scope,
    )
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
