# Phase 195

## 目标
- 落实“统计值由代码计算、LLM 仅归纳”的合并逻辑（字段归属表）。

## 变更
- 新增痛点类别标签归一化工具并支持中文类别映射：`backend/app/services/hotpost/rules.py`
- 在搜索响应中强制覆盖统计值（evidence_count、community_distribution、sentiment_overview、confidence）并覆盖痛点 mentions、迁移意向占比、机会共鸣计数：`backend/app/services/hotpost/service.py`
- 补充规则单测：`backend/tests/services/hotpost/test_hotpost_rules.py`

## 验证
- `PYTHONPATH=backend pytest backend/tests/services/hotpost/test_hotpost_rules.py backend/tests/services/hotpost/test_hotpost_report_merge.py -q`

## 结论
- 统计值全部由代码覆盖，LLM 输出仅用于结构化归纳。

## 影响范围
- 仅爆帖速递模块响应。
