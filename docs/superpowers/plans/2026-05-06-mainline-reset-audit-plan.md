# Mainline Reset Audit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 审计 RedditSignalScanner 主项目真实状态，分清脏仓来源、识别过度工程化、确认最短主链验收路径，并给出下一步最小修复/删减建议。

**Architecture:** 这是只读优先的复位审计，不做业务代码修改。先保护边界，再分层 dirty worktree，再用 phase-log + Serena + targeted commands 画出主项目主链，最后输出一份审计报告。Hotpost 日运营和小程序产品轨只作为边界影响项，不进入本轮修复范围。

**Tech Stack:** Git, Makefile, Serena MCP, pytest/vitest targeted checks, ripgrep, Markdown audit report.

---

## Plan Boundaries

本计划单独管理主项目复位审计，不写进根目录 `task_plan.md`。

不要混用：

- 日常出卡计划：根目录 `task_plan.md`
- 边界护栏计划：`docs/superpowers/plans/2026-05-06-boundary-guardrails-plan.md`
- 小程序功能计划：未来另开 `docs/superpowers/plans/YYYY-MM-DD-mini-<topic>-plan.md`

本计划默认不改：

- `hotpost-mini/hotpost-mini-app`
- `backend/data/hotpost/mini_snapshots`
- `hotpost-mini/.../cloudfunctions/*/data`
- Hotpost candidates / drafts / releases

## Current Facts To Preserve

- 根仓当前极脏：`git status --short | wc -l` 返回约 `1474`。
- 状态分布：`720 D / 43 M / 711 ??`。
- 目录分布头部：`reports` 约 `973`，`backend` 约 `382`，`frontend` 约 `38`。
- 小程序子仓当前干净：`make boundary-status` 显示 mini repo 在 `main`，最新提交 `6521ffa feat(mini): expose release communities`。
- phase-log 当前状态仍偏 Hotpost 日运营；主项目复位是新计划，不能假装 phase-log 已经完成切换。

## Deliverables

- Create: `reports/audits/mainline-reset-audit-2026-05-06.md`
- Optional update after user confirmation: `reports/phase-log/CURRENT_STATUS.md`
- Optional update after user confirmation: `reports/phase-log/OPEN_ITEMS.md`
- Optional update after user confirmation: `reports/phase-log/INDEX.md`

## Execution Status

- 2026-05-07: Tasks 0-7 executed. Audit report created at `reports/audits/mainline-reset-audit-2026-05-06.md`.
- Boundary verification passed: `make boundary-status`; mini repo `git status --short` is empty.
- Backend smoke passed: `70 passed, 1 skipped, 22 warnings`.
- Frontend smoke passed: `5 files passed / 27 tests passed`.
- Task 8 not executed because phase-log update requires user confirmation after reviewing audit findings.

## Task 0: Boundary Preflight

**Files:**
- Read-only

- [ ] **Step 1: Check root/mini boundary**

Run:

```bash
make boundary-status
```

Expected:

- Root section shows no `hotpost-mini` staged paths.
- Mini section shows branch and latest commit.

- [ ] **Step 2: Confirm mini app is not being staged by root**

Run:

```bash
git add -n hotpost-mini 2>&1 | rg "add 'hotpost-mini/|add hotpost-mini/" || true
```

Expected: no output.

- [ ] **Step 3: If boundary fails, stop**

If either command shows mini app files in root staging/dry-run, stop the audit and fix boundary guardrails first.

## Task 1: Dirty Worktree Inventory

**Files:**
- Create section in `reports/audits/mainline-reset-audit-2026-05-06.md`

- [ ] **Step 1: Create audit report skeleton**

Create `reports/audits/mainline-reset-audit-2026-05-06.md`:

```markdown
# Mainline Reset Audit

Date: 2026-05-06
Scope: RedditSignalScanner mainline only

## Executive Summary

## Dirty Worktree Inventory

## Mainline Product Map

## Over-Engineering Findings

## Test And Runtime Evidence

## Data Boundary Evidence

## Recommended Next Moves

## Not Touched

```

- [ ] **Step 2: Record dirty count**

Run:

```bash
git status --short | wc -l
```

Expected: record the number in `Dirty Worktree Inventory`.

- [ ] **Step 3: Record status type distribution**

Run:

```bash
git status --short | cut -c1-2 | sort | uniq -c
```

Expected: record counts for modified, deleted, and untracked files.

- [ ] **Step 4: Record directory distribution**

Run:

```bash
git status --short | awk '{path=$2; split(path,a,"/"); print a[1]}' | sort | uniq -c | sort -nr | sed -n '1,30p'
```

Expected: record top dirty directories.

- [ ] **Step 5: Classify dirty worktree into buckets**

Write these buckets in the report:

```markdown
| Bucket | Evidence | Action |
| --- | --- | --- |
| Boundary guardrails | AGENTS.md, Makefile, scripts/check-boundary-status.sh, new specs/plans | Keep separate commit |
| Phase-log/archive governance | reports/phase-log deletions/untracked archive entries | Do not touch during mainline audit |
| Mainline code | backend/app/services/analysis, report, crawl, community; frontend report/input pages | Audit only |
| Hotpost code/data | backend/app/services/hotpost, backend/scripts/hotpost, hotpost docs | Boundary-only, no cleanup |
| Mini app | hotpost-mini/hotpost-mini-app | Must remain clean |
```

## Task 2: Phase-Log And Historical Truth Source Review

**Files:**
- Modify: `reports/audits/mainline-reset-audit-2026-05-06.md`

- [ ] **Step 1: Read current phase-log entry points**

Run:

```bash
sed -n '1,220p' reports/phase-log/CURRENT_STATUS.md
sed -n '260,410p' reports/phase-log/OPEN_ITEMS.md
sed -n '1,100p' reports/phase-log/MILESTONES.md
sed -n '1,120p' reports/phase-log/INDEX.md
```

Expected: extract only current mainline-relevant claims, not every Hotpost detail.

- [ ] **Step 2: Read mainline historical summaries**

Run:

```bash
sed -n '1,180p' reports/phase-log/PHASE_SUMMARY_200_399.md
sed -n '1,180p' reports/phase-log/PHASE_SUMMARY_400_599.md
sed -n '1,180p' reports/phase-log/PHASE_SUMMARY_600_799.md
sed -n '1,180p' reports/phase-log/PHASE_SUMMARY_800_NOW.md
```

Expected: record the durable lessons:

- no silent fallback
- data contract and display contract must separate
- Full A / report quality depends on data bottom, not prompt only
- Hotpost is current operational product but not the whole repo

- [ ] **Step 3: State the current conflict**

Write:

```markdown
Current conflict: phase-log says active mainline is Hotpost daily operations, while this audit is reopening the original RedditSignalScanner mainline. This audit must not silently rewrite current status until findings are verified.
```

## Task 3: Mainline Product Map

**Files:**
- Modify: `reports/audits/mainline-reset-audit-2026-05-06.md`

- [ ] **Step 1: Map frontend routes**

Run:

```bash
sed -n '1,140p' frontend/src/router/index.tsx
sed -n '1,120p' frontend/src/router/routes.ts
```

Expected: record route groups:

- main product: `/`, `/progress/:taskId`, `/report/:taskId`, `/standard-report/:slug`, `/insights`, `/admin/...`
- Hotpost web operations: `/hotpost...`

- [ ] **Step 2: Map backend API routers**

Run:

```bash
sed -n '1,180p' backend/app/api/v1/api.py
```

Expected: record router groups:

- mainline: `analyze`, `decision_units`, `tasks`, `stream`, `reports`, `export`
- hotpost: `hotpost*`, `hotpost_wx_auth`, `hotpost_wx_favorites`

- [ ] **Step 3: Use Serena for core Python symbols**

Use Serena `get_symbols_overview` on:

```text
backend/app/api/v1/endpoints/analyze.py
backend/app/api/v1/endpoints/reports.py
backend/app/services/analysis/analysis_engine.py
backend/app/services/report/report_service.py
```

Expected: record top-level functions/classes and identify the shortest path from request to report.

- [ ] **Step 4: Draw the current mainline chain**

Write this diagram, then adjust based on evidence:

```text
InputPage
  -> POST /api/analyze
  -> analysis task / stream status
  -> AnalysisEngine / collection / semantic / facts
  -> ReportService
  -> ReportPage / StandardReportPage
```

## Task 4: Over-Engineering Audit

**Files:**
- Modify: `reports/audits/mainline-reset-audit-2026-05-06.md`

- [ ] **Step 1: Identify large files in mainline scope**

Run:

```bash
find backend/app/services/analysis backend/app/services/report backend/app/services/community backend/app/services/crawl backend/app/api/v1/endpoints frontend/src/pages frontend/src/services -type f \( -name '*.py' -o -name '*.tsx' -o -name '*.ts' \) -print0 | xargs -0 wc -l | sort -nr | sed -n '1,40p'
```

Expected: record top files over 300 lines and whether they are true domain centers or accidental God objects.

- [ ] **Step 2: Search for complexity smells**

Run:

```bash
rg -n "fallback|legacy|deprecated|TODO|FIXME|Any|type: ignore|except Exception|pass$" backend/app/services/analysis backend/app/services/report backend/app/services/community backend/app/services/crawl backend/app/api/v1/endpoints frontend/src/pages frontend/src/services | sed -n '1,200p'
```

Expected: group findings into:

- legitimate compatibility layer
- suspicious silent fallback
- type debt
- historical legacy still in active path

- [ ] **Step 3: Check duplicate service families**

Run:

```bash
find backend/app/services -maxdepth 2 -type d | sort | rg "analysis|report|community|crawl|discovery|semantic|hotpost"
```

Expected: identify overlapping service families, especially multiple community discovery/truth-source/crawl entry points.

- [ ] **Step 4: Classify each over-engineering finding**

Use this table:

```markdown
| Finding | Evidence | User impact | Keep / simplify / delete later | Confidence |
| --- | --- | --- | --- | --- |
```

Do not propose deletion without evidence that the path is unused.

## Task 5: Test And Runtime Evidence

**Files:**
- Modify: `reports/audits/mainline-reset-audit-2026-05-06.md`

- [ ] **Step 1: Identify exact test entry points**

Run:

```bash
rg --files backend/tests/services/analysis backend/tests/services/report backend/tests/api frontend/src/pages/__tests__ frontend/src/tests/contract | sed -n '1,180p'
```

Expected: record existing tests for analyze/report/mainline frontend.

- [ ] **Step 2: Run backend mainline smoke tests**

Run:

```bash
PYTHONPATH=backend pytest -q backend/tests/api/test_analyze.py backend/tests/api/test_reports.py backend/tests/services/report/test_report_service.py backend/tests/services/analysis/test_analysis_engine.py
```

Expected:

- If pass: record pass count.
- If fail: record failing test names and first failure reason. Do not fix in this audit.

- [ ] **Step 3: Run frontend mainline smoke tests**

Run:

```bash
cd frontend && npm test -- --run src/pages/__tests__/InputPage.test.tsx src/pages/__tests__/ReportPage.test.tsx src/pages/__tests__/ReportFlow.integration.test.tsx src/tests/contract/report-api.contract.test.ts src/tests/contract/report-schema.contract.test.ts
```

Expected:

- If pass: record pass count.
- If fail: record failing test names and first failure reason. Do not fix in this audit.

- [ ] **Step 4: Do not run E2E yet**

Record:

```markdown
E2E is deferred until smoke tests and dirty-worktree ownership are understood.
```

## Task 6: Data Boundary Audit

**Files:**
- Modify: `reports/audits/mainline-reset-audit-2026-05-06.md`

- [ ] **Step 1: Inspect DB rules**

Run:

```bash
rg -n "ALLOW_GOLD_DB|reddit_signal_scanner_dev|reddit_signal_scanner_test|reddit_signal_scanner" backend docs AGENTS.md | sed -n '1,160p'
```

Expected: record current Gold / Dev / Test DB contract.

- [ ] **Step 2: Inspect configuration defaults**

Run:

```bash
sed -n '1,220p' backend/app/core/config.py
sed -n '1,200p' backend/tests/core/test_config_defaults.py
```

Expected: record whether default config points to safe dev/test behavior.

- [ ] **Step 3: Record audit stance**

Write:

```markdown
This audit must not write Gold DB. Any data repair later must target Dev DB or Test DB unless explicitly approved.
```

## Task 7: Recommendations And Next Plan Split

**Files:**
- Modify: `reports/audits/mainline-reset-audit-2026-05-06.md`

- [ ] **Step 1: Write recommendations**

Use these categories:

```markdown
## Recommended Next Moves

### P0: Restore a shortest mainline acceptance chain

### P1: Reduce over-engineering where it blocks acceptance

### P2: Archive or quarantine historical clutter

### Keep Separate: Hotpost daily operations

### Keep Separate: Mini app product work
```

- [ ] **Step 2: Decide next plan files**

If findings confirm a concrete fix area, create one of these later:

- `docs/superpowers/plans/YYYY-MM-DD-mainline-acceptance-fix-plan.md`
- `docs/superpowers/plans/YYYY-MM-DD-mainline-overengineering-reduction-plan.md`
- `docs/superpowers/plans/YYYY-MM-DD-phase-log-dirty-worktree-cleanup-plan.md`

Do not mix these into this audit plan.

- [ ] **Step 3: Final boundary verification**

Run:

```bash
make boundary-status
git -C hotpost-mini/hotpost-mini-app status --short
```

Expected: mini repo remains clean.

## Task 8: Optional Phase-Log Update After User Confirmation

**Files:**
- Optional Modify: `reports/phase-log/CURRENT_STATUS.md`
- Optional Modify: `reports/phase-log/OPEN_ITEMS.md`
- Optional Modify: `reports/phase-log/INDEX.md`

- [ ] **Step 1: Ask for confirmation**

Only update phase-log if the user confirms the audit findings should become current project state.

- [ ] **Step 2: Update four-entry status, not new phase**

If confirmed, update the four-entry files. Do not create a new `phase{N}.md` unless the audit proves a mainline priority change or root-cause conclusion.

- [ ] **Step 3: Verify**

Run:

```bash
git diff --check -- reports/phase-log/CURRENT_STATUS.md reports/phase-log/OPEN_ITEMS.md reports/phase-log/INDEX.md
```

Expected: no output.

## Self Review

- This plan treats the dirty worktree as a first-class audit input, not a cleanup side quest.
- This plan explicitly audits over-engineering before proposing refactors.
- This plan protects Hotpost daily operations and mini app integrity.
- This plan produces an audit report before any implementation plan.
- This plan does not use root `task_plan.md`.
