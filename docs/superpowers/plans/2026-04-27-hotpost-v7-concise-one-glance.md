# Hotpost V7 Concise One-Glance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a read-only v7 Hotpost A/B runner that keeps the v6 model route but adds concise, accurate, one-glance Chinese writing constraints.

**Architecture:** Reuse the v4/v6 two-stage harness and sample loader. Add a v7 wrapper that injects a short writer overlay after the Gemini semantic brief and writes separate v7 artifacts.

**Tech Stack:** Python, pytest, existing Gemini and OpenRouter clients, existing Hotpost card validators.

---

### Task 1: Add V7 Tests

**Files:**
- Create: `backend/tests/scripts/evals/test_hotpost_three_tab_prompt_ab_v7.py`

- [x] Add tests for v7 model constants, concise writer overlay text, distinct report title, and distinct artifact names.
- [x] Run the v7 test file and confirm it fails because the v7 runner does not exist.

### Task 2: Add V7 Runner

**Files:**
- Create: `backend/scripts/evals/run_hotpost_three_tab_prompt_ab_v7.py`

- [x] Set `SEMANTIC_MODEL = "google/gemini-3-flash-preview"` and `WRITER_MODEL = "qwen/qwen3.6-max-preview"`.
- [x] Implement `build_concise_writer_messages()` so B variant asks for shorter, clearer fields without changing JSON structure or adding facts.
- [x] Reuse v4 generation and validation, but inject the v7 writer overlay before Qwen generation.
- [x] Write outputs to `reports/evals/hotpost_three_tab_prompt_ab_v7_concise_qwen_results.json` and `reports/evals/hotpost_three_tab_prompt_ab_v7_concise_qwen_report.md`.

### Task 3: Verify

**Files:**
- Test: `backend/tests/scripts/evals/test_hotpost_three_tab_prompt_ab_v7.py`
- Test: existing v1-v6 eval tests

- [x] Run focused v7 tests.
- [x] Run the full v7 experiment with `--limit-per-lane 2`.
- [x] Confirm 6 rows are produced, model route is `google/gemini-3-flash-preview -> qwen/qwen3.6-max-preview`, and variant errors are zero.
- [x] Run v1-v7 eval tests together.
