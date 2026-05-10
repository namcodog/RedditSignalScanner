# Phase 162 - Report Prompt 口径细化对齐

## 变更范围
- `backend/app/services/llm/report_prompts.py`

## 调整点
- 移除 pain_tree 引用，改为用 `high_value_pains + sample_comments_db` 作为机制与证据依据。
- 竞争格局改用 `aggregates` 的社区/平台聚合 + `business_signals.competitor_insights` 作为唯一口径来源。
- 勘探简报结构命名改为“开篇概览 / 决策风向标”。

## 备注
- 未改动事实字段输出结构，仅修正提示词引用与命名口径。
