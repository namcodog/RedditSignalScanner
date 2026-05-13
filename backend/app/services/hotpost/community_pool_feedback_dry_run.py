from __future__ import annotations

from collections import Counter
from typing import Any, Mapping

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.community_pool import CommunityPool
from app.services.community.interest_tag_catalog import InterestTagCatalog, load_interest_tag_catalog
from app.services.hotpost.community_value_scoring import assess_community_value


ACTION_ALREADY = "already_in_pool"
ACTION_PROMOTE = "promote_candidate"
ACTION_KEEP = "keep_testing"
ACTION_REJECT = "reject"


async def load_active_pool_community_keys(session: AsyncSession) -> set[str]:
    result = await session.execute(
        select(CommunityPool.name_key).where(
            CommunityPool.deleted_at.is_(None),
            CommunityPool.is_active.is_(True),
            CommunityPool.is_blacklisted.is_(False),
        )
    )
    return {_community_key(value) for value in result.scalars().all()}


def build_pool_feedback_dry_run(
    audit_payload: Mapping[str, Any],
    *,
    pool_community_keys: set[str],
    catalog: InterestTagCatalog | None = None,
) -> dict[str, Any]:
    interest_catalog = catalog or load_interest_tag_catalog()
    pool_keys = {_community_key(value) for value in pool_community_keys}
    rows = [
        _build_row(row, pool_keys=pool_keys, catalog=interest_catalog)
        for row in _audit_rows(audit_payload)
    ]
    counts = Counter(str(row["feedback_action"]) for row in rows)
    return {
        "schema_version": "hotpost-community-pool-feedback-dry-run/v1",
        "source_audit_schema": str(audit_payload.get("schema_version") or ""),
        "report_date": str(audit_payload.get("report_date") or ""),
        "contracts": {
            "writes_db": False,
            "auto_promote": False,
            "requires_human_review": True,
        },
        "summary": {
            "input_rows": len(rows),
            "already_in_pool": counts[ACTION_ALREADY],
            "promote_candidate": counts[ACTION_PROMOTE],
            "keep_testing": counts[ACTION_KEEP],
            "reject": counts[ACTION_REJECT],
        },
        "rows": rows,
    }


def _build_row(
    row: Mapping[str, Any],
    *,
    pool_keys: set[str],
    catalog: InterestTagCatalog,
) -> dict[str, Any]:
    community = _community_key(row.get("community"))
    evidence = _evidence(row)
    source_refs = _source_refs(row)
    action = _feedback_action(row, in_pool=community in pool_keys, total_evidence=evidence["total_evidence"])
    tags = [tag.display_name for tag in catalog.tags if set(tag.source_refs) & source_refs]
    in_pool = community in pool_keys
    return {
        "community": _display_community(row.get("community")),
        "source_scope": str(row.get("scope_id") or ""),
        "topic_cluster": str(row.get("topic_cluster_id") or ""),
        "candidate_count": evidence["candidate_count"],
        "draft_count": evidence["draft_count"],
        "published_count": evidence["published_count"],
        "reject_count": evidence["reject_count"],
        "duplicate_count": evidence["duplicate_count"],
        "suggested_user_tags": tags,
        "reasons": _reasons(action, evidence),
        "risks": _risks(row, evidence=evidence, has_tags=bool(tags)),
        "already_in_pool": in_pool,
        "feedback_action": action,
        "evidence": evidence,
        "value_assessment": assess_community_value(
            evidence=evidence,
            has_tags=bool(tags),
            in_pool=in_pool,
            feedback_action=action,
            new_topic_count=_int(row.get("new_topic_count")),
        ),
    }


def _feedback_action(row: Mapping[str, Any], *, in_pool: bool, total_evidence: int) -> str:
    if in_pool:
        return ACTION_ALREADY
    if total_evidence <= 0:
        return ACTION_KEEP
    suggested = str(row.get("suggested_action") or "")
    if suggested == ACTION_REJECT:
        return ACTION_REJECT
    if suggested == ACTION_PROMOTE:
        return ACTION_PROMOTE
    return ACTION_KEEP


def _reasons(action: str, evidence: Mapping[str, int]) -> list[str]:
    if action == ACTION_ALREADY:
        return ["already tracked in community_pool"]
    if action == ACTION_PROMOTE:
        return ["Hotpost probe has publishable evidence"]
    if action == ACTION_REJECT:
        return ["probe evidence was rejected in review"]
    if int(evidence["total_evidence"]) <= 0:
        return ["no probe evidence yet"]
    return ["probe evidence is not enough for pool feedback"]


def _risks(row: Mapping[str, Any], *, evidence: Mapping[str, int], has_tags: bool) -> list[str]:
    risks: list[str] = []
    if int(evidence["total_evidence"]) <= 0:
        risks.append("no_signal_yet")
    if int(evidence["reject_count"]) > 0:
        risks.append("review_rejections")
    if int(evidence["duplicate_count"]) > 0:
        risks.append("duplicate_posts")
    if not has_tags:
        risks.append("no_interest_tag_mapping")
    for note in _noise_notes(row.get("noise_notes")):
        if note not in risks:
            risks.append(note)
    return risks


def _noise_notes(value: object) -> list[str]:
    return [note.strip() for note in str(value or "").split(",") if note.strip()]


def _evidence(row: Mapping[str, Any]) -> dict[str, int]:
    candidate = _int(row.get("collected_candidates"))
    draft = _int(row.get("draft_count"))
    published = _int(row.get("published_count"))
    reject = _int(row.get("reject_count"))
    duplicate = _int(row.get("duplicate_count"))
    return {
        "candidate_count": candidate,
        "draft_count": draft,
        "published_count": published,
        "reject_count": reject,
        "duplicate_count": duplicate,
        "total_evidence": candidate + draft + published + reject,
    }


def _source_refs(row: Mapping[str, Any]) -> set[str]:
    refs: set[str] = set()
    cluster = str(row.get("topic_cluster_id") or "").strip()
    pack = str(row.get("topic_pack_id") or "").strip()
    if cluster:
        refs.add(f"topic_cluster:{cluster}")
    if pack:
        refs.add(f"topic_pack:{pack}")
    return refs


def _audit_rows(payload: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    rows = payload.get("rows")
    if not isinstance(rows, list):
        raise ValueError("audit payload rows must be a list")
    if not all(isinstance(row, Mapping) for row in rows):
        raise ValueError("audit payload rows must be objects")
    return rows


def _int(value: object) -> int:
    if isinstance(value, int | float):
        return int(value)
    if isinstance(value, str) and value.strip():
        return int(value)
    return 0


def _community_key(value: object) -> str:
    raw = str(value or "").strip().lower()
    return raw[2:] if raw.startswith("r/") else raw


def _display_community(value: object) -> str:
    key = _community_key(value)
    return f"r/{key}" if key else ""
