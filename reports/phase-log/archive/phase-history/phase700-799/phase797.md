# Phase 797 - Final Agent-Builder Push at Limit 18

## Date

- 2026-04-13

## Scope

- Continue from `phase796`.
- Keep all hard boundaries:
  - no planner change
  - no named topic budget change
  - no prompt change
  - no schema change
- Only try to close the last remaining `limit=18` hard gap:
  - `ai-automation:agent-builder = 1`

## Actions

### 1. Seeded stronger `agent-builder` inventory

New drafts created:

- `draft-cand-ai-automation-1sjgwd1-validate`
  - pack: `agent-builder`
  - named topic: `prompt-engineering`
  - lane: `hot`
- `draft-cand-ai-automation-1sfwj9j-validate`
  - pack: `agent-builder`
  - named topic: `harness-models`
  - lane: `hot`

### 2. Tried to free a named-topic slot

Two additional experiments were run:

- `draft-cand-business-growth-ops-1sjj9o8-validate`
  - goal: use an unnamed `funnel-conversion` ready draft to squeeze out `checkout-conversion`
  - result: did not improve the final plan and was deleted
- `draft-cand-ai-automation-1sjtuv4-validate`
  - goal: use an unnamed `upstream-winds` hot draft to squeeze out `claude-platform`
  - result: increased ready stock, but did not change the final `publish_list`

## Validation

Commands:

- `.venv/bin/python backend/scripts/hotpost/review_cards.py seed cand-ai-automation-1sjgwd1 validate --live`
- `.venv/bin/python backend/scripts/hotpost/review_cards.py seed cand-ai-automation-1sfwj9j validate --live`
- `.venv/bin/python backend/scripts/hotpost/review_cards.py seed cand-ai-automation-1sjtuv4 validate --live`
- `.venv/bin/python backend/scripts/hotpost/run_offline_publish_plan.py --limit 18 --output backend/tmp/offline-publish-plan-18.json`

Current `offline_publish_plan(limit=18)` still holds:

- lane:
  - `signal = 10`
  - `hot = 5`
  - `breakdown = 3`
- scope:
  - `ai-automation = 6`
  - `business-growth-ops = 6`
  - `ecommerce-sellers = 6`
- named topic:
  - `harness-models = 1`
  - `claude-platform = 1`
  - `checkout-conversion = 1`

Inventory summary now:

- `draft_count = 47`
- `ready_validate_drafts = 15`
- `ready_write_drafts = 29`
- `candidate_count = 78`

Current pack mix in `publish_list`:

- `ai-automation:agent-builder = 1`
- `ai-automation:tools-efficiency = 3`
- `ai-automation:upstream-winds = 2`
- `business-growth-ops:paid-economics = 2`
- `business-growth-ops:organic-discovery = 2`
- `business-growth-ops:funnel-conversion = 2`
- `ecommerce-sellers:selection-signals = 4`
- `ecommerce-sellers:category-winds = 1`
- `ecommerce-sellers:kill-signals = 1`

## Conclusion

This round added more real ready inventory, but did not close the final planning gap.

- the remaining hard gap still is:
  - `ai-automation:agent-builder = 1`

Why it did not close:

- every new `agent-builder` item that can actually compete is still bound to named-topic slots
- current `named topic` winners remain:
  - `harness-models`
  - `claude-platform`
  - `checkout-conversion`
- the extra `prompt-engineering` and unnamed AI hot draft increased inventory, but did not displace the current three-slot equilibrium

## Release

- No new release in this round.
- Current release remains: `release-6fb115e4b88a`
