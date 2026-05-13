from __future__ import annotations

from typing import Any, Mapping


def render_r12_prewrite_markdown(payload: Mapping[str, Any]) -> str:
    summary = _mapping(payload.get("summary"), "summary")
    lines = [
        "# Hotpost Community Pool R12 Prewrite Audit",
        "",
        "- DB writes: `false`",
        "- auto_promote: `false`",
        f"- input_rows: `{summary['input_rows']}`",
        f"- candidate_rows: `{summary['candidate_rows']}`",
        f"- would_insert: `{summary['would_insert']}`",
        f"- skipped_existing: `{summary['skipped_existing']}`",
        f"- blocked: `{summary['blocked']}`",
        "",
        "| Community | Action | Scope | Topic Cluster | Score | Tags | Evidence | Label Review | Risks |",
        "|---|---|---|---|---:|---|---:|---|---|",
    ]
    for row in _rows(payload):
        value = _mapping(row.get("value_assessment"), "row.value_assessment")
        evidence = _mapping(row.get("evidence"), "row.evidence")
        preview = _mapping(row.get("write_preview"), "row.write_preview")
        lines.append(
            "| "
            + str(row["community"])
            + " | "
            + str(preview["action"])
            + " | "
            + str(row["source_scope"])
            + " | "
            + str(row["topic_cluster"])
            + " | "
            + str(value["score"])
            + " | "
            + ", ".join(list(row.get("suggested_user_tags") or []))
            + " | "
            + str(evidence["total_evidence"])
            + " | "
            + str(row["label_review"])
            + " | "
            + ", ".join(list(row.get("risks") or []))
            + " |"
        )
    return "\n".join(lines).rstrip() + "\n"


def _rows(payload: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    rows = payload.get("rows")
    if not isinstance(rows, list):
        raise ValueError("payload rows must be a list")
    return [row for row in rows if isinstance(row, Mapping)]


def _mapping(value: object, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{field} must be an object")
    return value


__all__ = ["render_r12_prewrite_markdown"]
