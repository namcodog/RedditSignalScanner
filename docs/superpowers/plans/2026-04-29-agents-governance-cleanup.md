# AGENTS Governance Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove contradictory and over-heavy governance rules from `AGENTS.md` while preserving the current project operating contract.

**Architecture:** Treat `AGENTS.md` as a thin startup and hard-boundary contract. Keep fast-changing hotpost details in SOP/reference docs by link, and keep only durable gates and routing rules in this file.

**Tech Stack:** Markdown governance file, shell text checks, key-os CLI validation.

---

## File Structure

- Modify: `AGENTS.md`
  - Resolve key-os conditional-vs-fixed initialization conflict.
  - Replace stale onboarding order with current key-os + phase-log entry order.
  - Fix phase-log recording conflict.
  - Replace unavailable MCP hard chain with available-tool routing.
  - Tighten code/test/plan rules so docs-only and operational tasks are not forced into code workflows.
  - Condense hotpost rules into stable hard contracts plus SOP/reference links.

- Create or update: `reports/phase-log/phase1032.md`
  - Record the final state change after `AGENTS.md` is rewritten and verified.

## Task 1: Rewrite `AGENTS.md` Startup And Governance Rules

**Files:**
- Modify: `AGENTS.md`

- [x] **Step 1: Fix key-os rules**

Replace the current key-os usage wording with:
- fixed startup commands are mandatory;
- other key-os reads/writes are demand-driven;
- pure warning from `keyos check --json` is not a hard failure;
- direct file-tree reads under `KEYOS_ROOT` remain forbidden.

- [x] **Step 2: Fix project reading order**

Replace the old `README.md -> 文档阅读指南` entry with:
- startup: `keyos status/check/read`;
- current project state: `reports/phase-log/CURRENT_STATUS.md`, `OPEN_ITEMS.md`, `MILESTONES.md`, `INDEX.md`;
- task-specific docs only after that;
- `README.md` is background, not current progress truth.

- [x] **Step 3: Fix phase-log recording conflict**

Make phase creation conditional:
- create `phase{N}.md` only for stage change, key delivery, verified root cause, or priority/next-step change;
- otherwise update current status/open items/milestones only when needed;
- remove the blanket “unrecorded means incomplete” wording.

- [x] **Step 4: Fix tool-chain rule**

Replace the unavailable hard MCP chain with:
- use `serena` or `rg` for code location;
- use sequential thinking for non-trivial root-cause reasoning;
- use browser/Playwright/DevTools only for UI/E2E validation;
- do not block on unavailable MCP tools such as `exa-code`.

- [x] **Step 5: Condense hotpost rules**

Preserve durable contracts:
- `value-threshold publishing`;
- `all-scope` default;
- `7d -> 15d -> 30d` expansion discipline;
- `freshness gate workflow`, `named topic budget`, publish/snapshot/cloud sync stability;
- storage contract and allowed shared APIs;
- mini snapshot/cloud function data are derived products only.

Move detailed operational steps behind links to:
- `docs/sop/2026-04-08-日常产卡SOP.md`
- `docs/sop/2026-04-08-评审与发布SOP.md`
- `docs/sop/2026-04-08-优化触发SOP.md`
- `docs/reference/hotpost-storage-contract.md`

## Task 2: Verify The Rewrite

**Files:**
- Read: `AGENTS.md`

- [x] **Step 1: Run conflict text checks**

Run:
```bash
rg -n "只有在需要读取跨项目上下文|任何 `keyos` 命令返回非零退出码|未记录视为未完成|exa-code|README.md` → `docs/2025-10-10-文档阅读指南|统一反馈四问" AGENTS.md
```

Expected:
- no stale conflict lines remain.

- [x] **Step 2: Run key-os check**

Run:
```bash
keyos check --json
```

Expected:
- JSON output is readable.
- `has_failures=false`.
- warning-only output is acceptable and should not block this task.

## Task 3: Record The State Change

**Files:**
- Create: `reports/phase-log/phase1032.md`

- [x] **Step 1: Add short phase record**

Record four things only:
- this round rewrote `AGENTS.md`;
- startup/tool/phase/hotpost governance conflicts were removed;
- `CLAUDE.md/GEMINI.md` were intentionally not touched;
- next step is to use the new contract in the next real task.
