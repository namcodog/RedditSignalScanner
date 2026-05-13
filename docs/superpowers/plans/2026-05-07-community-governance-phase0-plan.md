# Community Governance Phase 0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn Phase 0 into a read-only community governance audit: define how communities enter, stay, need evidence, become stale, or get treated as noise.

**Architecture:** Reuse existing assets instead of building a new discovery system. Read Hotpost published cards, `community_pool`, `discovered_communities`, and `hotpost_supply_discovery_v2.yaml`; produce a governance report. Do not call Reddit search, write DB, create tables, touch `hotpost-mini`, or claim recommendation quality is solved.

**Tech Stack:** Python, SQLAlchemy async session, existing Hotpost JSON store, existing `CommunityPool` and `DiscoveredCommunity` models, YAML config.

---

## Locked Decisions

- Phase 0 name: `社区治理 Phase 0`.
- Goal: `A/B` from user choice: governance rules are the main goal; Hotpost + `community_pool` integration is the core evidence path.
- DB: read-only.
- Tables: no new table.
- `CommunityDiscoveryService`: do not use in Phase 0 runtime; Phase 1 may add dry-run support.
- `community_ranker`: do not call in Phase 0; move ranking/semantic scoring to Phase 1.
- Governance states: `promote_candidate / keep_active / needs_evidence / stale_review / noise`.
- Hotpost published cards: strong evidence.
- Mini boundary: only read root Hotpost published data; do not touch `hotpost-mini`.
- Current `phase0_preview.py`: delete and rewrite as governance audit.
- Deliverables: governance rules doc + read-only audit script + audit report.
- Acceptance: `A/B` from user choice: must output governance states with evidence, and still cover the three business scenarios as audit slices, not recommendation fixtures.

## Files

- Keep: `backend/app/services/hotpost/hotpost_community_activity.py`
  - Responsibility: small read-only activity provider. Trim only if needed; no recommendation scoring.
- Delete: `backend/scripts/community/phase0_preview.py`
  - Reason: wrong product口径; it implements recommendation preview and custom shallow scoring.
- Create: `backend/scripts/community/community_governance_audit.py`
  - Responsibility: read-only governance audit, no live Reddit search, no DB writes.
- Create: `docs/reference/community-governance-rules-2026-05-07.md`
  - Responsibility: human-readable governance rules and Phase 1 deferrals.
- Create: `reports/community-governance/phase0-audit.md`
  - Responsibility: generated audit report.
- Update: `reports/phase-log/phase1085.md`, `reports/phase-log/CURRENT_STATUS.md`, `reports/phase-log/OPEN_ITEMS.md`, `reports/phase-log/INDEX.md`
  - Responsibility: correct Phase 0 status from recommendation preview to governance audit.

---

### Task 1: Write Governance Rules

**Files:**
- Create: `docs/reference/community-governance-rules-2026-05-07.md`

- [ ] **Step 1: Create the rules document**

Write this exact structure:

```markdown
# Community Governance Rules

Date: 2026-05-07

## Phase 0 Scope

Phase 0 is a read-only governance audit. It does not recommend communities to users.

Allowed reads:
- Hotpost published cards
- `community_pool`
- `discovered_communities`
- `backend/config/hotpost_supply_discovery_v2.yaml`

Not allowed:
- DB writes
- New tables
- Reddit live search
- API or frontend changes
- `hotpost-mini` changes
- Recommendation algorithm claims

## Governance States

### promote_candidate

A community is a promote candidate when Hotpost has already produced useful published cards from it, but it is missing from active `community_pool`.

Minimum evidence:
- `hotpost_card_count >= 2`, or
- `hotpost_card_count >= 1` and the community is already in supply config or `discovered_communities`.

### keep_active

A community should stay active when it exists in `community_pool` and has recent Hotpost evidence or strong configured coverage.

Minimum evidence:
- active in `community_pool`, and
- `hotpost_card_count > 0` or present in supply config.

### needs_evidence

A community needs evidence when it appears in supply config or `discovered_communities`, but Hotpost has not yet produced published cards from it.

### stale_review

A community needs stale review when it is active in `community_pool`, but has no Hotpost cards and no supply config coverage.

### noise

A community is noise when it appears only through weak cross-domain evidence and should not be promoted in Phase 0.

Examples:
- AI-only community inside a pet-products audit slice
- SEO/PPC-only community inside a pet-products audit slice
- Ecommerce seller community inside an AI-tools audit slice

## Business Audit Slices

Phase 0 keeps three slices for coverage only:
- pet-products
- ai-tools
- crossborder-ecommerce

These are not recommendation fixtures. They are audit slices used to detect missing coverage and noise.

## Phase 1 Deferrals

- Add `CommunityDiscoveryService` dry-run mode.
- Decide whether to reuse `community_ranker.compute_ranking_scores`.
- Add semantic relevance or embedding-based matching.
- Decide whether governance results need durable snapshots.
```

- [ ] **Step 2: Verify rules document exists**

Run:

```bash
test -s docs/reference/community-governance-rules-2026-05-07.md
```

Expected: exit code `0`.

---

### Task 2: Replace Recommendation Preview With Governance Audit Script

**Files:**
- Delete: `backend/scripts/community/phase0_preview.py`
- Create: `backend/scripts/community/community_governance_audit.py`
- Reuse: `backend/app/services/hotpost/hotpost_community_activity.py`

- [ ] **Step 1: Delete the wrong preview script**

Delete:

```text
backend/scripts/community/phase0_preview.py
```

- [ ] **Step 2: Create the governance audit script**

Create `backend/scripts/community/community_governance_audit.py` with these responsibilities:

```python
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
    return "noise"


def evidence_for(item: CommunityActivity, discovered_status: str | None) -> dict[str, Any]:
    return {
        "hotpost_card_count": item.card_count,
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
    scopes = set(item.source_scopes) | (set(item.supply.scopes) if item.supply is not None else set())
    if scopes & spec["noise_scopes"] and not scopes & spec["allowed_scopes"]:
        return True
    corpus = " ".join([item.community_name, item.name_key, *item.example_titles]).lower()
    return bool(scopes & spec["noise_scopes"]) and not any(token in corpus for token in spec["expected_tokens"])


def build_payload(
    activity: dict[str, CommunityActivity],
    discovered: dict[str, str],
) -> dict[str, Any]:
    rows: list[GovernanceRow] = []
    for key, item in activity.items():
        status = discovered.get(key)
        rows.append(
            GovernanceRow(
                community=item.community_name,
                state=classify(item, status),
                evidence=evidence_for(item, status),
            )
        )

    by_state: dict[str, list[dict[str, Any]]] = {}
    for row in sorted(rows, key=lambda r: (-int(r.evidence["hotpost_card_count"]), r.community.lower())):
        by_state.setdefault(row.state, []).append(
            {
                "community": row.community,
                "evidence": row.evidence,
            }
        )

    slices = {}
    for slice_id in AUDIT_SLICES:
        slices[slice_id] = {
            "noise": [
                row.community
                for row in rows
                if row.evidence["hotpost_card_count"] > 0 and slice_noise(slice_id, activity[normalize_community_key(row.community)])
            ][:20]
        }

    return {
        "phase": "community-governance-phase0",
        "counts": {state: len(items) for state, items in by_state.items()},
        "states": by_state,
        "audit_slices": slices,
        "decision": "review_governance_report_then_open_phase1",
    }


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
        "",
    ]
    for state in ["promote_candidate", "keep_active", "needs_evidence", "stale_review", "noise"]:
        lines.extend([f"## {state}", ""])
        for item in payload["states"].get(state, [])[:30]:
            evidence = item["evidence"]
            lines.append(
                "- "
                + item["community"]
                + f" | cards={evidence['hotpost_card_count']}"
                + f" | latest={evidence['latest_card_at']}"
                + f" | pool={evidence['in_pool']}"
                + f" | supply={evidence['in_supply']}"
                + f" | discovered={evidence['discovered_status']}"
                + f" | sample={'; '.join(evidence['example_titles'][:1])}"
            )
        lines.append("")
    lines.extend(["## Audit Slices", ""])
    for slice_id, result in payload["audit_slices"].items():
        lines.append(f"- {slice_id} noise sample: `{', '.join(result['noise'][:10])}`")
    return "\n".join(lines).rstrip() + "\n"


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
```

- [ ] **Step 3: Syntax check**

Run:

```bash
PYTHONPATH=backend .venv/bin/python -m compileall backend/scripts/community/community_governance_audit.py
```

Expected: compile succeeds.

---

### Task 3: Add Focused Smoke Tests

**Files:**
- Create: `backend/tests/scripts/community/test_community_governance_audit.py`

- [ ] **Step 1: Write tests for governance classification**

Create tests that import pure functions only. Do not open DB.

```python
from __future__ import annotations

from collections import Counter

from app.services.hotpost.hotpost_community_activity import CommunityActivity, SupplyCommunitySnapshot
from scripts.community.community_governance_audit import classify, slice_noise


def test_hotpost_verified_missing_pool_promotes_candidate() -> None:
    item = CommunityActivity(community_name="r/ClaudeCode", name_key="claudecode")
    item.card_count = 2

    assert classify(item, None) == "promote_candidate"


def test_pool_without_hotpost_or_supply_is_stale_review() -> None:
    item = CommunityActivity(community_name="r/OldPool", name_key="oldpool")
    item.pool = object()  # type: ignore[assignment]

    assert classify(item, None) == "stale_review"


def test_supply_without_hotpost_needs_evidence() -> None:
    item = CommunityActivity(community_name="r/mcp", name_key="mcp")
    item.supply = SupplyCommunitySnapshot(scopes=("ai-automation",))

    assert classify(item, None) == "needs_evidence"


def test_pet_slice_flags_ai_scope_as_noise() -> None:
    item = CommunityActivity(community_name="r/AI_Agents", name_key="ai_agents")
    item.card_count = 1
    item.source_scopes = Counter({"ai-automation": 1})

    assert slice_noise("pet-products", item) is True
```

- [ ] **Step 2: Run tests**

Run:

```bash
PYTHONPATH=backend .venv/bin/python -m pytest backend/tests/scripts/community/test_community_governance_audit.py -q
```

Expected: tests pass.

---

### Task 4: Generate Governance Audit Report

**Files:**
- Create: `reports/community-governance/phase0-audit.md`

- [ ] **Step 1: Run live audit**

Run:

```bash
PYTHONPATH=backend .venv/bin/python backend/scripts/community/community_governance_audit.py --output reports/community-governance/phase0-audit.md
```

Expected:
- JSON printed to stdout.
- `reports/community-governance/phase0-audit.md` exists.
- JSON contains states: `promote_candidate`, `keep_active`, `needs_evidence`, `stale_review`, `noise` when data supports them.

- [ ] **Step 2: Verify report**

Run:

```bash
test -s reports/community-governance/phase0-audit.md
rg -n "promote_candidate|keep_active|needs_evidence|stale_review|noise" reports/community-governance/phase0-audit.md
```

Expected: report contains governance states.

---

### Task 5: Correct Phase Log

**Files:**
- Modify: `reports/phase-log/phase1085.md`
- Modify: `reports/phase-log/CURRENT_STATUS.md`
- Modify: `reports/phase-log/OPEN_ITEMS.md`
- Modify: `reports/phase-log/INDEX.md`

- [ ] **Step 1: Replace recommendation wording**

Change wording from “community recommendation preview / fixture passed / open_phase1_review” to:

```text
Community Governance Phase 0 已落地为只读治理审计：读取 Hotpost published cards、community_pool、discovered_communities 和 supply config，输出 promote_candidate / keep_active / needs_evidence / stale_review / noise。当前结论只允许进入 Phase 1 治理与语义审查，不能表述成推荐算法通过。
```

- [ ] **Step 2: Link the new report**

Add link:

```text
reports/community-governance/phase0-audit.md
```

- [ ] **Step 3: Verify phase-log diff**

Run:

```bash
git diff --check -- reports/phase-log/phase1085.md reports/phase-log/CURRENT_STATUS.md reports/phase-log/OPEN_ITEMS.md reports/phase-log/INDEX.md
```

Expected: no output.

---

### Task 6: Boundary and Quality Verification

**Files:**
- All files touched in this plan.

- [ ] **Step 1: Verify no mini pollution**

Run:

```bash
make boundary-status
```

Expected:
- Root section does not list `hotpost-mini`.
- Mini section may still show its independent dirty snapshot state; do not touch it.

- [ ] **Step 2: Verify no old preview remains**

Run:

```bash
test ! -f backend/scripts/community/phase0_preview.py
```

Expected: exit code `0`.

- [ ] **Step 3: Run target checks**

Run:

```bash
PYTHONPATH=backend .venv/bin/python -m compileall backend/app/services/hotpost/hotpost_community_activity.py backend/scripts/community/community_governance_audit.py
PYTHONPATH=backend .venv/bin/python -m pytest backend/tests/scripts/community/test_community_governance_audit.py -q
git diff --check -- backend/app/services/hotpost/hotpost_community_activity.py backend/scripts/community/community_governance_audit.py backend/tests/scripts/community/test_community_governance_audit.py docs/reference/community-governance-rules-2026-05-07.md reports/community-governance/phase0-audit.md reports/phase-log/phase1085.md reports/phase-log/CURRENT_STATUS.md reports/phase-log/OPEN_ITEMS.md reports/phase-log/INDEX.md
```

Expected:
- compile succeeds.
- pytest passes.
- `git diff --check` has no output.

## Self-Review

- This plan does not create tables.
- This plan does not write DB rows.
- This plan does not call Reddit live search.
- This plan deletes the wrong recommendation preview instead of patching it.
- This plan keeps Phase 1 items out of Phase 0: `CommunityDiscoveryService` dry-run, `community_ranker`, semantic scoring, durable snapshots.
- The only new runtime script is a read-only governance audit.
