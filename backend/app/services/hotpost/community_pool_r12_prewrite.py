from __future__ import annotations

from collections import Counter
from typing import Any, Mapping

from app.services.community.business_category_config import phase2_category_for
from app.services.community.community_pool_phase2_dev_writer import (
    canonical_community_name,
    normalize_key,
)


PREWRITE_SOURCE = "hotpost_community_pool_r12_prewrite"
ACTION_PREPARE = "prepare_dev_write"
ACTION_SKIP_EXISTING = "skip_existing"
ACTION_BLOCK_DELETED = "blocked_deleted_conflict"
ACTION_BLOCK_LABEL = "blocked_missing_label_mapping"


def build_r12_prewrite_plan(
    feedback_payload: Mapping[str, Any],
    *,
    active_pool_keys: set[str],
    deleted_pool_keys: set[str],
) -> dict[str, Any]:
    active_keys = {_key(value) for value in active_pool_keys}
    deleted_keys = {_key(value) for value in deleted_pool_keys}
    input_rows = _feedback_rows(feedback_payload)
    candidate_rows = [_build_row(row, active_keys, deleted_keys) for row in input_rows if _is_pool_candidate(row)]
    actions = Counter(str(row["write_preview"]["action"]) for row in candidate_rows)
    return {
        "schema_version": "hotpost-community-pool-r12-prewrite/v1",
        "source_feedback_schema": str(feedback_payload.get("schema_version") or ""),
        "report_date": str(feedback_payload.get("report_date") or ""),
        "contracts": {
            "writes_db": False,
            "auto_promote": False,
            "requires_human_review": True,
            "source": PREWRITE_SOURCE,
        },
        "summary": {
            "input_rows": len(input_rows),
            "candidate_rows": len(candidate_rows),
            "would_insert": actions[ACTION_PREPARE],
            "skipped_existing": actions[ACTION_SKIP_EXISTING],
            "blocked": actions[ACTION_BLOCK_DELETED] + actions[ACTION_BLOCK_LABEL],
        },
        "rows": candidate_rows,
    }


def _build_row(row: Mapping[str, Any], active_keys: set[str], deleted_keys: set[str]) -> dict[str, Any]:
    community = canonical_community_name(str(row.get("community") or ""))
    key = normalize_key(community)
    tags = [str(tag) for tag in list(row.get("suggested_user_tags") or []) if str(tag).strip()]
    source_scope = str(row.get("source_scope") or "")
    topic_cluster = str(row.get("topic_cluster") or "")
    evidence = _mapping(row.get("evidence"), "row.evidence")
    value = _mapping(row.get("value_assessment"), "row.value_assessment")
    write_action = _write_action(key=key, tags=tags, active_keys=active_keys, deleted_keys=deleted_keys)
    risks = _risks(row, write_action)
    return {
        "community": community,
        "source_scope": source_scope,
        "topic_cluster": topic_cluster,
        "suggested_user_tags": tags,
        "label_review": _label_review(tags),
        "evidence": dict(evidence),
        "value_assessment": dict(value),
        "risks": risks,
        "write_preview": {
            "action": write_action,
            "would_insert_pool": write_action == ACTION_PREPARE,
            "pool_insert": _pool_insert_preview(
                community=community,
                source_scope=source_scope,
                topic_cluster=topic_cluster,
                tags=tags,
                evidence=evidence,
                value=value,
            ),
        },
    }


def _pool_insert_preview(
    *,
    community: str,
    source_scope: str,
    topic_cluster: str,
    tags: list[str],
    evidence: Mapping[str, Any],
    value: Mapping[str, Any],
) -> dict[str, Any]:
    key = normalize_key(community)
    return {
        "name": community,
        "tier": "seed",
        "categories": [phase2_category_for(key=key, role="", scopes=[source_scope])],
        "priority": "medium",
        "description_keywords": {
            "source": PREWRITE_SOURCE,
            "display_name": community,
            "source_scope": source_scope,
            "topic_cluster": topic_cluster,
            "suggested_user_tags": tags,
            "value_stage": str(value.get("stage") or ""),
            "score": _int(value.get("score")),
            "candidate_count": _int(evidence.get("candidate_count")),
            "published_count": _int(evidence.get("published_count")),
            "duplicate_count": _int(evidence.get("duplicate_count")),
            "total_evidence": _int(evidence.get("total_evidence")),
        },
    }


def _is_pool_candidate(row: Mapping[str, Any]) -> bool:
    value = _mapping(row.get("value_assessment"), "row.value_assessment")
    return (
        row.get("feedback_action") == "promote_candidate"
        and value.get("stage") == "pool_candidate"
        and row.get("already_in_pool") is False
    )


def _write_action(*, key: str, tags: list[str], active_keys: set[str], deleted_keys: set[str]) -> str:
    if key in active_keys:
        return ACTION_SKIP_EXISTING
    if key in deleted_keys:
        return ACTION_BLOCK_DELETED
    if not tags:
        return ACTION_BLOCK_LABEL
    return ACTION_PREPARE


def _label_review(tags: list[str]) -> str:
    if not tags:
        return "missing_tag_mapping"
    if len(tags) > 1:
        return "multi_tag_review"
    return "single_tag_ok"


def _risks(row: Mapping[str, Any], write_action: str) -> list[str]:
    risks = [str(risk) for risk in list(row.get("risks") or []) if str(risk).strip()]
    if write_action not in {ACTION_PREPARE, ACTION_SKIP_EXISTING} and write_action not in risks:
        risks.append(write_action)
    return risks


def _feedback_rows(payload: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    rows = payload.get("rows")
    if not isinstance(rows, list):
        raise ValueError("feedback payload rows must be a list")
    if not all(isinstance(row, Mapping) for row in rows):
        raise ValueError("feedback payload rows must be objects")
    return rows


def _mapping(value: object, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{field} must be an object")
    return value


def _key(value: object) -> str:
    return normalize_key(str(value or ""))


def _int(value: object) -> int:
    if isinstance(value, int | float):
        return int(value)
    if isinstance(value, str) and value.strip():
        return int(value)
    return 0


__all__ = ["build_r12_prewrite_plan"]
