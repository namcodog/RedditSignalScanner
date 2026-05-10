# Hotpost Three Tab Prompt A/B Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run a small, repeatable A/B experiment for `signal`, `hot`, and `breakdown` card prompts so card copy becomes easier to understand without changing data structure, fields, candidate selection, or gates.

**Architecture:** Keep production prompts untouched until the experiment has evidence. Add one read-only eval runner that loads fixed samples from the latest release, generates baseline and variant outputs through the existing OpenRouter-backed LLM client, and writes a side-by-side report under `reports/evals/`.

**Tech Stack:** Python, existing hotpost card prompt builders, existing card content LLM router, existing release JSON files, pytest.

---

### Scope

**In scope**

- Read existing published cards from `backend/data/hotpost/releases/latest.json`.
- Sample `5` cards per lane: `signal`, `hot`, `breakdown`.
- Generate baseline output using current prompt builders.
- Generate variant output by appending a small plain-language overlay to the same prompts.
- Write machine-readable JSON and a compact Markdown comparison report.
- Add focused tests for sample selection, prompt overlay boundaries, and output path behavior.

**Out of scope**

- No production prompt asset changes in this first experiment pass.
- No JSON schema changes.
- No field changes.
- No candidate selection, freshness, publish gate, or mini app UI changes.
- No backfill or refresh of existing published cards.

### Files

- Create: `backend/scripts/evals/run_hotpost_three_tab_prompt_ab_v1.py`
- Test: `backend/tests/scripts/evals/test_hotpost_three_tab_prompt_ab_v1.py`
- Create: `docs/superpowers/plans/2026-04-27-hotpost-three-tab-prompt-ab.md`
- Output at runtime: `reports/evals/hotpost_three_tab_prompt_ab_v1_results.json`
- Output at runtime: `reports/evals/hotpost_three_tab_prompt_ab_v1_report.md`

### Tasks

- [ ] Add a read-only A/B runner that reconstructs drafts from latest release cards.
- [ ] Keep prompt variant as a small overlay inside the runner so production prompts are not changed before review.
- [ ] Add tests for lane sampling and report generation.
- [ ] Run focused tests.
- [ ] Run the A/B script with `--limit-per-lane 5`.
- [ ] Review generated report and decide whether to promote the overlay into real prompt assets.

### Acceptance

- The runner can run without mutating cards, releases, database, prompt assets, or publish state.
- It writes one JSON result file and one Markdown report.
- It uses the current OpenRouter route from existing environment variables.
- The variant keeps the same output fields as baseline for each lane.
- Focused tests pass.
