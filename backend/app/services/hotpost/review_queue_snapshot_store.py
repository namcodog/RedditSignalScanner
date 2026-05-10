from __future__ import annotations

import json
import os
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Any

from app.schemas.hotpost_card_candidates import CandidatePack


_SNAPSHOT_ROOT = Path(__file__).resolve().parents[3] / "data" / "hotpost" / "review_queue"
_SNAPSHOTS_DIR = _SNAPSHOT_ROOT / "snapshots"
_LATEST_PATH = _SNAPSHOT_ROOT / "latest.json"


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=path.parent,
        suffix=".tmp",
        delete=False,
    ) as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.flush()
        os.fsync(handle.fileno())
        temp_name = handle.name
    os.replace(temp_name, path)


def write_review_queue_snapshot(
    *,
    card_type:Optional[ str],
    scope:Optional[ str],
    level:Optional[ str],
    limit: int,
    candidates: list[CandidatePack],
) -> str:
    snapshot_id = f"queue-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8]}"
    payload = {
        "snapshot_id": snapshot_id,
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "card_type": card_type,
        "scope": scope,
        "level": level,
        "limit": limit,
        "candidate_count": len(candidates),
        "candidates": [item.model_dump(mode="json") for item in candidates],
    }
    _atomic_write_json(_SNAPSHOTS_DIR / f"{snapshot_id}.json", payload)
    _atomic_write_json(_LATEST_PATH, {"snapshot_id": snapshot_id})
    return snapshot_id


def load_review_queue_snapshot(snapshot_id:Optional[ str] = None) -> dict[str, Any]:
    resolved_id = snapshot_id
    if resolved_id is None:
        if not _LATEST_PATH.exists():
            raise LookupError("No review queue snapshot found. Run `review_cards.py queue` first.")
        resolved_id = str(json.loads(_LATEST_PATH.read_text(encoding="utf-8"))["snapshot_id"])
    path = _SNAPSHOTS_DIR / f"{resolved_id}.json"
    if not path.exists():
        raise LookupError(f"Review queue snapshot not found: {resolved_id}")
    return json.loads(path.read_text(encoding="utf-8"))


def get_snapshot_candidate(candidate_id: str, snapshot_id:Optional[ str] = None) -> CandidatePack:
    payload = load_review_queue_snapshot(snapshot_id)
    item = next((entry for entry in payload.get("candidates", []) if entry["candidate_id"] == candidate_id), None)
    if item is None:
        raise LookupError(
            f"Candidate `{candidate_id}` not found in review queue snapshot `{payload['snapshot_id']}`. Re-run `review_cards.py queue`."
        )
    return CandidatePack.model_validate(item)


__all__ = [
    "get_snapshot_candidate",
    "load_review_queue_snapshot",
    "write_review_queue_snapshot",
]
