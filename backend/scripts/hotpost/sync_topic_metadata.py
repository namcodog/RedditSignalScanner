from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.hotpost.card_payload_store import mutate_cards_payload
from app.services.hotpost.topic_metadata import build_candidate_metadata_lookup, resolve_topic_metadata


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill topic metadata into local hotpost payload buckets.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON summary.")
    args = parser.parse_args()
    summary = sync_topic_metadata()
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return
    for bucket in ("candidates", "drafts", "published"):
        info = summary[bucket]
        print(
            f"{bucket}: changed={info['changed_items']} "
            f"pack={info['with_topic_pack_id']} "
            f"cluster={info['with_topic_cluster_id']} "
            f"named={info['with_named_topic_ids']}"
        )


def sync_topic_metadata() -> dict[str, Any]:
    def _mutate(payload: dict[str, Any]) -> dict[str, Any]:
        candidates = [dict(item) for item in list(payload.get("candidates") or [])]
        candidate_summary = _sync_bucket(candidates, candidate_lookup={})
        payload["candidates"] = candidates

        candidate_lookup = build_candidate_metadata_lookup(candidates)
        drafts = [dict(item) for item in list(payload.get("drafts") or [])]
        drafts_summary = _sync_bucket(drafts, candidate_lookup=candidate_lookup)
        payload["drafts"] = drafts

        published = [dict(item) for item in list(payload.get("published") or [])]
        published_summary = _sync_bucket(published, candidate_lookup=candidate_lookup)
        payload["published"] = published

        return {
            "candidates": candidate_summary,
            "drafts": drafts_summary,
            "published": published_summary,
        }

    return mutate_cards_payload(_mutate)


def _sync_bucket(items: list[dict[str, Any]], *, candidate_lookup: dict[str, dict[str, Any]]) -> dict[str, int]:
    changed_items = 0
    for item in items:
        metadata = resolve_topic_metadata(item, candidate_lookup=candidate_lookup)
        changed = False
        for field_name, value in metadata.items():
            if item.get(field_name) == value:
                continue
            item[field_name] = value
            changed = True
        if changed:
            changed_items += 1
    return {
        "total": len(items),
        "changed_items": changed_items,
        "with_topic_pack_id": sum(1 for item in items if item.get("topic_pack_id")),
        "with_topic_cluster_id": sum(1 for item in items if item.get("topic_cluster_id")),
        "with_named_topic_ids": sum(1 for item in items if list(item.get("named_topic_ids") or [])),
    }


if __name__ == "__main__":
    main()
