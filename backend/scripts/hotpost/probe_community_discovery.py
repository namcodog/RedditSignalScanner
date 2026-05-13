from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
import sys
from typing import Any, Mapping, cast

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.scripts_support.env_loader import load_backend_env
from app.schemas.hotpost_signal import SourceScopeId
from app.services.hotpost.community_probe_collect import collect_experimental_scope_probe
from app.services.hotpost.hotpost_supply_contract import get_supply_collect_profile


async def _run(*, scope: str, mode: str, max_candidates: int | None) -> dict[str, object]:
    return await collect_experimental_scope_probe(
        cast(SourceScopeId, scope),
        mode=mode,
        max_candidates=max_candidates,
    )


def main() -> None:
    load_backend_env()
    collect_defaults = get_supply_collect_profile("safe")
    parser = argparse.ArgumentParser(description="Probe Hotpost experimental communities explicitly.")
    parser.add_argument("--scope", required=True, help="Source scope to probe.")
    parser.add_argument("--mode", choices=["safe", "harvest"], default="safe")
    parser.add_argument("--max-candidates", type=int, default=collect_defaults["max_candidates_per_scope"])
    args = parser.parse_args()
    summary = asyncio.run(_run(scope=args.scope, mode=args.mode, max_candidates=args.max_candidates))
    print(json.dumps(_jsonable_summary(summary), ensure_ascii=False, indent=2))


def _jsonable_summary(summary: Mapping[str, object]) -> dict[str, object]:
    raw_items = summary.get("items")
    items = raw_items if isinstance(raw_items, list) else []
    payload = {key: value for key, value in summary.items() if key != "items"}
    payload["item_count"] = len(items)
    store = summary.get("experimental_candidate_store")
    if isinstance(store, Mapping):
        payload["experimental_candidate_path"] = _json_scalar(store.get("path"))
        payload["experimental_candidate_count"] = _json_scalar(store.get("candidate_count"))
    payload["items"] = [_candidate_output(item) for item in items]
    return payload


def _candidate_output(item: object) -> dict[str, object]:
    raw = item.model_dump(mode="json") if hasattr(item, "model_dump") else item
    if not isinstance(raw, Mapping):
        return {"value": str(raw)}
    keys = (
        "candidate_id",
        "source_scope_id",
        "topic_pack_id",
        "topic_cluster_id",
        "matched_subreddit",
        "title",
    )
    return {key: _json_scalar(raw.get(key)) for key in keys if raw.get(key) is not None}


def _json_scalar(value: Any) -> object:
    if isinstance(value, str | int | float | bool) or value is None:
        return value
    return str(value)


if __name__ == "__main__":
    main()
