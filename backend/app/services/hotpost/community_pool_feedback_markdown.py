from __future__ import annotations

from typing import Any, Mapping


def render_pool_feedback_markdown(payload: Mapping[str, Any]) -> str:
    summary = _mapping(payload.get("summary"), "summary")
    lines = [
        "# Hotpost Community Pool Feedback Dry-Run",
        "",
        "- DB writes: `false`",
        "- auto_promote: `false`",
        f"- input_rows: `{summary['input_rows']}`",
        f"- already_in_pool: `{summary['already_in_pool']}`",
        f"- promote_candidate: `{summary['promote_candidate']}`",
        f"- keep_testing: `{summary['keep_testing']}`",
        f"- reject: `{summary['reject']}`",
        "",
        "| Community | Scope | Topic Cluster | Action | Value Stage | Score | Tags | Evidence | Risks |",
        "|---|---|---|---|---|---:|---|---|---|",
    ]
    for row in _rows_from_payload(payload):
        evidence = _mapping(row.get("evidence"), "row.evidence")
        value = _mapping(row.get("value_assessment"), "row.value_assessment")
        lines.append(
            "| "
            + str(row["community"])
            + " | "
            + str(row["source_scope"])
            + " | "
            + str(row["topic_cluster"])
            + " | "
            + str(row["feedback_action"])
            + " | "
            + str(value["stage"])
            + " | "
            + str(value["score"])
            + " | "
            + ", ".join(list(row.get("suggested_user_tags") or []))
            + " | "
            + str(evidence["total_evidence"])
            + " | "
            + ", ".join(list(row.get("risks") or []))
            + " |"
        )
    return "\n".join(lines).rstrip() + "\n"


def _rows_from_payload(payload: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    rows = payload.get("rows")
    if not isinstance(rows, list):
        raise ValueError("payload rows must be a list")
    return [row for row in rows if isinstance(row, Mapping)]


def _mapping(value: object, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{field} must be an object")
    return value


__all__ = ["render_pool_feedback_markdown"]
