from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


_ROOT = Path(__file__).resolve().parents[4] / "reports" / "hotpost-generation-traces"


def generation_trace_path(trace_id: str) -> Path:
    safe_id = re.sub(r"[^A-Za-z0-9_.-]+", "-", trace_id).strip(".-")
    if not safe_id:
        raise ValueError("trace_id is required")
    return _ROOT / f"{safe_id}.json"


def save_generation_trace(trace_id: str, payload: dict[str, Any]) -> Path:
    path = generation_trace_path(trace_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def load_generation_trace(trace_id: str) -> dict[str, Any] | None:
    path = generation_trace_path(trace_id)
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else None


__all__ = ["generation_trace_path", "load_generation_trace", "save_generation_trace"]
