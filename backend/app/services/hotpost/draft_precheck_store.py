from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


_ROOT = Path(__file__).resolve().parents[4] / "reports" / "hotpost-draft-precheck"


def draft_precheck_path(draft_id: str) -> Path:
    safe_id = re.sub(r"[^A-Za-z0-9_.-]+", "-", draft_id).strip(".-")
    if not safe_id:
        raise ValueError("draft_id is required")
    return _ROOT / f"{safe_id}.json"


def save_draft_precheck(draft_id: str, payload: dict[str, Any]) -> Path:
    path = draft_precheck_path(draft_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def load_draft_precheck(draft_id: str) -> dict[str, Any] | None:
    path = draft_precheck_path(draft_id)
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else None


__all__ = ["draft_precheck_path", "load_draft_precheck", "save_draft_precheck"]
