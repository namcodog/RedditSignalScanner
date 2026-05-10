# Boundary Guardrails Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 防止主仓、Hotpost 日运营、小程序子仓互相污染，让三条轨可以并行推进但不会误提交、误改派生产物或破坏小程序运营节奏。

**Architecture:** 不重构仓库结构，先用最小硬护栏解决最高风险：根仓本地 exclude、防误提交检查、任务轨声明、双仓状态检查、文档固化。小程序继续作为独立 git 仓库存在；主仓只通过 Hotpost release 和 `push_mini_snapshot.py` 向小程序派生数据。

**Tech Stack:** Git local exclude、Makefile / shell read-only guard、Markdown docs、现有 phase-log / specs / plans、可选 gstack freeze/guard 运行时边界。

---

## Plan Boundaries

这份计划是独立安全护栏计划，不写进根目录 `task_plan.md`。根目录 `task_plan.md` 保持给当天 Hotpost 出卡运营使用。

相关但不混用的计划：

- 边界设计文档：`docs/superpowers/specs/2026-05-06-project-boundary-operating-model-design.md`
- 本计划：`docs/superpowers/plans/2026-05-06-boundary-guardrails-plan.md`
- 日常出卡计划：根目录 `task_plan.md`
- 后续主项目复位计划：应另开 `docs/superpowers/plans/YYYY-MM-DD-mainline-reset-audit-plan.md`
- 小程序功能计划：应另开 `docs/superpowers/plans/YYYY-MM-DD-mini-<topic>-plan.md`

## File Structure

- Modify local only: `.git/info/exclude`
  - 作用：根仓本地忽略 `/hotpost-mini/`，防止误 `git add .` 把小程序目录纳入主仓。
- Create: `scripts/check-boundary-status.sh`
  - 作用：只读检查根仓和小程序子仓状态，不修改任何文件。
- Modify: `Makefile`
  - 作用：增加 `boundary-status` 只读入口，方便每次提交前运行。
- Modify: `docs/superpowers/specs/2026-05-06-project-boundary-operating-model-design.md`
  - 作用：补充“计划分流规则”和“提交前检查规则”。
- Optional Modify: `AGENTS.md`
  - 作用：用户确认后，把边界防污染规则升格为仓库级约束；不在第一步直接改，避免把临时计划过早写成硬规则。

## Task 1: Add Local Root Exclude For Mini Repo

**Files:**
- Modify local only: `.git/info/exclude`

- [x] **Step 1: Inspect current local exclude**

Run:

```bash
sed -n '1,120p' .git/info/exclude
```

Expected: file is readable. If `/hotpost-mini/` already exists, do not duplicate it.

- [x] **Step 2: Add the local ignore rule**

Run:

```bash
printf '\n# Local boundary guard: hotpost mini app is an independent git repo\n/hotpost-mini/\n' >> .git/info/exclude
```

Expected: `.git/info/exclude` contains `/hotpost-mini/`.

- [x] **Step 3: Verify root dry-run add will not stage mini app**

Run:

```bash
git add -n hotpost-mini 2>&1 | rg "add 'hotpost-mini/|add hotpost-mini/" || true
```

Expected: no `add 'hotpost-mini/...` paths appear.

## Task 2: Add Read-Only Boundary Status Script

**Files:**
- Create: `scripts/check-boundary-status.sh`

- [x] **Step 1: Create the script**

Create `scripts/check-boundary-status.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MINI_DIR="$ROOT_DIR/hotpost-mini/hotpost-mini-app"

echo "== root repo =="
git -C "$ROOT_DIR" status --short -- hotpost-mini || true

echo
echo "== mini repo =="
if [ -d "$MINI_DIR/.git" ]; then
  git -C "$MINI_DIR" status --short
  git -C "$MINI_DIR" branch --show-current
  git -C "$MINI_DIR" log -1 --oneline --decorate
else
  echo "missing mini repo: $MINI_DIR"
  exit 1
fi
```

- [x] **Step 2: Make it executable**

Run:

```bash
chmod +x scripts/check-boundary-status.sh
```

Expected: command exits 0.

- [x] **Step 3: Run it**

Run:

```bash
scripts/check-boundary-status.sh
```

Expected:

- Root section does not show staged `hotpost-mini` files.
- Mini section shows its own git status, branch, and latest commit.

## Task 3: Add Makefile Shortcut

**Files:**
- Modify: `Makefile`

- [x] **Step 1: Add help entry**

Add a help line near other operational checks:

```make
	@echo "  ${YELLOW}boundary-status${RESET} : Check root repo vs hotpost mini repo boundary status."
```

- [x] **Step 2: Add target**

Add:

```make
boundary-status:
	@./scripts/check-boundary-status.sh
```

- [x] **Step 3: Verify**

Run:

```bash
make boundary-status
```

Expected: same output as `scripts/check-boundary-status.sh`.

## Task 4: Update Boundary Design Doc

**Files:**
- Modify: `docs/superpowers/specs/2026-05-06-project-boundary-operating-model-design.md`

- [x] **Step 1: Add plan separation rule**

Add under `Operating Rules`:

```markdown
8. 不同轨道必须使用不同 plan 文件：日常出卡继续用根目录 `task_plan.md`；边界护栏、主项目复位、小程序功能各自放在 `docs/superpowers/plans/`，不能混写。
```

- [x] **Step 2: Add commit guard rule**

Add:

```markdown
9. 提交前必须运行 `make boundary-status`；主项目提交不得包含小程序子仓改动，小程序提交必须在子仓内完成。
```

- [x] **Step 3: Verify markdown diff**

Run:

```bash
git diff --check -- docs/superpowers/specs/2026-05-06-project-boundary-operating-model-design.md
```

Expected: no output.

## Task 5: Decide Whether To Promote Rules To AGENTS.md

**Files:**
- Optional Modify: `AGENTS.md`

- [x] **Step 1: Review whether the guardrails proved useful**

Run:

```bash
make boundary-status
git add -n hotpost-mini 2>&1 | rg "add 'hotpost-mini/|add hotpost-mini/" || true
```

Expected: no accidental mini app staging.

- [x] **Step 2: If user approves, add a short AGENTS.md rule**

Only after user approval, add a short section:

```markdown
### 主项目 / Hotpost / 小程序边界

- 根目录 `task_plan.md` 只用于当前日常运营，不混入边界护栏、主项目复位或小程序功能计划。
- `hotpost-mini/hotpost-mini-app` 是独立 git 小程序仓库；小程序提交必须在子仓内完成。
- 根仓提交前运行 `make boundary-status`；禁止在根仓用 `git add .` 混入小程序。
- `mini_snapshots` 和 `hotpost-mini/.../cloudfunctions/*/data` 是派生产物，只能由 `push_mini_snapshot.py` 写入。
```

- [x] **Step 3: Verify**

Run:

```bash
git diff --check -- AGENTS.md
```

Expected: no output.

## Task 6: Closeout Checks

**Files:**
- Read-only check

- [x] **Step 1: Root boundary check**

Run:

```bash
make boundary-status
```

Expected: root and mini status are clearly separated.

- [x] **Step 2: Root dry-run add check**

Run:

```bash
git add -n hotpost-mini 2>&1 | rg "add 'hotpost-mini/|add hotpost-mini/" || true
```

Expected: no output.

- [x] **Step 3: Mini repo clean check**

Run:

```bash
git -C hotpost-mini/hotpost-mini-app status --short
```

Expected: no output unless the active task is explicitly a mini app task.

- [x] **Step 4: Markdown whitespace check**

Run:

```bash
git diff --check -- scripts/check-boundary-status.sh Makefile docs/superpowers/specs/2026-05-06-project-boundary-operating-model-design.md docs/superpowers/plans/2026-05-06-boundary-guardrails-plan.md
```

Expected: no output.

## Plan Review

- This plan deliberately avoids submodule migration. Submodule can be revisited later, but the immediate risk is accidental staging and task-plan mixing.
- This plan does not modify Hotpost release data, mini snapshot data, cloud function bundle data, or小程序源码.
- This plan keeps root `task_plan.md` dedicated to daily Hotpost operations and creates separate files for boundary/mainline/mini plans.
