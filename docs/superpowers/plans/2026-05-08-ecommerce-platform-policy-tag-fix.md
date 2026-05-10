# Ecommerce Platform Policy Tag Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the user-facing “电商平台政策与风向” tag catch ecommerce platform policy/risk cards instead of only AI platform route topics.

**Architecture:** This is a taxonomy/config fix. Keep card data and publishing flow unchanged; update the interest-tag catalog contract and test it through the existing community recommendation matcher.

**Tech Stack:** Python pytest, JSON catalog at `backend/config/community_interest_tags.json`.

---

### Task 1: Lock The Expected Tag Contract

**Files:**
- Modify: `backend/tests/services/community/test_community_recommendation_preview.py`

- [ ] **Step 1: Add a failing regression test**

Add a test that loads the real catalog and proves `platform_policy_trends` includes `topic_cluster:unit-economics-and-platform-risk`, then verifies an FBA/platform-fee signal matches it.

- [ ] **Step 2: Run the test to verify RED**

Run:

```bash
PYTHONPATH=backend pytest backend/tests/services/community/test_community_recommendation_preview.py::test_platform_policy_trends_covers_ecommerce_platform_risk -q
```

Expected: fail because the current tag does not include the ecommerce platform-risk source ref or keywords.

### Task 2: Patch The Catalog

**Files:**
- Modify: `backend/config/community_interest_tags.json`

- [ ] **Step 1: Add ecommerce platform-risk source ref**

Add `topic_cluster:unit-economics-and-platform-risk` to `platform_policy_trends.source_refs`.

- [ ] **Step 2: Add precise ecommerce policy keywords**

Add only platform/risk terms such as `amazon`, `fba`, `etsy`, `shopify`, `fee`, `refund`, `returns`, `platform-risk`, and `unit-economics`. Do not move broad seller ops terms here.

### Task 3: Verify

- [ ] Run the targeted test.
- [ ] Run the community recommendation test slice.
- [ ] Run `git diff --check`.
