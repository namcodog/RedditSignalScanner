# Phase 97 - DB status check (backfill/labels/embeddings)

## Action
- Queried DB for backfill coverage via `community_cache.backfill_floor`.
- Checked labeling coverage (`post_semantic_labels`, `content_labels`).
- Checked embedding coverage (`post_embeddings`) and running process.

## Result
- Backfill pending (active & not blacklisted, floor null or <12mo): 180 communities; sample list captured in output.
- Full list exported: reports/phase-log/phase97-backfill-pending.csv (180 rows).
- Post semantic labels: 186,888 / 196,215 total posts (~95.2%); 172,443 / 181,770 in last 12 months (~94.9%).
- Comment labels: 1,286,705 / 2,139,758 total comments (~60.1%); 608,135 / 1,953,883 in last 12 months (~31.1%).
- Embeddings: 186,726 / 196,215 total posts (~95.2%); 172,281 / 181,770 in last 12 months (~94.8%).
- No running `backfill_embeddings.py` process detected.
