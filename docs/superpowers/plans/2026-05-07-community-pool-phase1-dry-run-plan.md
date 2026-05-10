# Community Pool Phase 1 Dry-Run Governance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn Phase 0 community-pool governance results into a read-only dry-run entry plan with caps, evidence fields, and a write-before-review gate.

**Architecture:** Phase 1 stays read-only. A pure planner converts Phase 0 audit payload into machine-readable dry-run rows; a CLI script renders JSON and Markdown reports. No DB writes, no API/frontend changes, no mini program changes.

**Tech Stack:** Python 3.11, existing SQLAlchemy read session, existing `community_governance_audit.py`, pytest.

---

## Confirmed Mouth

Phase 1 is **not** production write. It is the write-before-review gate.

- `入池` still means entering system learning / collection / analysis / evidence accumulation scope.
- Phase 1 must not write Gold DB, Dev DB, `community_pool`, API, frontend, Hotpost daily ops, or `hotpost-mini`.
- Phase 1 first-class subject is the `108` existing-evidence communities: `69 promote_candidate + 39 keep_active`.
- `needs_evidence=31`, `stale_review=115`, and `observation_queue=10` are not downgrade/delete queues. They are evidence-review queues.
- Generic communities can enter the pool, but Phase 1 must mark them with a cap/budget requirement.
- Generic communities also need a hot-floor rule: must-have platform hot signals bypass the regular generic cap, with explicit reason `must_have_hot_signal`.
- Long-tail communities are priority learning assets and must be judged by activity, post quality, vertical density, and learnability.

## Files

- Create: `backend/app/services/community/community_pool_phase1_planner.py`
  - Pure planner. No DB session. Converts Phase 0 audit payload into dry-run rows and summary.
- Create: `backend/scripts/community/community_pool_phase1_dry_run.py`
  - CLI wrapper. Loads Phase 0 audit read-only, calls planner, writes report artifacts.
- Create: `backend/tests/services/community/test_community_pool_phase1_planner.py`
  - Unit tests for row classification, cap policy, and queue handling.
- Create: `backend/tests/scripts/community/test_community_pool_phase1_dry_run.py`
  - CLI/render tests without DB writes.
- Output at runtime: `reports/community-governance/phase1-dry-run.json`
- Output at runtime: `reports/community-governance/phase1-dry-run.md`
- Modify after verification: `reports/phase-log/CURRENT_STATUS.md`
- Modify after verification: `reports/phase-log/OPEN_ITEMS.md`
- Modify after verification: `reports/phase-log/INDEX.md`

## Acceptance

Phase 1 is accepted only if the generated reports answer these questions:

- Which `69` communities are proposed as pool additions?
- Which `39` communities stay unchanged in pool?
- Which generic communities require cap/budget?
- How does Phase 1 prevent the generic cap from hiding must-have hot signals?
- Which long-tail communities need activity/post-quality fields?
- How are `31 / 115 / 10` routed without downgrade or deletion?
- If a future write step is approved, which fields would be written and how many rows would be affected?

## Task 1: Pure Planner Contract

**Files:**
- Create: `backend/app/services/community/community_pool_phase1_planner.py`
- Test: `backend/tests/services/community/test_community_pool_phase1_planner.py`

- [ ] **Step 1: Write the failing planner tests**

Create `backend/tests/services/community/test_community_pool_phase1_planner.py` with focused fixture payloads:

```python
from __future__ import annotations

from app.services.community.community_pool_phase1_planner import build_phase1_plan


def test_phase1_routes_existing_evidence_without_db_write() -> None:
    payload = {
        "counts": {
            "promote_candidate": 1,
            "keep_active": 1,
            "needs_evidence": 1,
            "stale_review": 1,
            "observation_queue": 1,
        },
        "states": {
            "promote_candidate": [
                {
                    "community": "r/PPC",
                    "evidence": {
                        "hotpost_card_count": 37,
                        "in_pool": False,
                        "in_supply": True,
                        "discovered_status": None,
                        "supply_scopes": ["business-growth-ops"],
                        "example_titles": ["PPC sample"],
                    },
                }
            ],
            "keep_active": [
                {
                    "community": "r/BuyItForLife",
                    "evidence": {
                        "hotpost_card_count": 51,
                        "in_pool": True,
                        "in_supply": True,
                        "discovered_status": None,
                        "supply_scopes": ["ecommerce-sellers"],
                        "example_titles": ["BIFL sample"],
                    },
                }
            ],
            "needs_evidence": [{"community": "r/mcp", "evidence": {}}],
            "stale_review": [{"community": "r/airfryer", "evidence": {}}],
            "observation_queue": [{"community": "r/VacuumCleaners", "evidence": {}}],
        },
    }

    plan = build_phase1_plan(payload)

    assert plan["summary"]["proposed_pool_additions"] == 1
    assert plan["summary"]["keep_pool_unchanged"] == 1
    assert plan["summary"]["review_only"]["needs_evidence"] == 1
    assert plan["summary"]["review_only"]["stale_review"] == 1
    assert plan["summary"]["review_only"]["observation_queue"] == 1
    assert plan["writes_allowed"] is False


def test_generic_community_requires_cap_policy() -> None:
    payload = {
        "counts": {},
        "states": {
            "promote_candidate": [
                {
                    "community": "r/OpenAI",
                    "evidence": {
                        "hotpost_card_count": 30,
                        "in_pool": False,
                        "in_supply": True,
                        "discovered_status": "pending",
                        "supply_scopes": ["ai-automation"],
                        "example_titles": ["OpenAI sample"],
                    },
                }
            ],
            "keep_active": [],
            "needs_evidence": [],
            "stale_review": [],
            "observation_queue": [],
        },
    }

    plan = build_phase1_plan(payload)
    row = plan["rows"][0]

    assert row["community"] == "r/OpenAI"
    assert row["phase1_action"] == "propose_pool_addition"
    assert row["role"] == "generic_hotspot"
    assert row["cap_required"] is True
    assert row["suggested_usage_policy"]["mode"] == "capped_learning"


def test_longtail_community_gets_evidence_fields() -> None:
    payload = {
        "counts": {},
        "states": {
            "promote_candidate": [
                {
                    "community": "r/AsianBeauty",
                    "evidence": {
                        "hotpost_card_count": 5,
                        "in_pool": False,
                        "in_supply": False,
                        "discovered_status": None,
                        "supply_scopes": [],
                        "example_titles": ["AsianBeauty sample"],
                    },
                }
            ],
            "keep_active": [],
            "needs_evidence": [],
            "stale_review": [],
            "observation_queue": [],
        },
    }

    plan = build_phase1_plan(payload)
    row = plan["rows"][0]

    assert row["role"] == "longtail_vertical"
    assert row["cap_required"] is False
    assert row["required_evidence_fields"] == [
        "activity",
        "post_quality",
        "vertical_density",
        "learnability",
    ]
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```bash
PYTHONPATH=backend .venv/bin/python -m pytest backend/tests/services/community/test_community_pool_phase1_planner.py -q
```

Expected: fail because `community_pool_phase1_planner.py` does not exist.

- [ ] **Step 3: Implement the minimal planner**

Create `backend/app/services/community/community_pool_phase1_planner.py`:

```python
from __future__ import annotations

from typing import Any

GENERIC_HOTSPOT_KEYS = {
    "ppc",
    "digitalmarketing",
    "openai",
    "claudeai",
    "artificial",
    "productmanagement",
    "analytics",
    "google_ads",
    "googleads",
    "adops",
    "projectmanagement",
    "content_marketing",
    "juststart",
    "productivity",
    "singularity",
    "seogrowth",
    "substack",
    "facebookads",
    "seo",
    "chatgpt",
    "entrepreneur",
    "techseo",
    "smallbusiness",
    "saas",
    "startups",
    "marketing",
    "bigseo",
}

AI_WORKFLOW_HINTS = {"claude", "llm", "cursor", "agent", "coding", "openwebui", "comfyui"}
PLATFORM_OPS_HINTS = {"amazon", "etsy", "shopify", "seller", "sales", "marketing", "support", "revops"}


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
        "required_evidence_fields": [
            "activity",
            "post_quality",
            "vertical_density",
            "learnability",
        ],
        "write_preview": {
            "would_insert_pool": action == "propose_pool_addition",
            "would_update_pool": False,
            "writes_allowed_in_phase1": False,
        },
        "evidence": evidence,
    }


def build_phase1_plan(phase0_payload: dict[str, Any]) -> dict[str, Any]:
    states = phase0_payload.get("states") or {}
    rows = [
        existing_evidence_row("promote_candidate", item)
        for item in states.get("promote_candidate", [])
    ]
    rows.extend(
        existing_evidence_row("keep_active", item)
        for item in states.get("keep_active", [])
    )

    review_only = {
        "needs_evidence": len(states.get("needs_evidence", [])),
        "stale_review": len(states.get("stale_review", [])),
        "observation_queue": len(states.get("observation_queue", [])),
    }

    return {
        "phase": "community-pool-phase1-dry-run",
        "writes_allowed": False,
        "summary": {
            "existing_evidence_communities": len(rows),
            "proposed_pool_additions": sum(
                1 for row in rows if row["phase1_action"] == "propose_pool_addition"
            ),
            "keep_pool_unchanged": sum(
                1 for row in rows if row["phase1_action"] == "keep_pool_unchanged"
            ),
            "generic_cap_required": sum(1 for row in rows if row["cap_required"]),
            "review_only": review_only,
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
```

- [ ] **Step 4: Run planner tests and verify pass**

Run:

```bash
PYTHONPATH=backend .venv/bin/python -m pytest backend/tests/services/community/test_community_pool_phase1_planner.py -q
```

Expected: `3 passed`.

## Task 2: Dry-Run CLI and Reports

**Files:**
- Create: `backend/scripts/community/community_pool_phase1_dry_run.py`
- Test: `backend/tests/scripts/community/test_community_pool_phase1_dry_run.py`

- [ ] **Step 1: Write CLI render tests**

Create `backend/tests/scripts/community/test_community_pool_phase1_dry_run.py`:

```python
from __future__ import annotations

from scripts.community.community_pool_phase1_dry_run import render_markdown


def test_render_markdown_states_no_db_writes() -> None:
    payload = {
        "summary": {
            "existing_evidence_communities": 2,
            "proposed_pool_additions": 1,
            "keep_pool_unchanged": 1,
            "generic_cap_required": 1,
            "review_only": {
                "needs_evidence": 31,
                "stale_review": 115,
                "observation_queue": 10,
            },
        },
        "rows": [
            {
                "community": "r/OpenAI",
                "source_state": "promote_candidate",
                "phase1_action": "propose_pool_addition",
                "role": "generic_hotspot",
                "cap_required": True,
                "suggested_usage_policy": {"mode": "capped_learning"},
                "write_preview": {
                    "would_insert_pool": True,
                    "would_update_pool": False,
                    "writes_allowed_in_phase1": False,
                },
                "evidence": {"hotpost_card_count": 30},
            }
        ],
    }

    markdown = render_markdown(payload)

    assert "Phase 1 Community Pool Dry-Run" in markdown
    assert "DB writes: `false`" in markdown
    assert "| r/OpenAI | promote_candidate | propose_pool_addition | generic_hotspot | Y |" in markdown
    assert "needs_evidence=31 / stale_review=115 / observation_queue=10" in markdown
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```bash
PYTHONPATH=backend .venv/bin/python -m pytest backend/tests/scripts/community/test_community_pool_phase1_dry_run.py -q
```

Expected: fail because CLI file does not exist.

- [ ] **Step 3: Implement CLI**

Create `backend/scripts/community/community_pool_phase1_dry_run.py`:

```python
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = ROOT.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.community.community_pool_phase1_planner import build_phase1_plan
from scripts.community.community_governance_audit import run_audit

DEFAULT_JSON_OUTPUT = PROJECT_ROOT / "reports" / "community-governance" / "phase1-dry-run.json"
DEFAULT_MD_OUTPUT = PROJECT_ROOT / "reports" / "community-governance" / "phase1-dry-run.md"


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    review = summary["review_only"]
    lines = [
        "# Phase 1 Community Pool Dry-Run",
        "",
        "- DB writes: `false`",
        f"- existing_evidence_communities: `{summary['existing_evidence_communities']}`",
        f"- proposed_pool_additions: `{summary['proposed_pool_additions']}`",
        f"- keep_pool_unchanged: `{summary['keep_pool_unchanged']}`",
        f"- generic_cap_required: `{summary['generic_cap_required']}`",
        (
            "- review_only: "
            f"`needs_evidence={review['needs_evidence']} / "
            f"stale_review={review['stale_review']} / "
            f"observation_queue={review['observation_queue']}`"
        ),
        "",
        "## Existing Evidence Rows",
        "",
        "| Community | Source State | Phase 1 Action | Role | Cap | Cards |",
        "|---|---|---|---|---|---:|",
    ]
    for row in payload["rows"]:
        evidence = row.get("evidence") or {}
        lines.append(
            "| "
            + row["community"]
            + " | "
            + row["source_state"]
            + " | "
            + row["phase1_action"]
            + " | "
            + row["role"]
            + " | "
            + ("Y" if row["cap_required"] else "N")
            + " | "
            + str(evidence.get("hotpost_card_count", 0))
            + " |"
        )
    lines.extend(
        [
            "",
            "## Write Gate",
            "",
            "This report is a dry-run gate. It does not authorize DB writes.",
            "A later write step needs explicit human approval and a row-level rollback plan.",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


async def build() -> dict[str, Any]:
    return build_phase1_plan(await run_audit())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate community pool Phase 1 dry-run reports.")
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON_OUTPUT)
    parser.add_argument("--md-output", type=Path, default=DEFAULT_MD_OUTPUT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = asyncio.run(build())
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    args.md_output.write_text(render_markdown(payload), encoding="utf-8")
    print(json.dumps(payload["summary"], ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run CLI render tests**

Run:

```bash
PYTHONPATH=backend .venv/bin/python -m pytest backend/tests/scripts/community/test_community_pool_phase1_dry_run.py -q
```

Expected: `1 passed`.

## Task 3: Generate Dry-Run Artifacts

**Files:**
- Output: `reports/community-governance/phase1-dry-run.json`
- Output: `reports/community-governance/phase1-dry-run.md`

- [ ] **Step 1: Run dry-run generator**

Run:

```bash
PYTHONPATH=backend .venv/bin/python backend/scripts/community/community_pool_phase1_dry_run.py
```

Expected output summary:

```json
{"existing_evidence_communities": 108, "generic_cap_required": 27, "keep_pool_unchanged": 39, "proposed_pool_additions": 69, "review_only": {"needs_evidence": 31, "observation_queue": 10, "stale_review": 115}}
```

- [ ] **Step 2: Verify report counts**

Run:

```bash
python - <<'PY'
import json
payload=json.load(open("reports/community-governance/phase1-dry-run.json"))
print(payload["summary"])
assert payload["writes_allowed"] is False
assert payload["summary"]["existing_evidence_communities"] == 108
assert payload["summary"]["proposed_pool_additions"] == 69
assert payload["summary"]["keep_pool_unchanged"] == 39
assert payload["summary"]["review_only"] == {
    "needs_evidence": 31,
    "stale_review": 115,
    "observation_queue": 10,
}
PY
```

Expected: prints summary and exits `0`.

## Task 4: Verification and Boundary Checks

**Files:**
- No new code files beyond Tasks 1-3.

- [ ] **Step 1: Run focused tests**

Run:

```bash
PYTHONPATH=backend .venv/bin/python -m pytest \
  backend/tests/services/community/test_community_pool_phase1_planner.py \
  backend/tests/scripts/community/test_community_pool_phase1_dry_run.py \
  backend/tests/scripts/community/test_community_governance_audit.py
```

Expected: all tests pass.

- [ ] **Step 2: Prove no DB write path exists in Phase 1 files**

Run:

```bash
rg -n "\.add\(|commit\(|flush\(|delete\(|update\(|insert\(|--write|--execute" \
  backend/app/services/community/community_pool_phase1_planner.py \
  backend/scripts/community/community_pool_phase1_dry_run.py
```

Expected: no matches.

- [ ] **Step 3: Check mini boundary**

Run:

```bash
make boundary-status
```

Expected: no new `hotpost-mini/hotpost-mini-app` changes from Phase 1.

- [ ] **Step 4: Check diff formatting**

Run:

```bash
git diff --check -- \
  backend/app/services/community/community_pool_phase1_planner.py \
  backend/scripts/community/community_pool_phase1_dry_run.py \
  backend/tests/services/community/test_community_pool_phase1_planner.py \
  backend/tests/scripts/community/test_community_pool_phase1_dry_run.py \
  reports/community-governance/phase1-dry-run.json \
  reports/community-governance/phase1-dry-run.md
```

Expected: no output, exit `0`.

## Task 5: Phase-Log Closeout

**Files:**
- Modify: `reports/phase-log/CURRENT_STATUS.md`
- Modify: `reports/phase-log/OPEN_ITEMS.md`
- Modify: `reports/phase-log/INDEX.md`
- Create only if Phase 1 artifacts are generated and verified: `reports/phase-log/phase1088.md`

- [ ] **Step 1: Update current status**

Record:

- Phase 1 dry-run artifacts generated.
- DB writes still not allowed.
- `69 / 39 / 31 / 115 / 10` counts verified.
- Next gate is human review of write preview.

- [ ] **Step 2: Add phase-log entry**

Create `reports/phase-log/phase1088.md` only after verification. Keep it under 20 lines.

- [ ] **Step 3: Re-run targeted status checks**

Run:

```bash
rg -n "Phase 1|phase1-dry-run|不写 DB|write gate" \
  reports/phase-log/CURRENT_STATUS.md \
  reports/phase-log/OPEN_ITEMS.md \
  reports/phase-log/INDEX.md \
  reports/phase-log/phase1088.md
```

Expected: all four phase-log entry points reference Phase 1 accurately.

## Self-Review

- Spec coverage: the six confirmed items are covered by Tasks 1-5.
- Placeholder scan: no placeholder markers or deferred implementation placeholders are allowed in the execution tasks.
- Scope control: no DB writes, no API/frontend changes, no mini changes, no production service hookup.
- Main risk: role inference is still deterministic and simple. That is acceptable for Phase 1 dry-run, but its output must be reviewed before any future write step.
