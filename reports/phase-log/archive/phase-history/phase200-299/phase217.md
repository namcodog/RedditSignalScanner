# Phase 217

## 目标
- LLM Prompt 增强：输出 evidence_post_ids 与 why_relevant，并映射到真实帖子。

## 变更
- Prompt 输出结构增强（trending/rant/opportunity）：`backend/app/services/hotpost/prompts.py`
  - topics/pain_points/unmet_needs 增加 `evidence_post_ids`
  - 新增 `post_annotations`（why_relevant）
- LLM 输出映射与落地：`backend/app/services/hotpost/report_llm.py`
  - 新增 `apply_hotpost_llm_annotations`
  - evidence_post_ids 映射为真实 evidence
  - why_relevant 写回 top_posts
- 搜索数据传递增强：`backend/app/services/hotpost/service.py`
  - posts_payload 补充 `id` 与 `heat_score`
- Schema & 前端类型补齐：`backend/app/schemas/hotpost.py`, `frontend/src/types/hotpost.ts`

## 测试
- `pytest backend/tests/services/hotpost/test_hotpost_report_merge.py -q`

## 结论
- Phase 217 完成，证据与 why_relevant 已能从 LLM 输出映射到真实帖子。
