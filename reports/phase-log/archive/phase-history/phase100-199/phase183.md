# Phase 183 - LLM Label Backfill + SOP Sync

Date: 2026-02-02

## Scope
- Fill gaps in LLM label pipeline and semantic backflow.
- Align SOP with LLM labeling and semantic sync.

## Changes
- Added legacy backfill for comment LLM labels alongside posts.
- Backfill now preserves entities/sentiment/purchase_intent fields when available.
- SOP updated to document LLM labels (post_llm_labels/comment_llm_labels) and semantic_terms/semantic_rules backflow.
 - Granted REFERENCES/SELECT on users/evidence_posts/posts_raw/comments to rss_app (dev/test) for migrations.
 - Applied alembic heads in dev/test; LLM label tables created.
 - Ran LLM label tasks (dev): posts=3, comments=3; legacy backfill processed=0.
- Verified semantic backflow counts: semantic_rules(meta.source=llm)=61; semantic_terms recent=60.
- Switched LLM labeling to Gemini Flash-Lite (GEMINI_API_KEY + LLM_LABEL_MODEL_NAME), separate from report LLM.
- Ran minimal Gemini validation with token-trim overrides (body=300, comment=160): posts=2, comments=2.
- Current dev counts: post_llm_labels=14, comment_llm_labels=5.
- Added Core/Lab split defaults, lab 10% deep sampling + mid-score (5-7) long pass, skip obvious high/low, hash-based dedupe, and batch LLM calls.
- Tuned defaults to balanced mode: lab deep sample 15%, skip low <=2, lab truncation ratio 0.6.
- Ran minimal validation with Core/Lab split rules (body=600, comment=200): posts=2, comments=0 (no eligible comment candidates after filters).

## Files Touched
- backend/app/tasks/llm_label_task.py
- docs/sop/数据清洗打分规则v1.2规范.md

## Tests
- `pytest backend/tests/services/test_llm_labeler.py -q`

## Notes
- LLM labeling remains Core/Lab + 90-day scope.
- Dev migration blocked: `permission denied for table users` while applying `20260128_000001` (needs REFERENCES on `users` for db_user `rss_app`).
