# Phase 795 - Round 7 Ready Inventory Sprint

## Date

- 2026-04-13

## Scope

- Execute round 7 without changing:
  - planner
  - named topic budget
  - prompt
  - schema
- Only improve real ready inventory for:
  - `ai-automation:agent-builder`
  - `business-growth-ops:organic-discovery`
  - `ecommerce-sellers:selection-signals`

## Changes

### 1. Tightened listing-pack semantic override

Changed files:

- `backend/app/services/hotpost/topic_metadata.py`
- `backend/config/hotpost_supply_discovery_v2.yaml`
- `backend/tests/services/hotpost/test_topic_metadata.py`

What changed:

- Listing-derived pack override now requires semantic cluster score `>= 9`.
- This keeps useful corrections while avoiding broad relabeling.
- It corrected two real exposure issues:
  - `cand-ai-automation-1sjd3tj` -> `ai-automation:tools-efficiency`
  - `cand-business-growth-ops-1sjh2m7` -> `business-growth-ops:funnel-conversion`
- It also avoided false positives:
  - `cand-ai-automation-1simerz` stayed in `upstream-winds`
  - `cand-ecommerce-sellers-1shvr83` stayed in `category-winds`

### 2. Repaired one real ready draft

- Fixed `draft-cand-business-growth-ops-1sj00ez-validate`
- Root cause:
  - `detail.min_test_action` was empty, so the draft was not truly ready
- Repair:
  - filled `min_test_action`
  - updated through `review_cards.py update-draft`

## Inventory Impact

Target packs after this round:

- `ai-automation:tools-efficiency`
  - candidates: `1`
  - drafts: `1`
  - ready_validate: `1`
- `ai-automation:agent-builder`
  - candidates: `4`
  - drafts: `0`
  - ready_validate: `0`
- `business-growth-ops:organic-discovery`
  - candidates: `0`
  - drafts: `7`
  - ready_write: `6`
- `business-growth-ops:funnel-conversion`
  - candidates: `5`
  - drafts: `0`
- `ecommerce-sellers:selection-signals`
  - candidates: `7`
  - drafts: `14`
  - ready_write: `14`

Net effect:

- `tools-efficiency` exposure improved by `+1`
- `funnel-conversion` exposure improved by `+1`
- `organic-discovery` now has one repaired ready draft that can actually participate

## Validation

Commands:

- `.venv/bin/python backend/scripts/hotpost/sync_topic_metadata.py --json`
- `.venv/bin/python backend/scripts/hotpost/run_offline_publish_plan.py --limit 18 --output backend/tmp/offline-publish-plan-18.json`
- `.venv/bin/pytest backend/tests/services/hotpost/test_topic_metadata.py backend/tests/services/hotpost/test_offline_publish_plan.py -q --tb=short`

Results:

- `sync_topic_metadata`
  - candidates changed: `3`
  - drafts changed: `0`
  - published changed: `0`
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
- `ecommerce-sellers:selection-signals = 2`

`pack_gap_total = 3`

## Conclusion

Round 7 pushed `18` closer to publish without touching planner or prompt.

- before this round: `pack_gap_total = 4`
- after this round: `pack_gap_total = 3`

The remaining gap is now pure local ready inventory:

- `agent-builder` still lacks non-`mcp-workflows` ready stock
- `selection-signals` still lacks additional validate-ready exposure

## Release

- No new release in this round.
- Current release remains: `release-6fb115e4b88a`
