# Hotpost Community Discovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an isolated experimental community layer and a read-only audit report so discovery results can later feed the semantic library without polluting daily publishing.

**Architecture:** Experimental communities live in `hotpost_supply_discovery_v2.yaml` as a probe-only layer. Default `daily_collect.py` and normal search specs exclude them; explicit audit/spec calls can include them. The first audit only reads current candidates/drafts/published/rejections and writes a report, with no DB writes and no automatic promotion.

**Tech Stack:** Python, YAML config, existing Hotpost JSON stores, pytest.

---

### Task 1: Config Isolation

**Files:**
- Modify: `backend/config/hotpost_supply_discovery_v2.yaml`
- Modify: `backend/app/services/hotpost/hotpost_supply_projection.py`
- Modify: `backend/app/services/hotpost/reddit_search_spec_builder.py`
- Test: `backend/tests/services/hotpost/test_reddit_search_spec_builder.py`

- [x] Add `experimental_communities` under selected topic clusters.
- [x] Add `include_experimental=False` to topic-pack projection and reddit spec building.
- [x] Verify normal `build_reddit_search_specs(scope)` excludes experimental communities.
- [x] Verify `build_reddit_search_specs(scope, include_experimental=True)` includes them with small probe limits.

### Task 2: Read-Only Audit Report

**Files:**
- Create: `backend/app/services/hotpost/community_discovery_audit.py`
- Create: `backend/scripts/hotpost/audit_community_discovery.py`
- Test: `backend/tests/services/hotpost/test_community_discovery_audit.py`

- [x] Read experimental communities from config.
- [x] Count `collected_candidates`, `draft_count`, `published_count`, `reject_count`, `duplicate_count`, `new_topic_count`.
- [x] Add semantic feed fields: `frequent_entities`, `pain_solution_tags`, `sample_titles`, `product_tags`.
- [x] Return `suggested_action` only as advice: `promote_candidate`, `keep_testing`, `downgrade`, `reject`.
- [x] Write report to `reports/community-governance/community-discovery-audit-YYYY-MM-DD.json` only when script is run.

### Task 3: Verification

**Files:**
- Update tests from Task 1 and Task 2 only.

- [x] Run `pytest backend/tests/services/hotpost/test_reddit_search_spec_builder.py backend/tests/services/hotpost/test_community_discovery_audit.py`.
- [x] Run `python backend/scripts/hotpost/audit_community_discovery.py --date 2026-05-08`.
- [x] Run `git diff --check`.

### Verification Note

- `2026-05-08` verification: `19 passed`.
- Audit report regenerated at `reports/community-governance/community-discovery-audit-2026-05-08.json`, `row_count=16`.
- Current audit result is all `keep_testing`; the probe layer exists, but it has not yet produced candidate/draft/published evidence.

### Guardrails

- `experimental_communities` is not `primary_communities`.
- `experimental_communities` is not `community_pool`.
- Daily collect default does not include experimental communities.
- First version does not write DB, candidates, drafts, published cards, or YAML promotion changes.
- First version does not auto-promote.
