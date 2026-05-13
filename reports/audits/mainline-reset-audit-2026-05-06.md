# Mainline Reset Audit

Date: 2026-05-06
Scope: RedditSignalScanner mainline only

## Executive Summary

This audit is read-only first. It reopens the original RedditSignalScanner mainline without taking over Hotpost daily operations or the mini app product repo.

Main findings:

- The root worktree is extremely dirty: `1474` status entries, split as `720 D / 43 M / 711 ??`; this is a separate cleanup problem and must not be mixed with mainline reset.
- Mainline and Hotpost are route/API distinguishable. The current risk is not that the products are inseparable; it is that dirty-worktree ownership and shared service complexity can cause accidental cross-track edits.
- The project already did real decoupling work. `ReportService` is not the current main over-engineering target; it is now a thin service shell around runtime/context/workflow modules.
- The largest remaining mainline complexity risk is `backend/app/services/analysis/analysis_engine.py`, especially the still-large `run_analysis` domain center.
- Mainline smoke tests pass: backend `70 passed, 1 skipped`; frontend `27 passed`.
- Data boundary rules are present and mostly aligned: default DB is Dev, Gold has explicit guardrails, but old archive snippets still contain direct Gold DB commands and must not be reused as current SOP.

## Dirty Worktree Inventory

Current root worktree status:

```text
git status --short | wc -l
1474

git status --short | cut -c1-2 | sort | uniq -c
720  D
 43  M
711 ??
```

Top dirty directories:

```text
973 reports
382 backend
 38 frontend
 17 "reports
 11 "docs
  9 docs
  6 mem
  2 scripts
  2 makefiles
  2 .agents
```

Dirty worktree buckets:

| Bucket | Evidence | Action |
| --- | --- | --- |
| Boundary guardrails | `AGENTS.md`, `Makefile`, `scripts/check-boundary-status.sh`, new specs/plans | Keep separate commit |
| Phase-log/archive governance | Many `reports/phase-log` deletions and untracked archive entries | Do not touch during mainline audit |
| Mainline code | `backend/app/services/analysis`, `report`, `crawl`, `community`; frontend report/input pages | Audit only |
| Hotpost code/data | `backend/app/services/hotpost`, `backend/scripts/hotpost`, Hotpost docs/data | Boundary-only, no cleanup |
| Mini app | `hotpost-mini/hotpost-mini-app` independent git repo | Must remain clean |

## Phase-Log And Historical Truth Source

Current four-entry phase-log state is Hotpost-heavy:

- `CURRENT_STATUS.md` says the current active judgment is Hotpost V13 routing, mini app launch readiness, and recent Hotpost operating results.
- `OPEN_ITEMS.md` P0/P1/P2 is mainly about Hotpost supply thickness, rolling inventory, trend audit, mini release validation, and all-scope daily operation.
- `MILESTONES.md` still preserves the original mainline history: project skeleton, analysis/data contract tightening, Full A/report quality recovery, then Hotpost 1.0 and steady operation.
- `INDEX.md` current entry list is dominated by Hotpost and mini app phase references.

Durable lessons from historical summaries:

- `PHASE_SUMMARY_200_399.md`: do not let display fallback pretend to be real data; distinguish insufficient samples from chain failure.
- `PHASE_SUMMARY_400_599.md`: Full A/report quality problems usually come from the data bottom and contracts, not just prompts.
- `PHASE_SUMMARY_600_799.md`: Hotpost formed `signal / hot / breakdown` and pack-specific operating assets, but that is a later product layer.
- `PHASE_SUMMARY_800_NOW.md`: current operating phase emphasizes freshness, quota, collect efficiency, and short phase-log governance.

Current conflict: phase-log says active mainline is Hotpost daily operations, while this audit is reopening the original RedditSignalScanner mainline. This audit must not silently rewrite current status until findings are verified.

## Mainline Product Map

Frontend routes:

- Main product: `/`, `/progress/:taskId`, `/report/:taskId`, `/standard-report/:slug`, `/insights`, `/insights/:taskId`, `/decision-units`, `/dashboard`, `/admin/...`
- Auth/supporting pages: `/login`, `/register`, `*`
- Hotpost web operations: `/hotpost`, `/hotpost/clues/:clueId`, `/hotpost/box`, `/hotpost/lab/search`, `/hotpost/result/:queryId`

Backend API routers:

- Mainline: `analyze`, `decision_units`, `tasks`, `stream`, `reports`, `export`
- Hotpost: `hotpost`, `hotpost_clues`, `hotpost_card_candidates`, `hotpost_card_drafts`, `hotpost_card_review`, `hotpost_wx_auth`, `hotpost_wx_favorites`, `hotpost_source_scopes`, `hotpost_candidate_collection`

Serena symbol map:

- `backend/app/api/v1/endpoints/analyze.py`: `create_analysis_task`, `_schedule_analysis`, `_schedule_example_report`, topic/mode resolvers.
- `backend/app/api/v1/endpoints/reports.py`: `get_analysis_report`, download/export endpoints, fallback community detail helpers, `SlidingWindowRateLimiter`.
- `backend/app/services/analysis/analysis_engine.py`: large procedural core around `run_analysis`, collection, sample guard, keyword/search query generation, scoring, cache/backfill, data lineage, and insufficient-data handling.
- `backend/app/services/report/report_service.py`: `ReportService.get_report`, payload validation, overview building, HTML coercion, runtime metadata, and report cache protocol.

Current shortest mainline chain:

```text
InputPage
  -> POST /api/analyze
  -> create_analysis_task
  -> _schedule_analysis
  -> AnalysisEngine.run_analysis
  -> tasks / stream status
  -> reports.get_analysis_report
  -> ReportService.get_report
  -> ReportPage / StandardReportPage
```

Boundary note: the Web and backend route layers are already split enough to distinguish main product and Hotpost. The larger risk is not route ambiguity; it is dirty-worktree ownership and shared backend/service complexity.

## Over-Engineering Findings

Important correction after phase-log and Serena verification:

- This project already did real decoupling work. Do not treat every large area as untouched over-engineering.
- The strongest historical evidence is `phase304`, `phase310`, `phase320`, `phase329`, `phase339`, `phase361`, `phase369`, `phase378`, and `phase399` under `reports/phase-log/archive/phase-history/phase300-399/`.
- The repeated architecture principle in those phases was: "make the main entry thinner, move heavy work back to workflow/service modules, keep one truth source."
- Current code confirms this history: report runtime/context/enrichment/assembly/payload/request-factory concerns are separate modules, and crawl seed/archive/execute-target concerns are also separated.

Confirmed decoupled assets still present:

| Area | Current files | Evidence |
| --- | --- | --- |
| Report service shell | `backend/app/services/report/report_service.py` | 191 lines; Serena shows mostly `get_report` plus public runtime delegates |
| Report runtime/helper layer | `report_runtime.py`, `report_runtime_factory.py` | owns validation, overview, quality level, request/assembly deps |
| Report context loading | `report_context_loader.py` | owns task/analysis/access/cache-key context loading |
| Report enrichment | `report_enrichment_workflow.py` | owns action item enrichment, evidence marking, audit writing |
| Report assembly/payload | `report_assembly_workflow.py`, `report_payload_builder.py` | owns report payload assembly and output shaping |
| Crawl seed/archive workflows | `seed_crawl_metrics_service.py`, `seed_archive_workflow.py` | owns seed crawl metrics and archive execution workflow |
| Crawl execute target runtime | `execute_target_task_runtime.py`, `execute_target_task_support.py` | owns task runtime wiring and helper chain |
| Frontend route constants | `frontend/src/router/routes.ts` | `phase399` split route constants to break router/page cycle |

Large-file evidence:

```text
4995 backend/app/services/analysis/analysis_engine.py
1497 frontend/src/pages/hotpost/HotPostResultPage.tsx
1359 frontend/src/pages/ReportPage.tsx
 923 backend/app/services/analysis/analysis_collection_support.py
 913 frontend/src/pages/__tests__/ReportPage.test.tsx
 896 frontend/src/pages/admin/CommunityPoolPage.tsx
 884 backend/app/services/community/community_import_service.py
 873 backend/app/api/v1/endpoints/reports.py
 844 backend/app/services/analysis/t1_stats.py
 832 backend/app/services/analysis/signal_extraction.py
```

Complexity-smell evidence:

- `analysis_engine.py` is a 4995-line domain center that still owns many concerns: collection, scoring, sample guard, backfill, keyword filtering, data lineage, facts, and report-ready output. Some support modules exist, but `run_analysis` remains the largest mainline risk.
- `reports.py` is 873 lines and includes report retrieval, export, fallback community details, community maps, and a rate limiter. This is an endpoint-layer concern, not evidence that `ReportService` itself failed to decouple.
- `ReportPage.tsx` is 1359 lines, so frontend report rendering likely mixes page state, data normalization, display contract, and UI layout.
- `community_import_service.py` is 884 lines and uses broad `Any` plus multiple spreadsheet libraries; likely a utility workflow that should remain separate from the shortest mainline acceptance path.
- `rg` shows active use of `fallback`, `legacy`, `Any`, `type: ignore`, and `except Exception` across mainline scopes. Some are legitimate compatibility layers, but the current codebase has too many ambiguous cases to treat fallback as safe by default.

Duplicate/overlapping service families:

```text
backend/app/services/analysis
backend/app/services/community
backend/app/services/crawl
backend/app/services/discovery
backend/app/services/hotpost
backend/app/services/report
backend/app/services/semantic
```

Finding classification:

| Finding | Evidence | User impact | Keep / simplify / delete later | Confidence |
| --- | --- | --- | --- | --- |
| Analysis engine is still the biggest God-object candidate | `analysis_engine.py` 4995 lines; support modules exist, but Serena still shows `run_analysis` plus many helper concerns in the same file | Hard to prove mainline behavior; fixes risk collateral regressions | Simplify later around one shortest acceptance chain | High |
| Report service was substantially decoupled already | `report_service.py` is 191 lines; phase369 says runtime/helper pack was moved out; current Serena confirms runtime/context/factory/workflow modules | Avoid wasting time redoing solved work | Preserve current boundaries; audit endpoint bloat separately | High |
| Report endpoint may still be too broad | `reports.py` 873 lines; endpoint owns exports, maps, fallback community details, and limiter | Endpoint fixes may still sprawl | Split only if current tests or acceptance path show it blocks delivery | Medium |
| Frontend report page is too large for safe iteration | `ReportPage.tsx` 1359 lines | UI/report contract changes are hard to review; snapshot changes can mask data issues | Simplify later by extracting presentational sections only after contract is stable | Medium |
| Legacy/fallback patterns need policy review | `stream.py` delegates to legacy route with `type: ignore`; `InputPage.tsx` keeps fallback examples; crawl fallback is explicit | Silent fallback could hide real failures, but some fallback is intentional rescue | Keep explicit rescue/fallback with observable flags; audit silent fallback first | High |
| Too many service families overlap the mainline | `analysis`, `community`, `crawl`, `discovery`, `semantic`, `report` all participate in the original chain | New agents may fix symptoms by adding another layer | Map one accepted chain before adding or deleting services | Medium |

## Test And Runtime Evidence

Existing mainline test entry points include:

- Backend API: `backend/tests/api/test_analyze.py`, `backend/tests/api/test_reports.py`
- Backend report service: `backend/tests/services/report/test_report_service.py` plus many workflow-specific report tests
- Backend analysis service: `backend/tests/services/analysis/test_analysis_engine.py` plus support-module tests
- Frontend report/input flow: `frontend/src/pages/__tests__/InputPage.test.tsx`, `ReportPage.test.tsx`, `ReportFlow.integration.test.tsx`
- Frontend contracts: `frontend/src/tests/contract/report-api.contract.test.ts`, `report-schema.contract.test.ts`

Backend smoke:

```bash
PYTHONPATH=backend pytest -q backend/tests/api/test_analyze.py backend/tests/api/test_reports.py backend/tests/services/report/test_report_service.py backend/tests/services/analysis/test_analysis_engine.py
```

Result:

- `70 passed, 1 skipped, 22 warnings in 54.28s`
- Warnings include dependency deprecations, SQLAlchemy connection warning, and several non-async tests marked with `@pytest.mark.asyncio`.

Frontend smoke:

```bash
cd frontend && npm test -- --run src/pages/__tests__/InputPage.test.tsx src/pages/__tests__/ReportPage.test.tsx src/pages/__tests__/ReportFlow.integration.test.tsx src/tests/contract/report-api.contract.test.ts src/tests/contract/report-schema.contract.test.ts
```

Result:

- `5 files passed, 27 tests passed`
- Test noise includes React Router v7 future warnings, React `act(...)` warnings in `ReportPage` tests, and expected error-path logs for failed report loading / missing `canonical_report_json`.

E2E is deferred until smoke tests and dirty-worktree ownership are understood.

## Data Boundary Evidence

Current DB contract:

- Gold DB: `reddit_signal_scanner`, used as standard/production reference. Non-prod access requires explicit `ALLOW_GOLD_DB=1`.
- Dev DB: `reddit_signal_scanner_dev`, default write target for local integration and manual workflows.
- Test DB: `reddit_signal_scanner_test`, automated-test target and safe reset target.
- Gold -> Dev copying is allowed only for targeted task data; reverse writeback and full DB copy are not part of this audit.

Configuration evidence:

- `backend/app/core/config.py` defaults `POSTGRES_DB` to `reddit_signal_scanner_dev`.
- `backend/app/db/session.py` also defaults `POSTGRES_DB` to `reddit_signal_scanner_dev` and calls `validate_database_target(DATABASE_URL)` at import time.
- `backend/app/db/database_guard.py` blocks `reddit_signal_scanner` in non-prod unless `ALLOW_GOLD_DB=1`.
- `backend/.env.example` points `DATABASE_URL` and migration URL at `reddit_signal_scanner_dev`, with `ALLOW_GOLD_DB=0`.
- `community_governance_service.cleanup_dev()` only allows cleanup on `reddit_signal_scanner_dev` or `reddit_signal_scanner_test`.
- `label_io_runtime.ensure_non_gold_database()` blocks LLM label import into Gold unless explicitly allowed.

Risk evidence:

- Historical archive docs and old scripts still mention direct `reddit_signal_scanner` commands. They are mostly under `docs/archive` or `docs/archive/root/scripts/legacy`, so they should not be treated as current runbooks.
- Any future cleanup task must avoid following archived psql snippets without checking the current DB guard contract.

Audit stance: this audit must not write Gold DB. Any data repair later must target Dev DB or Test DB unless explicitly approved.

## Recommended Next Moves

### P0: Restore a shortest mainline acceptance chain

Do not begin with broad refactors. First define and run one accepted chain:

```text
InputPage
  -> create_analysis_task
  -> AnalysisEngine.run_analysis
  -> reports.get_analysis_report
  -> ReportService.get_report
  -> ReportPage
```

The current smoke evidence is good enough to say this chain has automated coverage, but not enough to say product acceptance is restored. Next plan should produce one reproducible acceptance fixture or local runbook for this chain.

Suggested next plan file:

- `docs/superpowers/plans/YYYY-MM-DD-mainline-acceptance-fix-plan.md`

### P1: Reduce over-engineering where it blocks acceptance

Do not redo the report-service decoupling. It already exists and current code confirms it.

Focus order:

1. `analysis_engine.py`: identify what `run_analysis` must own vs what can move to existing `analysis_*_support.py` modules.
2. `backend/app/api/v1/endpoints/reports.py`: split only if endpoint breadth blocks report acceptance or hides fallback behavior.
3. `frontend/src/pages/ReportPage.tsx`: split page state / data adapter / display sections only after the canonical report contract is stable.

Suggested next plan file:

- `docs/superpowers/plans/YYYY-MM-DD-mainline-overengineering-reduction-plan.md`

### P2: Archive or quarantine historical clutter

The dirty worktree is a separate problem from mainline acceptance. It should not be solved with `git add .`, broad deletes, or one mixed cleanup commit.

Suggested next plan file:

- `docs/superpowers/plans/YYYY-MM-DD-phase-log-dirty-worktree-cleanup-plan.md`

### Keep Separate: Hotpost daily operations

Hotpost daily card production remains on its own operating track:

```text
collect -> gate -> review/publish -> release -> mini snapshot
```

Do not move daily card work into the mainline reset audit plan.

### Keep Separate: Mini app product work

`hotpost-mini/hotpost-mini-app` remains an independent git repo and consumer of published snapshots. Mainline reset work must continue to pass `make boundary-status` before commit/staging decisions.

## Not Touched

- `hotpost-mini/hotpost-mini-app`
- `backend/data/hotpost/mini_snapshots`
- `hotpost-mini/.../cloudfunctions/*/data`
- Hotpost candidates, drafts, and releases
