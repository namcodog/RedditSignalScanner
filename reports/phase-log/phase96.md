# Phase 96 - Real scored-post verification (direct run)

## Action
- Ran a direct `run_analysis` using a stub data collection built from `posts_raw JOIN post_scores_latest_v` (Shopify profile communities).
- Verified `post_score_stats` and `noise_pool_stats` in the returned sources.

## Result
- `post_score_stats`: scored_posts=2, score_coverage=0.67, pool_counts={'core': 2}.
- `noise_pool_stats`: noise_posts=0.
- Warning: `discovered_communities` insert failed due to missing Task row (direct run bypassed `tasks` table); analysis still completed.
