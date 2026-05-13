# Phase 92 - Attach post scores into analysis

## Action
- Added `_attach_post_scores` to enrich deduped posts with `business_pool`/`value_score` from `post_scores_latest_v` (fallback to `post_scores`).
- Wired `run_analysis` to record `post_score_stats` into sources.
- Hardened the new test to clean duplicates before insert.

## Result
- Test: `python -m pytest backend/tests/services/test_analysis_engine.py -k attach_post_scores` (pass).
- Chrome DevTools MCP unavailable: profile already in use, validation skipped.
