# Phase 793 - `limit=18` pack frontier validation

Date: 2026-04-13

## Goal

Execute the fifth round of supply/programming repair for `offline_publish_plan(limit=18)` without touching prompt, lane definitions, or schema, and verify whether the remaining `pack_mix_drift` can still be improved by planner-only changes.

## What I checked

- Re-read the current key-os repair conclusions:
  - `supply repair budget v1`
  - `pack programming mix v1`
  - `named topic budget v1`
- Re-ran local-only verification:
  - `.venv/bin/python backend/scripts/hotpost/sync_topic_metadata.py --json`
  - `.venv/bin/python backend/scripts/hotpost/run_offline_publish_plan.py --limit 18 --output backend/tmp/offline-publish-plan-18.json`
  - `.venv/bin/pytest backend/tests/services/hotpost/test_offline_publish_plan.py -q --tb=short`
- Inspected the current visible inventory behind the planner by lane/scope/pack.

## Result

Current `limit=18` still holds:

- lane = `signal 10 / hot 5 / breakdown 3`
- scope = `ai-automation 6 / business-growth-ops 6 / ecommerce-sellers 6`
- named topic budget = PASS
- named topic counts:
  - `category-demand-shift = 1`
  - `checkout-conversion = 1`
  - `mcp-workflows = 1`

Current pack counts in `publish_list`:

- `ai-automation:tools-efficiency = 1`
- `ai-automation:upstream-winds = 4`
- `ai-automation:agent-builder = 1`
- `business-growth-ops:paid-economics = 4`
- `business-growth-ops:organic-discovery = 1`
- `business-growth-ops:funnel-conversion = 1`
- `ecommerce-sellers:selection-signals = 2`
- `ecommerce-sellers:category-winds = 2`
- `ecommerce-sellers:kill-signals = 2`

Current pack gaps stay at:

- `ai-automation:tools-efficiency = 1`
- `ai-automation:agent-builder = 1`
- `business-growth-ops:organic-discovery = 1`
- `business-growth-ops:funnel-conversion = 1`
- `ecommerce-sellers:selection-signals = 2`
- `pack_gap_total = 6`

## Why this round is a no-op

The remaining drift is now constrained by local visible inventory, not by projection order:

- `ai-automation:tools-efficiency`
  - visible inventory under current filters = `1`
  - already fully used in the plan
- `ai-automation:agent-builder`
  - visible validate candidates all carry the same named topic: `mcp-workflows`
  - current budget allows only `1`
- `business-growth-ops:organic-discovery`
  - visible inventory only appears in `breakdown`
  - increasing it would break current `scope 6/6/6`
- `business-growth-ops:funnel-conversion`
  - visible validate candidates all carry the same named topic: `checkout-conversion`
  - current budget allows only `1`
- `ecommerce-sellers:selection-signals`
  - visible inventory only appears in `breakdown`
  - current `2` slots are already what keeps ecommerce scope at `6`

## Decision

- No code changes in this round.
- `offline_publish_plan.py` is no longer the primary bottleneck for `limit=18`.
- The frontier is now inventory-bound.

## Next step

Do not keep grinding planner logic for `18`.

The next meaningful move is either:

1. expose more local supply for:
   - `ai-automation:tools-efficiency`
   - `business-growth-ops:organic-discovery`
   - `business-growth-ops:funnel-conversion`
   - `ecommerce-sellers:selection-signals`
2. or move the frontier study to a higher window after new supply lands.
