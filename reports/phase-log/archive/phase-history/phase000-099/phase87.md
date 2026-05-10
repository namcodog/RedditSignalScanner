# Phase 87 - SOP alignment fixes (A/B)

## 1) A group vetting alignment
- discovered_communities: A group moved from pending -> approved.
- admin_reviewed_at set to now() when empty; admin_notes appended.

## 2) Backfill metadata alignment
- community_cache.backfill_floor set for all A/B communities using min(created_at) of posts_raw (12 months, is_current).
- posts_raw source_track set to backfill_posts for A/B posts in the backfill fetch window (12 months, is_current).
- posts_raw crawl_run_id already present for B posts (non-null). Not overwritten to avoid losing per-run audit.

## 3) comment_scores requirement check
- A/B candidates matching score_comments_v2 criteria: 0 (no run needed).

## Verification snapshot
- A group discovered_communities status: approved.
- backfill_floor null count: 0 / 18.
- source_track for A/B 12m posts: backfill_posts (1987 rows).
