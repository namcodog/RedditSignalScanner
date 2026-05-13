# Phase 91 - Activate probe_hot and facts_v2 gate run

## Action
- Triggered `tasks.probe.run_hot_probe` (manual_probe_hot) to activate hot-source discovery.
- Created and ran an analysis task with `topic_profile_id=shopify_ads_conversion_v1`.

## Result
- probe_hot: crawl_run_id `e6050e89-4f85-4891-b82e-d1e5f4a4b1f6`, target `1bb45c36-9aca-54d8-a3e7-592efc83cd50`, status `partial` (caps_reached).
- Analysis task: `399925d9-17dc-4106-b36c-79f247d90c36` completed.
- facts_v2 snapshot written (tier `C_scouting`, passed=true).
- Analysis sources include `facts_v2_quality` and `dedup_stats`; `collection_warnings` present (empty list).
