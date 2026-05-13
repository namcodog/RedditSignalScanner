# Phase 86 - Systemic SOP audit (crawl -> ingest -> label)

## Scope
Audit overall data capture + ingestion + labeling against SOP, focused on A/B groups (12 months).

## Runtime snapshot
- Workers:
  - beat running (single instance)
  - monitoring_queue worker running
  - labels worker running
  - analysis/crawler/backfill workers running
- Queues:
  - analysis_queue=0
  - backfill_queue=0
  - crawler_queue=52
  - monitoring_queue=0
  - compensation_queue=0

## Ingestion
- A posts (12m): 1,819
- A comments (12m): 42,990
- B posts (12m): 168
- B comments (12m): 1,955
- posts_hot cached (last 30d, A+B): 1,781

## Labels
- A comments labeled: 42,990 / 42,990
- B comments labeled: 1,955 / 1,955

## Cleaning & scoring
- posts_quarantine (A+B, 12m): 11
- posts_raw.value_score null: 0 / 1,987
- comments.value_score null: 0 / 44,945
- post_scores for A+B posts: 1,987
- comment_scores for A+B comments: 0

## SOP gaps / deviations
1) discovered_communities status:
   - A group remains pending; B group approved. SOP expects vetting->evaluation recorded for new communities.
2) backfill_floor in community_cache is NULL for A/B; SOP expects backfill_floor to advance on backfill.
3) posts_raw source_track shows "incremental" for A/B (12m) instead of backfill, and posts_raw crawl_run_id not populated for B posts run.
4) comment_scores pipeline not populated (if required by SOP).

## Chrome DevTools validation
- MCP connection failed due to existing browser profile in use.

## Next
- Decide whether to align discovered_communities for A group (approve or purge pending).
- Fix backfill_floor and source_track/crawl_run_id annotations for posts backfill.
- Confirm whether comment_scores is required or optional for current phase.
