# Phase 794 - sixth pack inventory sprint

Date: 2026-04-13

## Goal

Execute the sixth supply/programming repair round without touching:

- prompt
- lane definitions
- schema
- planner logic
- named topic budget

Focus only on `pack inventory sprint` for `limit=18`.

## Changes

### 1. Metadata override for listing-derived pack drift

Files changed:

- `backend/app/services/hotpost/topic_metadata.py`
- `backend/config/hotpost_supply_discovery_v2.yaml`
- `backend/tests/services/hotpost/test_topic_metadata.py`

What changed:

- For `listing_*` driven candidates with no named topic, `topic_metadata` now allows semantic pack inference to override the generic listing pack.
- This is intentionally narrow. It does not change schema and does not touch prompt or planner.

### 2. Phrase coverage added for two real missing packs

Added phrase coverage for:

- `ai-automation:tools-efficiency`
  - `too productive to switch off`
  - `always working on something`
  - related workflow-friction phrases
- `business-growth-ops:funnel-conversion`
  - `booking appointments`
  - `form submission`
  - `booking event`
  - related funnel phrases

## Inventory effect

Target pack inventory after sync:

- `ai-automation:tools-efficiency`
  - candidates: `1`
  - drafts: `1`
  - ready_validate: `1`
- `ai-automation:agent-builder`
  - candidates: `5`
  - drafts: `0`
  - ready_validate: `0`
- `business-growth-ops:organic-discovery`
  - candidates: `0`
  - drafts: `7`
  - ready_write: `6`
- `business-growth-ops:funnel-conversion`
  - candidates: `5`
  - drafts: `0`
  - ready_validate: `0`
- `ecommerce-sellers:selection-signals`
  - candidates: `8`
  - drafts: `14`
  - ready_write: `14`

Compared with the previous state, this round added effective visible inventory by reclassifying:

- `tools-efficiency` `+1` candidate
- `funnel-conversion` `+1` candidate

## Validation

Commands:

- `.venv/bin/python backend/scripts/hotpost/sync_topic_metadata.py --json`
- `.venv/bin/python backend/scripts/hotpost/run_offline_publish_plan.py --limit 18 --output backend/tmp/offline-publish-plan-18.json`
- `.venv/bin/pytest backend/tests/services/hotpost/test_topic_metadata.py backend/tests/services/hotpost/test_offline_publish_plan.py -q --tb=short`

Results:

- `sync_topic_metadata`:
  - candidates changed: `4`
  - drafts changed: `1`
- tests:
  - `8 passed`

Current `offline_publish_plan(limit=18)`:

- lane:
  - `signal = 10`
  - `hot = 5`
  - `breakdown = 3`
- scope:
  - `ai-automation = 6`
  - `business-growth-ops = 6`
  - `ecommerce-sellers = 6`
- named topic:
  - `category-demand-shift = 1`
  - `checkout-conversion = 1`
  - `mcp-workflows = 1`

Pack counts:

- `ai-automation:tools-efficiency = 2`
- `ai-automation:upstream-winds = 3`
- `ai-automation:agent-builder = 1`
- `business-growth-ops:paid-economics = 3`
- `business-growth-ops:organic-discovery = 1`
- `business-growth-ops:funnel-conversion = 2`
- `ecommerce-sellers:selection-signals = 2`
- `ecommerce-sellers:category-winds = 3`
- `ecommerce-sellers:kill-signals = 1`

Remaining gaps:

- `ai-automation:agent-builder = 1`
- `business-growth-ops:organic-discovery = 1`
- `ecommerce-sellers:selection-signals = 2`

`pack_gap_total = 4`

## Conclusion

This round really pushed `18` closer to publish.

- Before: `pack_gap_total = 6`
- After: `pack_gap_total = 4`

The remaining gaps are no longer caused by metadata misclassification:

- `agent-builder` is now constrained by visible inventory being tied to `mcp-workflows`
- `organic-discovery` exists only in the `breakdown` pool
- `selection-signals` already has large write inventory, but further exposure is constrained by current lane/scope composition

## Release

- No new release was created in this round.
- Current release stays: `release-6fb115e4b88a`
