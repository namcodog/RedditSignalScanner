# Phase 161 - Report Prompt 结构/口径对齐

## 变更范围
- `backend/app/services/llm/report_prompts.py`

## 调整点
- facts 口径改为 `facts_slice` 实际字段：
  - trend_summary / market_saturation / battlefield_profiles / top_drivers
  - aggregates / business_signals / sample_posts_db / sample_comments_db / facts_v2_quality
- 决策卡片结构对齐 PRD：
  - 2.2 改为 P/S Ratio
  - 2.3 高潜力社群
  - 2.4 明确机会点（可执行）
- 核心战场引用从 `battlefield_profiles` 取

## 备注
- 未改动模板其它风格与写作规则
