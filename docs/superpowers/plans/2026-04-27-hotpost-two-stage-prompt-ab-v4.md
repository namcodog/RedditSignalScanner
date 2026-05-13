# Hotpost Two-Stage Prompt A/B V4 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a read-only v4 Hotpost A/B runner where Gemini produces an English semantic brief and Qwen generates the final Chinese card fields.

**Architecture:** Keep production prompts untouched. Reuse the existing v1/v3 eval harness for samples, validation, reports, and retries; add one v4 runner that calls Gemini first, injects the brief into the Qwen prompt, and writes separate v4 artifacts.

**Tech Stack:** Python, pytest, existing `GeminiChatClient`, existing OpenRouter-compatible `OpenAIChatClient`, existing Hotpost card content validators.

---

### Task 1: Add V4 Tests

**Files:**
- Create: `backend/tests/scripts/evals/test_hotpost_three_tab_prompt_ab_v4.py`

- [x] Write tests for v4 model constants, semantic brief prompt requirements, brief injection, report title, and v3 rules inheritance.
- [x] Run the v4 test file and confirm it fails because the v4 runner does not exist.

### Task 2: Add V4 Runner

**Files:**
- Create: `backend/scripts/evals/run_hotpost_three_tab_prompt_ab_v4.py`

- [x] Implement constants:
  - `SEMANTIC_MODEL = "google/gemini-3.1-pro-preview"`
  - `WRITER_MODEL = "qwen/qwen3.6-max-preview"`
- [x] Implement `build_semantic_brief_messages()` so Gemini outputs JSON only, with `core_interpretation`, `evidence_boundary`, `chinese_writing_guidance`, and `field_guidance`.
- [x] Implement `generate_semantic_brief()` with `GeminiChatClient`.
- [x] Implement `build_writer_messages()` by taking the normal v3 prompt and appending the semantic brief before the Qwen generation call.
- [x] Implement `generate_one_two_stage()` and `run_experiment()` using v1 sample loading and validators, plus v3 banned patterns.
- [x] Write outputs to `reports/evals/hotpost_three_tab_prompt_ab_v4_two_stage_results.json` and `reports/evals/hotpost_three_tab_prompt_ab_v4_two_stage_report.md`.

### Task 3: Verify

**Files:**
- Test: `backend/tests/scripts/evals/test_hotpost_three_tab_prompt_ab_v1.py`
- Test: `backend/tests/scripts/evals/test_hotpost_three_tab_prompt_ab_v3.py`
- Test: `backend/tests/scripts/evals/test_hotpost_three_tab_prompt_ab_v4.py`

- [x] Run focused pytest for v1/v3/v4 eval scripts.
- [x] Run the v4 experiment with `--limit-per-lane 2`.
- [x] Confirm the report shows model route `google/gemini-3.1-pro-preview -> qwen/qwen3.6-max-preview`.
