from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence

from app.schemas.hotpost_card_candidates import CandidatePack
from app.schemas.hotpost_signal import SourceScopeId


_ROOT = Path(__file__).resolve().parents[3] / "data" / "hotpost" / "experimental_candidates"


def experimental_candidates_root() -> Path:
    return _ROOT


def experimental_scope_path(scope_id: SourceScopeId | str) -> Path:
    return experimental_candidates_root() / f"{scope_id}.json"


def load_experimental_candidates(source_scope_id: SourceScopeId | str | None = None) -> list[dict[str, Any]]:
    if source_scope_id is not None:
        return _read_json_list_if_exists(experimental_scope_path(source_scope_id))
    root = experimental_candidates_root()
    if not root.exists():
        return []
    items: list[dict[str, Any]] = []
    for path in sorted(root.glob("*.json")):
        items.extend(_read_json_list_if_exists(path))
    return items


def replace_experimental_scope_candidates(
    source_scope_id: SourceScopeId | str,
    candidates: Sequence[CandidatePack | Mapping[str, Any]],
) -> dict[str, Any]:
    rows = [
        item.model_dump(mode="json") if hasattr(item, "model_dump") else dict(item)
        for item in candidates
    ]
    path = experimental_scope_path(source_scope_id)
    _atomic_write_json(path, rows)
    return {
        "path": str(path),
        "scope_id": str(source_scope_id),
        "candidate_count": len(rows),
    }


def _read_json_list_if_exists(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError(f"Expected JSON list: {path}")
    rows: list[dict[str, Any]] = []
    for item in payload:
        if not isinstance(item, dict):
            raise ValueError(f"Expected JSON object items: {path}")
        rows.append(item)
    return rows


def _atomic_write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        delete=False,
    ) as temp_file:
        json.dump(payload, temp_file, ensure_ascii=False, indent=2)
        temp_file.write("\n")
        temp_name = temp_file.name
    os.replace(temp_name, path)


__all__ = [
    "experimental_candidates_root",
    "experimental_scope_path",
    "load_experimental_candidates",
    "replace_experimental_scope_candidates",
]
