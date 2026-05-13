# Phase 796 - Round 7 Full Inventory Sprint

## Date

- 2026-04-13

## Scope

- Execute the user's "补真货" flow end-to-end.
- Do not change:
  - planner
  - named topic budget
  - prompt
  - schema
- Only improve real ready inventory for:
  - `ai-automation:agent-builder`
  - `business-growth-ops:organic-discovery`
  - `business-growth-ops:funnel-conversion`
  - `ecommerce-sellers:selection-signals`

## Changes

### 1. Created a rollback point

- `backend/tmp/pack-inventory-sprint-20260413/ai-automation.candidates.before.json`
- `backend/tmp/pack-inventory-sprint-20260413/business-growth-ops.candidates.before.json`
- `backend/tmp/pack-inventory-sprint-20260413/ecommerce-sellers.candidates.before.json`

### 2. Ran harvest collect across all three scopes

Commands:

- `python backend/scripts/hotpost/daily_collect.py --scope ai-automation --mode harvest --max-candidates 24`
- `python backend/scripts/hotpost/daily_collect.py --scope business-growth-ops --mode harvest --max-candidates 24`
- `python backend/scripts/hotpost/daily_collect.py --scope ecommerce-sellers --mode harvest --max-candidates 24`

Scope-level harvest result:

- `ai-automation = 14`
- `business-growth-ops = 16`
- `ecommerce-sellers = 20`

### 3. Ran targeted named-topic supplement to add real stock

Named topics collected:

- `prompt-engineering`
- `harness-models`
- `pet-supplies`
- `flashlight-selection`
- `checkout-conversion`

Result:

- `watch_count = 5`
- targeted new candidates landed in the real candidate pool

### 4. Seeded and repaired validate drafts

New validate drafts materialized and repaired to true ready state:

- `draft-cand-ai-automation-1se46w8-validate`
- `draft-cand-ai-automation-1sipxwa-validate`
- `draft-cand-business-growth-ops-1siulf6-validate`
- `draft-cand-business-growth-ops-1semeaz-validate`
- `draft-cand-ecommerce-sellers-1sivg7z-validate`
- `draft-cand-ecommerce-sellers-1si8x21-validate`

All six had their `min_test_action` checked; any empty field was filled before counting them as ready inventory.

## Inventory Impact

### Candidate growth vs rollback point

- `ai-automation:agent-builder`
  - candidates: `4 -> 0`
  - note: no persistent candidate growth remained, but this pack now has real ready drafts
- `business-growth-ops:organic-discovery`
  - candidates: `0 -> 8`
  - added: `+8`
- `business-growth-ops:funnel-conversion`
  - candidates: `5 -> 5`
  - added new ids into the current pool: `+2`
- `ecommerce-sellers:selection-signals`
  - candidates: `7 -> 22`
  - added: `+15`

### Current draft / ready inventory

- `ai-automation:agent-builder`
  - drafts: `2`
  - ready: `2`
- `business-growth-ops:organic-discovery`
  - drafts: `8`
  - ready: `8`
- `business-growth-ops:funnel-conversion`
  - drafts: `1`
  - ready: `1`
- `ecommerce-sellers:selection-signals`
  - drafts: `16`
  - ready: `15`

## Validation

Commands:

- `.venv/bin/python backend/scripts/hotpost/sync_topic_metadata.py --json`
- `.venv/bin/python backend/scripts/hotpost/run_offline_publish_plan.py --limit 18 --output backend/tmp/offline-publish-plan-18.json`
- `.venv/bin/pytest backend/tests/services/hotpost/test_topic_metadata.py backend/tests/services/hotpost/test_offline_publish_plan.py -q --tb=short`

Results:

- `sync_topic_metadata`
  - candidates changed: `7`
  - drafts changed: `1`
  - published changed: `4`
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
  - `checkout-conversion = 1`
  - `claude-platform = 1`
  - `harness-models = 1`

Current inventory summary:

- `published_count = 155`
- `draft_count = 44`
- `ready_validate_drafts = 12`
- `ready_write_drafts = 29`
- `candidate_count = 62`

## Conclusion

This round fully executed the "stop tuning, start stocking" direction.

- before this sprint: `pack_gap_total = 3`
- after this sprint: `pack_gap_total = 1`

Remaining hard gap:

- `ai-automation:agent-builder = 1`

That means `limit=18` is now almost fully blocked only by one more real non-redundant `agent-builder` ready slot.

## Release

- No new release in this round.
- Current release remains: `release-6fb115e4b88a`
