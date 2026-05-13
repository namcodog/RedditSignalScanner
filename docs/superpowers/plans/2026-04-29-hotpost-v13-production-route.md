# Hotpost V13 Production Route Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make daily Hotpost card generation use the `hotpost_v13_title_standalone` profile by default while keeping hot controversy charts on their independent model route.

**Architecture:** `generate_card_content()` becomes the single production switch point for V13 text generation. Hot controversy chart generation remains separate, but its model/version/timeout move from hard-coded constants into `hotpost_quality.yaml` so governance is explicit.

**Tech Stack:** Python, pytest, FastAPI service modules, YAML configuration.

---

### Task 1: Production Profile Governance

**Files:**
- Modify: `backend/config/hotpost_quality.yaml`
- Modify: `backend/app/services/hotpost/card_content_generator.py`
- Modify: `backend/app/services/hotpost/card_content_llm_router.py`
- Test: `backend/tests/services/hotpost/test_card_content_generator.py`
- Test: `backend/tests/services/hotpost/test_card_content_llm_router.py`

- [ ] Add tests proving `production_profile_id` reads as `hotpost_v13_title_standalone`.
- [ ] Add tests proving hot lane generation uses `deepseek/deepseek-v4-flash -> xiaomi/mimo-v2.5-pro` when the production profile is active.
- [ ] Add profile resolver code that hard-fails on unknown production profile.
- [ ] Route production profile before lane / pack overrides.

### Task 2: V13 Text Generation Path

**Files:**
- Modify: `backend/app/services/hotpost/card_content_generator.py`
- Test: `backend/tests/services/hotpost/test_card_content_generator.py`

- [ ] Generate a semantic brief with the profile semantic model.
- [ ] Append the semantic brief to the existing hot/signal writer prompt.
- [ ] Generate the card payload with the profile writer model and existing field schema.
- [ ] Preserve existing validation, quote reordering, final readout, and breakdown upgrade behavior.

### Task 3: Hot Controversy Model Governance

**Files:**
- Modify: `backend/config/hotpost_quality.yaml`
- Modify: `backend/app/services/hotpost/hot_controversy_llm.py`
- Test: `backend/tests/services/hotpost/test_hot_controversy_llm.py`

- [ ] Add `hot_controversy` config with model, summary version, and timeout.
- [ ] Load config inside `hot_controversy_llm.py`.
- [ ] Keep default model as `google/gemini-2.5-flash-lite`.
- [ ] Do not connect controversy chart generation to V13 text profile.

### Task 4: Verification and Phase Log

**Files:**
- Modify: `reports/phase-log/phase1040.md` or next available phase file.

- [ ] Run targeted pytest for LLM router, card generator, and hot controversy tests.
- [ ] Record the state change in phase-log only after tests pass.
