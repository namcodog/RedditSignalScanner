from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.services.llm.comment_label_planner import (
    interleave_selected_rows_by_domain as _service_interleave_selected_rows_by_domain,
)


def truncate_text(text: str, limit: int) -> str:
    if not text:
        return ""
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)] + "..."


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=True) + "\n")


def comment_payload_from_row(
    row: dict[str, Any],
    *,
    max_body_chars: int,
) -> dict[str, Any]:
    return {
        "task_type": "comment_label",
        "id": int(row.get("id")),
        "subreddit": str(row.get("subreddit") or ""),
        "post_title": truncate_text(str(row.get("post_title") or ""), max_body_chars),
        "comment_body": truncate_text(str(row.get("body") or ""), max_body_chars),
        "domain": str(row.get("domain") or ""),
        "business_pool": str(row.get("business_pool") or "unscored"),
    }


def interleave_selected_rows_by_domain(
    rows_by_domain: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    return _service_interleave_selected_rows_by_domain(rows_by_domain)


__all__ = [
    "comment_payload_from_row",
    "interleave_selected_rows_by_domain",
    "truncate_text",
    "write_jsonl",
]
