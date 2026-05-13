from __future__ import annotations

import json
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

ROOT = Path(__file__).resolve().parents[4]
REVIEW_REJECTIONS_PATH = ROOT / "backend/data/hotpost/review_rejections.json"


def load_review_rejections() -> dict[str, dict[str, Any]]:
    if not REVIEW_REJECTIONS_PATH.exists():
        return {}
    return json.loads(REVIEW_REJECTIONS_PATH.read_text(encoding="utf-8"))


def list_rejected_candidate_ids() -> set[str]:
    return set(load_review_rejections().keys())


def save_review_rejection(candidate_id: str, *, reason: str, note: str = "") -> dict[str, Any]:
    payload = load_review_rejections()
    payload[candidate_id] = {
        "candidate_id": candidate_id,
        "reason": reason.strip(),
        "note": note.strip(),
    }
    _atomic_write(payload)
    return payload[candidate_id]


def _atomic_write(payload: dict[str, dict[str, Any]]) -> None:
    REVIEW_REJECTIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=REVIEW_REJECTIONS_PATH.parent,
        delete=False,
    ) as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        temp_path = Path(handle.name)
    temp_path.replace(REVIEW_REJECTIONS_PATH)
