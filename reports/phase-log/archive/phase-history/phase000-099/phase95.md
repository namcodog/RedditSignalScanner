# Phase 95 - Noise pool policy + business_pool weighting + worker reload

## Action
- Added noise isolation + business_pool weighting in analysis pipeline.
- Signal extractor now prefers `priority_score` when present.
- Restarted analysis/labels workers to load new code (killed old worker PIDs that did not stop on SIGTERM).
- Triggered new analysis task to verify sources keys.

## Result
- Task id: `f176882e-c623-4aef-b7a2-1968869997ac`, Celery id: `1527609f-c160-4fd3-9b6a-3ca66f3a7033`.
- `analyses.sources` now contains `post_score_stats` and `noise_pool_stats`.
- Chrome DevTools MCP unavailable (profile already in use).
