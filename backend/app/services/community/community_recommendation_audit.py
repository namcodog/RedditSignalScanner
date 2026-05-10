from __future__ import annotations

from dataclasses import dataclass

from app.services.community.community_recommendation_models import (
    CommunityRecommendation,
    JsonValue,
    RecommendationPreview,
)
from app.services.community.community_recommendation_utils import to_json_value
from app.services.community.interest_tag_catalog import (
    InterestTagCatalog,
    RecommendationPolicy,
    load_interest_tag_catalog,
)


@dataclass(frozen=True)
class RecommendationAuditRow:
    tag: str
    community: str
    review_status: str
    action: str
    reason: str
    risk_flags: tuple[str, ...]


@dataclass(frozen=True)
class RecommendationAudit:
    rows: tuple[RecommendationAuditRow, ...]

    @property
    def row_count(self) -> int:
        return len(self.rows)


def _rule(policy: RecommendationPolicy, code: str) -> tuple[str, str, str]:
    item = policy.audit_rules[code]
    return item["review_status"], item["action"], item["reason"]


def _classify(
    item: CommunityRecommendation,
    policy: RecommendationPolicy,
) -> tuple[str, str, str]:
    if "needs_more_evidence" in item.risk_flags or item.status == "watching":
        return _rule(policy, "needs_evidence")
    if "generic_hotspot" in item.risk_flags:
        return _rule(policy, "generic_reference")
    if not item.semantic_terms:
        return _rule(policy, "review_match")
    return _rule(policy, "recommended")


def build_recommendation_audit(
    preview: RecommendationPreview,
    catalog: InterestTagCatalog | None = None,
) -> RecommendationAudit:
    policy = (catalog or load_interest_tag_catalog()).policy
    tag_names = {tag.tag_id: tag.name for tag in preview.tags}
    rows: list[RecommendationAuditRow] = []
    for tag_id, items in preview.recommendations.items():
        for item in items:
            status, action, reason = _classify(item, policy)
            rows.append(
                RecommendationAuditRow(
                    tag=tag_names.get(tag_id, tag_id),
                    community=item.community,
                    review_status=status,
                    action=action,
                    reason=reason,
                    risk_flags=item.risk_flags,
                )
            )
    return RecommendationAudit(rows=tuple(rows))


def audit_to_payload(audit: RecommendationAudit) -> dict[str, JsonValue]:
    return {
        "row_count": audit.row_count,
        "rows": [
            {
                "tag": row.tag,
                "community": row.community,
                "review_status": row.review_status,
                "action": row.action,
                "reason": row.reason,
                "risk_flags": to_json_value(row.risk_flags),
            }
            for row in audit.rows
        ],
    }


def render_audit_markdown(audit: RecommendationAudit) -> str:
    lines = [
        "# Community Recommendation Audit",
        "",
        f"- row_count: `{audit.row_count}`",
        "",
        "| Tag | Community | Review | Action | Reason |",
        "|---|---|---|---|---|",
    ]
    for row in audit.rows:
        lines.append(
            "| "
            + row.tag
            + " | "
            + row.community
            + " | "
            + row.review_status
            + " | "
            + row.action
            + " | "
            + row.reason
            + " |"
        )
    return "\n".join(lines).rstrip() + "\n"


__all__ = [
    "RecommendationAudit",
    "RecommendationAuditRow",
    "audit_to_payload",
    "build_recommendation_audit",
    "render_audit_markdown",
]
