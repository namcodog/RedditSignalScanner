from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.hotpost.offline_publish_plan import build_offline_publish_plan


def _build_scope_summaries(governance: dict[str, object]) -> dict[str, dict[str, str]]:
    summaries: dict[str, dict[str, str]] = {}
    for scope_id, scope_payload in dict((governance.get("scopes") or {})).items():
        scope_data = dict(scope_payload or {})
        summaries[str(scope_id)] = {
            "overall_decision": str(scope_data.get("overall_decision") or "publish"),
            "allocation": str(dict(scope_data.get("allocation") or {}).get("decision") or "publish"),
            "rotation": str(dict(scope_data.get("rotation") or {}).get("decision") or "publish"),
            "supply": str(dict(scope_data.get("supply") or {}).get("decision") or "publish"),
            "source_health": str(dict(scope_data.get("source_health") or {}).get("decision") or "publish"),
        }
    return summaries

def main() -> None:
    parser = argparse.ArgumentParser(description="Audit topic-tree governance for the current publish plan.")
    parser.add_argument("--limit", type=int, default=None, help="Optional publish window size override.")
    parser.add_argument("--scope", default=None, help="Audit one scope only. Omit to use the product default: all-scope.")
    parser.add_argument("--all-scope", action="store_true", help="Explicitly audit all scopes together.")
    parser.add_argument("--output", type=Path, default=None, help="Optional path to write JSON output.")
    args = parser.parse_args()

    payload = build_offline_publish_plan(
        limit=args.limit,
        scope=None if args.all_scope else args.scope,
    )
    governance = payload.get("topic_tree_governance") or {}
    audit = {
        "generated_at": payload.get("generated_at"),
        "scope": payload.get("scope"),
        "overall_decision": (governance.get("overall_decision") or "publish"),
        "scope_summaries": _build_scope_summaries(governance),
        "topic_tree_governance": governance,
    }
    text = json.dumps(audit, ensure_ascii=False, indent=2)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
