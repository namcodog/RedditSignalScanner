# Hotpost V13 Full Run Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 用 V12/V13 已认可的组合模型与语义规则，对 Hotpost 已发布卡和后续运营出卡做可审核的全量刷新，不直接污染历史发布真相源。

**Architecture:** 新增一个只读优先的 `published V13 shadow refresh` 入口，先按 published cards 分片生成 before/after plan 和人工审核报告。审核通过后只允许通过 `apply-plan` 精确写回最新 published 投影，不直接手改 release 历史文件，不接入生产实时 repair pass。

**Tech Stack:** Python async scripts, existing Hotpost card storage APIs, `deepseek/deepseek-v4-flash` semantic model, `xiaomi/mimo-v2.5-pro` writer model, pytest.

---

### Task 1: Build Published V13 Shadow Runner

**Files:**
- Create: `backend/scripts/hotpost/run_v13_published_shadow_refresh.py`
- Test: `backend/tests/scripts/hotpost/test_v13_published_shadow_refresh.py`

- [ ] **Step 1: Write tests for safe defaults**

Test expectations:
- default mode writes a plan and report only
- no `--apply` behavior exists
- selector supports `--lane`, `--limit`, `--offset`, `--card-id`
- default profile is `hotpost_v13_title_standalone`
- per-card timeout is enabled

Run:

```bash
SKIP_DB_RESET=1 PYTHONPATH=. pytest backend/tests/scripts/hotpost/test_v13_published_shadow_refresh.py -q
```

Expected first result: fail because the script does not exist yet.

- [ ] **Step 2: Implement minimal runner**

Runner behavior:
- load cards only through `load_published_cards()`
- select cards by `card_id / lane / limit / offset`
- call the same V13 generation chain used by `backend/scripts/evals/run_hotpost_v13_shadow_new_samples.py`
- write:
  - `reports/evals/hotpost_v13_published_shadow_<timestamp>.json`
  - `reports/evals/hotpost_v13_published_shadow_<timestamp>.md`
- include for each card:
  - original card
  - refreshed candidate card
  - changed fields
  - V11/V12/V13 issue counts
  - error or timeout

- [ ] **Step 3: Add resume support**

Use `--resume-from <json>` to skip card ids that already have a successful refreshed candidate. This is required because 437 cards with external LLM calls will not be reliable as one uninterrupted job.

- [ ] **Step 4: Run tests**

```bash
SKIP_DB_RESET=1 PYTHONPATH=. pytest backend/tests/scripts/hotpost/test_v13_published_shadow_refresh.py -q
```

Expected: pass.

---

### Task 2: Add Apply-Plan Gate

**Files:**
- Modify: `backend/scripts/hotpost/run_v13_published_shadow_refresh.py`
- Test: `backend/tests/scripts/hotpost/test_v13_published_shadow_refresh.py`

- [ ] **Step 1: Write apply-plan tests**

Test expectations:
- `--apply-plan` accepts only a generated plan with `kind=hotpost_v13_published_shadow_refresh`
- requires `--approved-by-human`
- uses `merge_published_cards()`
- refuses plans with errors unless `--allow-error-free-only` passes
- preserves identity fields: `card_id`, `published_at`, `source_link`, `lane`, `card_type`

- [ ] **Step 2: Implement apply-plan**

Apply behavior:
- no model calls
- no selector flags allowed
- no release history editing
- writes exact refreshed cards from plan through storage API
- prints merged count and skipped count

- [ ] **Step 3: Run tests**

```bash
SKIP_DB_RESET=1 PYTHONPATH=. pytest backend/tests/scripts/hotpost/test_v13_published_shadow_refresh.py -q
```

Expected: pass.

---

### Task 3: Pilot Run

**Files:**
- Output only: `reports/evals/`
- No production writes

- [ ] **Step 1: Run 10-card mixed pilot**

```bash
PYTHONPATH=. python backend/scripts/hotpost/run_v13_published_shadow_refresh.py \
  --limit 10 \
  --workers 1 \
  --output-prefix reports/evals/hotpost_v13_fullrun_pilot_10
```

Acceptance:
- 10 selected
- 0 model/auth errors
- no card hangs beyond per-card timeout
- report includes before/after for title, summary_line, why_now, detail fields

- [ ] **Step 2: Human review**

Review focus:
- title can stand alone
- no title-party compression
- no action advice mixed into why_now
- no dead-object subject like “工具开始强调”
- no English/product spacing issue
- no field structure changes

- [ ] **Step 3: Fix only proven rule gaps**

If pilot exposes repeated defects, update prompt/rules/detectors first, then rerun pilot. Do not move to all cards until pilot is clean.

---

### Task 4: Lane Sharded Shadow Run

**Files:**
- Output only: `reports/evals/`

Current published count baseline:
- total: 437
- signal: 205
- hot: 104
- breakdown: 95
- lane empty / old structure: 33

- [ ] **Step 1: Run signal in shards**

```bash
PYTHONPATH=. python backend/scripts/hotpost/run_v13_published_shadow_refresh.py --lane signal --limit 50 --offset 0 --workers 1 --output-prefix reports/evals/hotpost_v13_fullrun_signal_000
PYTHONPATH=. python backend/scripts/hotpost/run_v13_published_shadow_refresh.py --lane signal --limit 50 --offset 50 --workers 1 --output-prefix reports/evals/hotpost_v13_fullrun_signal_050
PYTHONPATH=. python backend/scripts/hotpost/run_v13_published_shadow_refresh.py --lane signal --limit 50 --offset 100 --workers 1 --output-prefix reports/evals/hotpost_v13_fullrun_signal_100
PYTHONPATH=. python backend/scripts/hotpost/run_v13_published_shadow_refresh.py --lane signal --limit 50 --offset 150 --workers 1 --output-prefix reports/evals/hotpost_v13_fullrun_signal_150
PYTHONPATH=. python backend/scripts/hotpost/run_v13_published_shadow_refresh.py --lane signal --limit 50 --offset 200 --workers 1 --output-prefix reports/evals/hotpost_v13_fullrun_signal_200
```

- [ ] **Step 2: Run hot in shards**

```bash
PYTHONPATH=. python backend/scripts/hotpost/run_v13_published_shadow_refresh.py --lane hot --limit 50 --offset 0 --workers 1 --output-prefix reports/evals/hotpost_v13_fullrun_hot_000
PYTHONPATH=. python backend/scripts/hotpost/run_v13_published_shadow_refresh.py --lane hot --limit 50 --offset 50 --workers 1 --output-prefix reports/evals/hotpost_v13_fullrun_hot_050
PYTHONPATH=. python backend/scripts/hotpost/run_v13_published_shadow_refresh.py --lane hot --limit 50 --offset 100 --workers 1 --output-prefix reports/evals/hotpost_v13_fullrun_hot_100
```

- [ ] **Step 3: Run breakdown in shards**

```bash
PYTHONPATH=. python backend/scripts/hotpost/run_v13_published_shadow_refresh.py --lane breakdown --limit 50 --offset 0 --workers 1 --output-prefix reports/evals/hotpost_v13_fullrun_breakdown_000
PYTHONPATH=. python backend/scripts/hotpost/run_v13_published_shadow_refresh.py --lane breakdown --limit 50 --offset 50 --workers 1 --output-prefix reports/evals/hotpost_v13_fullrun_breakdown_050
```

- [ ] **Step 4: Treat old lane-empty cards separately**

Do not mix the 33 lane-empty cards into the first full run. First export them into a review report and decide whether they are still worth preserving. Old structure cards are higher risk because field semantics may not map cleanly.

---

### Task 5: Quality Rollup And Human Approval

**Files:**
- Create: `reports/evals/hotpost_v13_fullrun_rollup_<timestamp>.md`

- [ ] **Step 1: Build rollup**

Rollup must include:
- total selected / generated / failed / timed out
- changed field counts
- V13 title residual issue count
- V12 density residual issue count
- banned pattern hits
- 30-card review sample: 10 signal, 10 hot, 10 breakdown

- [ ] **Step 2: Human approval checkpoint**

Approval condition:
- model error rate below 3%
- title residual issue rate below 2%
- no repeated structural field corruption
- manual review sample passes
- user explicitly approves apply-plan

---

### Task 6: Apply Approved Plan

**Files:**
- Reads: approved full-run plan JSON
- Writes: latest published projection only through `merge_published_cards()`
- Then writes mini snapshot through existing script

- [ ] **Step 1: Apply plan**

```bash
PYTHONPATH=. python backend/scripts/hotpost/run_v13_published_shadow_refresh.py \
  --apply-plan reports/evals/<approved_plan>.json \
  --approved-by-human
```

- [ ] **Step 2: Push mini snapshot**

```bash
PYTHONPATH=. python backend/scripts/hotpost/push_mini_snapshot.py
```

- [ ] **Step 3: Verify release and mini sync**

```bash
PYTHONPATH=. python backend/scripts/hotpost/check_mini_release_sync.py
```

- [ ] **Step 4: Record phase-log**

Create a short `reports/phase-log/phaseNNNN.md` with:
- approved plan path
- merged count
- mini snapshot result
- any skipped cards
- next operating rule

---

## Operating Decision

Recommended rollout:

1. Use V13 profile for new daily operational output first.
2. Run 10-card published pilot.
3. Run lane-sharded full shadow for all normal-lane published cards.
4. Human-review rollup.
5. Apply only after explicit approval.
6. Handle lane-empty legacy cards as a separate cleanup decision.

Do not apply all 437 cards directly from model output without a plan file and human checkpoint.
