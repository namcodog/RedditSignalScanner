from __future__ import annotations

from typing import Any

GENERIC_HOTSPOT_KEYS = {
    "adops",
    "analytics",
    "artificial",
    "bigseo",
    "chatgpt",
    "claudeai",
    "content_marketing",
    "digitalmarketing",
    "entrepreneur",
    "facebookads",
    "google_ads",
    "googleads",
    "juststart",
    "marketing",
    "openai",
    "ppc",
    "productivity",
    "productmanagement",
    "projectmanagement",
    "saas",
    "seo",
    "seogrowth",
    "singularity",
    "smallbusiness",
    "startups",
    "substack",
    "techseo",
}

AI_WORKFLOW_HINTS = {"agent", "claude", "coding", "comfyui", "cursor", "llm", "openwebui"}
PLATFORM_OPS_HINTS = {
    "amazon",
    "etsy",
    "marketing",
    "revops",
    "sales",
    "seller",
    "shopify",
    "support",
}

EVIDENCE_FIELDS = [
    "activity",
    "post_quality",
    "vertical_density",
    "learnability",
]

GENERIC_REGULAR_LEARNING_CAP_RATIO = 0.25
GENERIC_MAX_CAP_RATIO_WITHOUT_HUMAN_REVIEW = 0.3
GENERIC_HOT_FLOOR_BYPASS_REASON = "must_have_hot_signal"

FUTURE_WRITE_FIELDS = [
    "community",
    "source_state",
    "role",
    "cap_required",
    "suggested_usage_policy",
    "required_evidence_fields",
    "evidence_snapshot",
]


def normalize_key(community: str) -> str:
    value = str(community or "").strip()
    if value.lower().startswith("r/"):
        value = value[2:]
    return value.lower()


def infer_role(community: str, evidence: dict[str, Any]) -> str:
    key = normalize_key(community)
    if key in GENERIC_HOTSPOT_KEYS:
        return "generic_hotspot"

    scopes = set(evidence.get("supply_scopes") or [])
    if "ai-automation" in scopes and any(token in key for token in AI_WORKFLOW_HINTS):
        return "ai_workflow"
    if scopes & {"business-growth-ops", "ecommerce-sellers"} and any(
        token in key for token in PLATFORM_OPS_HINTS
    ):
        return "platform_ops"

    return "longtail_vertical"


def usage_policy_for(role: str) -> dict[str, Any]:
    if role == "generic_hotspot":
        return {
            "mode": "capped_learning",
            "cap_review_required": True,
            "regular_learning_cap_ratio": GENERIC_REGULAR_LEARNING_CAP_RATIO,
            "max_cap_ratio_without_human_review": GENERIC_MAX_CAP_RATIO_WITHOUT_HUMAN_REVIEW,
            "rule": "May enter learning scope, but cannot displace long-tail default collection.",
        }
    if role == "longtail_vertical":
        return {
            "mode": "priority_learning",
            "cap_review_required": False,
            "rule": "Evaluate by activity, post quality, vertical density, and learnability.",
        }
    return {
        "mode": "scoped_learning",
        "cap_review_required": False,
        "rule": "Bind to business scope before any future write.",
    }


def hot_floor_for(role: str) -> dict[str, Any]:
    if role != "generic_hotspot":
        return {
            "must_cover_platform_hot_signal": False,
            "bypasses_regular_cap": False,
            "cap_bypass_reason_required": False,
            "allowed_cap_bypass_reason": None,
            "scope": "not_applicable",
        }
    return {
        "must_cover_platform_hot_signal": True,
        "bypasses_regular_cap": True,
        "cap_bypass_reason_required": True,
        "allowed_cap_bypass_reason": GENERIC_HOT_FLOOR_BYPASS_REASON,
        "scope": "hot_signal_coverage_only",
    }


def existing_evidence_row(state: str, item: dict[str, Any]) -> dict[str, Any]:
    evidence = item.get("evidence") or {}
    role = infer_role(item["community"], evidence)
    action = "propose_pool_addition" if state == "promote_candidate" else "keep_pool_unchanged"
    return {
        "community": item["community"],
        "source_state": state,
        "phase1_action": action,
        "role": role,
        "cap_required": role == "generic_hotspot",
        "suggested_usage_policy": usage_policy_for(role),
        "required_evidence_fields": EVIDENCE_FIELDS,
        "hot_floor": hot_floor_for(role),
        "write_preview": {
            "would_insert_pool": action == "propose_pool_addition",
            "would_update_pool": False,
            "writes_allowed_in_phase1": False,
        },
        "evidence": evidence,
    }


def build_generic_cap_policy(rows: list[dict[str, Any]]) -> dict[str, Any]:
    generic_count = sum(1 for row in rows if row["role"] == "generic_hotspot")
    current_ratio = round(generic_count / len(rows), 4) if rows else 0.0
    return {
        "regular_learning_cap_ratio": GENERIC_REGULAR_LEARNING_CAP_RATIO,
        "max_cap_ratio_without_human_review": GENERIC_MAX_CAP_RATIO_WITHOUT_HUMAN_REVIEW,
        "current_generic_ratio": current_ratio,
        "hot_floor_enabled": True,
        "hot_floor_bypasses_regular_cap": True,
        "allowed_cap_bypass_reason": GENERIC_HOT_FLOOR_BYPASS_REASON,
    }


def build_phase1_plan(phase0_payload: dict[str, Any]) -> dict[str, Any]:
    states = phase0_payload.get("states") or {}
    rows = [
        existing_evidence_row("promote_candidate", item)
        for item in states.get("promote_candidate", [])
    ]
    rows.extend(
        existing_evidence_row("keep_active", item) for item in states.get("keep_active", [])
    )

    review_only = {
        "needs_evidence": len(states.get("needs_evidence", [])),
        "stale_review": len(states.get("stale_review", [])),
        "observation_queue": len(states.get("observation_queue", [])),
    }
    would_insert_pool_rows = sum(
        1 for row in rows if row["phase1_action"] == "propose_pool_addition"
    )
    would_update_pool_rows = 0

    return {
        "phase": "community-pool-phase1-dry-run",
        "writes_allowed": False,
        "summary": {
            "existing_evidence_communities": len(rows),
            "proposed_pool_additions": would_insert_pool_rows,
            "keep_pool_unchanged": sum(
                1 for row in rows if row["phase1_action"] == "keep_pool_unchanged"
            ),
            "generic_cap_required": sum(1 for row in rows if row["cap_required"]),
            "generic_cap_policy": build_generic_cap_policy(rows),
            "review_only": review_only,
        },
        "future_write_preview": {
            "writes_allowed_in_phase1": False,
            "would_insert_pool_rows": would_insert_pool_rows,
            "would_update_pool_rows": would_update_pool_rows,
            "fields_requiring_future_approval": FUTURE_WRITE_FIELDS,
        },
        "rows": rows,
        "review_only_queues": {
            state: [
                {
                    "community": item["community"],
                    "phase1_action": "review_evidence_only",
                    "writes_allowed_in_phase1": False,
                }
                for item in states.get(state, [])
            ]
            for state in review_only
        },
    }
