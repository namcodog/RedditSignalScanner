# Phase 510 - Family live final stable path and worker idempotency

Date: 2026-03-27

## What changed

1. Fixed live runtime analysis worker dispatch mode
- File: `backend/scripts/acceptance/manage_live_runtime.py`
- Change: set `ENABLE_CELERY_DISPATCH=1` for `analysis-live`
- Purpose: stop using inline warmup rerun in isolated live runtime and force real Celery scheduling

2. Added regression coverage for live runtime env
- File: `backend/tests/scripts/acceptance/test_manage_live_runtime.py`
- Assertion: `analysis-live` process spec now carries `ENABLE_CELERY_DISPATCH=1`

3. Added duplicate-delivery idempotency guard at analysis task entry
- File: `backend/app/tasks/analysis_task.py`
- Added:
  - `_load_completed_task_snapshot(...)`
  - `_build_duplicate_delivery_response(...)`
- Change: `run_analysis_task(...)` now short-circuits when the task is already `COMPLETED`
- Purpose: prevent duplicate Celery deliveries from trying to move `COMPLETED -> PROCESSING/FAILED`

4. Added regression test for duplicate-delivery response
- File: `backend/tests/tasks/test_task_status_transitions.py`

## Verification

### Targeted tests
- `pytest tests/scripts/acceptance/test_manage_live_runtime.py -q`
- `pytest tests/tasks/test_task_status_transitions.py tests/scripts/acceptance/test_manage_live_runtime.py -q`
- Result: pass

### Live final verification
- Command pattern:
  - `python scripts/acceptance/run_open_question_live_acceptance.py --suite final --base-url http://127.0.0.1:8016 --frontend-base-url http://127.0.0.1:3006 --product-description '我们是新手父母，夜奶和睡眠记录总断档，家人换手照护时经常漏项，想知道有没有真实可行的产品切口。' --required-tier A_full --min-reddit-links 2 --max-analysis-attempts 1 --warmup-wait-timeout-seconds 420`
- Output:
  - `backend/reports/local-acceptance/open_question_live_final_1774598415.json`
- Result:
  - `accepted = true`
  - `report_tier = A_full`
  - `issues = 0`
  - target communities:
    - `r/daddit`
    - `r/NewParents`
    - `r/beyondthebump`
  - evidence links:
    - `https://www.reddit.com/r/NewParents/comments/1k107ov/is_feeding_to_sleep_really_so_bad/`
    - `https://www.reddit.com/r/daddit/comments/1s2mn61/bedtime_routine_fix/`

### Worker log verification
- Before fix:
  - duplicate delivery produced `Invalid status transition: TaskStatus.COMPLETED -> TaskStatus.PENDING/FAILED`
- After fix:
  - duplicate delivery is short-circuited with log:
    - `Task ... already completed; skipping duplicate analysis dispatch.`
  - no terminal invalid-transition exception remained

## What this phase proves

- Family/parenting open question can now produce a clean `A_full` final report under the current live final path.
- The worker no longer blows up when the same completed analysis task is delivered again.
- The system is moving from “result looks right but backend is noisy” to “result right + runtime behavior controlled”.

## Remaining issue

- `celery_analysis_live_runtime.log` still shows:
  - `RuntimeWarning: coroutine 'Queue.get' was never awaited`
  - intermittent `bulk-live` heartbeat drift/miss
- This is a separate runtime hygiene issue, not the report-quality blocker for this phase.

## Next step

1. Re-run targeted `EDC` / another non-family domain under the same final path
2. Confirm the same runtime/idempotency fixes hold cross-domain
3. Then return to coverage/backfill generalization task list
