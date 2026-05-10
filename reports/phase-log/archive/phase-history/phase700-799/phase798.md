# Phase 798 - Continued Inventory Supplement at Limit 18

## Date

- 2026-04-13

## Scope

- Continue supplementing real inventory without changing:
  - planner
  - named topic budget
  - prompt
  - schema
- Try to close the last remaining `ai-automation:agent-builder = 1` gap.

## Actions

### 1. Added more real ready drafts

New drafts kept as valid inventory:

- `draft-cand-ai-automation-1sjgwd1-validate`
  - pack: `agent-builder`
  - named topic: `prompt-engineering`
  - lane: `hot`
- `draft-cand-ai-automation-1sfwj9j-validate`
  - pack: `agent-builder`
  - named topic: `harness-models`
  - lane: `hot`
- `draft-cand-ai-automation-1sjtuv4-validate`
  - pack: `upstream-winds`
  - unnamed
  - lane: `hot`
- `draft-cand-business-growth-ops-1sjzbzx-validate`
  - pack: `organic-discovery`
  - unnamed
  - lane: `signal`

### 2. Removed a failed temporary draft

- `draft-cand-business-growth-ops-1sjj9o8-validate`
  - intended to replace `checkout-conversion`
  - did not improve the `publish_list`
  - deleted to avoid leaving dirty state

### 3. Reverted one ineffective supply-config experiment

- Temporarily added `open-source-projects` into `agent-builder.topic_clusters`
- Re-ran AI harvest
- Result: it did not produce durable non-named `agent-builder` exposure
- Final action: reverted the YAML change

## Validation

Commands:

- `.venv/bin/python backend/scripts/hotpost/review_cards.py seed ... --live`
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

Inventory summary:

- `draft_count = 48`
- `ready_validate_drafts = 15`
- `ready_write_drafts = 29`
- `candidate_count = 62`

## Conclusion

This continuation added more valid inventory, but did not close the final gap.

Current remaining hard gap:

- `ai-automation:agent-builder = 1`

Current root cause is no longer raw inventory count.
It is the competition among the three current named-topic slots:

- `harness-models`
- `claude-platform`
- `checkout-conversion`

The new inventory is real and useful, but it still does not displace the current three-slot equilibrium inside the `limit=18` publish window.

## Release

- No new release in this round.
- Current release remains: `release-6fb115e4b88a`
