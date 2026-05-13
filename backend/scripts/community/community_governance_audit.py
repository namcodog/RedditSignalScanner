from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = ROOT.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import select

from app.db.session import SessionFactory
from app.models.discovered_community import DiscoveredCommunity
from app.scripts_support.env_loader import load_backend_env
from app.services.hotpost.hotpost_community_activity import (
    CommunityActivity,
    HotpostCommunityActivityProvider,
    normalize_community_key,
)

DEFAULT_OUTPUT = PROJECT_ROOT / "reports" / "community-governance" / "phase0-audit.md"

AUDIT_SLICES = {
    "pet-products": {
        "allowed_scopes": {"ecommerce-sellers"},
        "noise_scopes": {"ai-automation", "business-growth-ops"},
        "expected_tokens": {"pet", "home", "cleaning", "amazon", "etsy", "frugal"},
    },
    "ai-tools": {
        "allowed_scopes": {"ai-automation"},
        "noise_scopes": {"ecommerce-sellers", "business-growth-ops"},
        "expected_tokens": {"ai", "llm", "agent", "claude", "openai", "coding"},
    },
    "crossborder-ecommerce": {
        "allowed_scopes": {"ecommerce-sellers", "business-growth-ops"},
        "noise_scopes": {"ai-automation"},
        "expected_tokens": {"shopify", "etsy", "amazon", "ecommerce", "seller", "fba"},
    },
}

LOW_PRIORITY_STALE_KEYS = {
    "blendedfamilies",
    "divorce",
    "education",
    "familyissues",
    "homeschool",
    "leanfire",
    "marriage",
    "relationship_advice",
    "relationships",
    "ukpersonalfinance",
}

GOVERNANCE_STATES = (
    "promote_candidate",
    "keep_active",
    "needs_evidence",
    "stale_review",
    "observation_queue",
)

STATE_DESCRIPTIONS = {
    "promote_candidate": "Hotpost has validated these communities, but they are not active in community_pool yet.",
    "keep_active": "These communities are already in community_pool and still have Hotpost or supply evidence.",
    "needs_evidence": "These communities are known by supply or discovery, but still need Hotpost evidence.",
    "stale_review": "These are legacy community_pool assets without current Hotpost/supply/discovery evidence; review old DB evidence before any downgrade.",
    "observation_queue": "These are low-evidence or uncategorized communities for later review; this is not a blacklist.",
}


@dataclass(frozen=True)
class GovernanceRow:
    community: str
    state: str
    evidence: dict[str, Any]


async def load_discovered_statuses() -> dict[str, str]:
    async with SessionFactory() as db:
        rows = await db.execute(
            select(DiscoveredCommunity.name, DiscoveredCommunity.status).where(
                DiscoveredCommunity.deleted_at.is_(None)
            )
        )
        return {normalize_community_key(name): status for name, status in rows.fetchall()}


def classify(item: CommunityActivity, discovered_status: str | None) -> str:
    in_pool = item.pool is not None
    in_supply = item.supply is not None
    in_discovered = discovered_status is not None
    has_hotpost = item.card_count > 0

    if has_hotpost and not in_pool:
        if item.card_count >= 2 or in_supply or in_discovered:
            return "promote_candidate"
    if in_pool and (has_hotpost or in_supply):
        return "keep_active"
    if not has_hotpost and (in_supply or in_discovered):
        return "needs_evidence"
    if in_pool and not has_hotpost and not in_supply:
        return "stale_review"
    return "observation_queue"


def promotion_band(item: CommunityActivity, discovered_status: str | None) -> str | None:
    if classify(item, discovered_status) != "promote_candidate":
        return None
    if item.supply is not None and item.card_count >= 5:
        return "strong"
    if item.supply is not None and item.card_count >= 2:
        return "medium"
    return "weak"


def evidence_for(item: CommunityActivity, discovered_status: str | None) -> dict[str, Any]:
    return {
        "hotpost_card_count": item.card_count,
        "promotion_band": promotion_band(item, discovered_status),
        "latest_card_at": item.latest_card_at,
        "lanes": dict(item.lanes),
        "source_scopes": dict(item.source_scopes),
        "topic_packs": dict(item.topic_packs),
        "in_pool": item.pool is not None,
        "pool_tier": item.pool.tier if item.pool is not None else None,
        "pool_daily_posts": item.pool.daily_posts if item.pool is not None else 0,
        "pool_quality_score": item.pool.quality_score if item.pool is not None else 0.0,
        "in_supply": item.supply is not None,
        "supply_scopes": list(item.supply.scopes) if item.supply is not None else [],
        "discovered_status": discovered_status,
        "example_card_ids": item.example_card_ids,
        "example_titles": item.example_titles,
    }


def slice_noise(slice_id: str, item: CommunityActivity) -> bool:
    spec = AUDIT_SLICES[slice_id]
    scopes = set(item.source_scopes)
    if item.supply is not None:
        scopes.update(item.supply.scopes)
    if scopes & spec["noise_scopes"] and not scopes & spec["allowed_scopes"]:
        return True
    corpus = " ".join([item.community_name, item.name_key, *item.example_titles]).lower()
    return bool(scopes & spec["noise_scopes"]) and not any(
        token in corpus for token in spec["expected_tokens"]
    )


def is_low_priority_stale(item: CommunityActivity) -> bool:
    return item.name_key in LOW_PRIORITY_STALE_KEYS


def build_payload(
    activity: dict[str, CommunityActivity],
    discovered: dict[str, str],
) -> dict[str, Any]:
    rows = [
        GovernanceRow(
            community=item.community_name,
            state=classify(item, discovered.get(key)),
            evidence=evidence_for(item, discovered.get(key)),
        )
        for key, item in activity.items()
    ]

    by_state: dict[str, list[dict[str, Any]]] = {state: [] for state in GOVERNANCE_STATES}
    for row in sorted(
        rows,
        key=lambda value: (-int(value.evidence["hotpost_card_count"]), value.community.lower()),
    ):
        by_state[row.state].append({"community": row.community, "evidence": row.evidence})

    return {
        "phase": "community-governance-phase0",
        "counts": {state: len(items) for state, items in by_state.items()},
        "states": by_state,
        "stale_review_triage": build_stale_review_triage(rows, activity),
        "classification_errors": build_classification_error_payload(rows, activity),
        "decision": "review_governance_report_then_open_phase1",
    }


def build_stale_review_triage(
    rows: list[GovernanceRow],
    activity: dict[str, CommunityActivity],
) -> dict[str, Any]:
    stale = [row for row in rows if row.state == "stale_review"]
    excluded = [
        row.community
        for row in stale
        if is_low_priority_stale(activity[normalize_community_key(row.community)])
    ]
    return {
        "business_review_count": len(stale) - len(excluded),
        "excluded_low_priority_count": len(excluded),
        "excluded_low_priority": excluded,
    }


def build_classification_error_payload(
    rows: list[GovernanceRow],
    activity: dict[str, CommunityActivity],
) -> dict[str, dict[str, list[str]]]:
    errors: dict[str, dict[str, list[str]]] = {}
    for slice_id in AUDIT_SLICES:
        errors[slice_id] = {
            "cross_domain_mismatch": [
                row.community
                for row in rows
                if row.evidence["hotpost_card_count"] > 0
                and slice_noise(slice_id, activity[normalize_community_key(row.community)])
            ][:20]
        }
    return errors


async def run_audit() -> dict[str, Any]:
    load_backend_env()
    async with SessionFactory() as db:
        activity = await HotpostCommunityActivityProvider().load(db)
    discovered = await load_discovered_statuses()
    return build_payload(activity, discovered)


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Community Governance Phase 0 Audit",
        "",
        f"- decision: `{payload['decision']}`",
        f"- counts: `{json.dumps(payload['counts'], ensure_ascii=False, sort_keys=True)}`",
        f"- stale_review_business_queue: `{payload['stale_review_triage']['business_review_count']}`",
        f"- stale_review_low_priority_excluded: `{payload['stale_review_triage']['excluded_low_priority_count']}`",
        "",
    ]
    for state in GOVERNANCE_STATES:
        lines.extend([f"## {state}", ""])
        lines.extend([STATE_DESCRIPTIONS[state], ""])
        items = payload["states"].get(state, [])
        if state == "stale_review":
            excluded = set(payload["stale_review_triage"]["excluded_low_priority"])
            review_items = [item for item in items if item["community"] not in excluded]
            lines.extend(["### Business Review Queue", ""])
            lines.extend(render_items(review_items[:30]))
            lines.extend(["", "### Low Priority Excluded From First Pass", ""])
            lines.extend(
                f"- {community}"
                for community in payload["stale_review_triage"]["excluded_low_priority"]
            )
            lines.append("")
            continue
        lines.extend(render_items(items[:30]))
        lines.append("")
    lines.extend(["## Classification Errors", ""])
    lines.append("These are cross-domain mismatches caught by business checks, not a global community blacklist.")
    lines.append("")
    for slice_id, result in payload["classification_errors"].items():
        lines.append(
            f"- {slice_id} cross-domain mismatch: `{', '.join(result['cross_domain_mismatch'][:10])}`"
        )
    return "\n".join(lines).rstrip() + "\n"


def render_items(items: list[dict[str, Any]]) -> list[str]:
    lines: list[str] = []
    for item in items:
        evidence = item["evidence"]
        promotion = (
            f" | promote={evidence['promotion_band']}"
            if evidence.get("promotion_band")
            else ""
        )
        lines.append(
            "- "
            + item["community"]
            + f" | cards={evidence['hotpost_card_count']}"
            + promotion
            + f" | latest={evidence['latest_card_at']}"
            + f" | pool={evidence['in_pool']}"
            + f" | supply={evidence['in_supply']}"
            + f" | discovered={evidence['discovered_status']}"
            + f" | sample={'; '.join(evidence['example_titles'][:1])}"
        )
    return lines


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run read-only community governance Phase 0 audit.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--json-only", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = asyncio.run(run_audit())
    if not args.json_only:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(render_markdown(payload), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
