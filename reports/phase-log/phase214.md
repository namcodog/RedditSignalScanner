# Phase 214

## 目标
- 补齐帖子核心数据字段（heat_score / reddit_url / body_preview）。

## 变更
- Hotpost schema 增加 `heat_score`：`backend/app/schemas/hotpost.py`
- 生成热度分与更长摘要：`backend/app/services/hotpost/service.py`
  - `heat_score = score + num_comments * 2`
  - `body_preview` 截断长度调整为 500
- 前端类型补齐：`frontend/src/types/hotpost.ts`

## 测试
- `pytest backend/tests/services/hotpost/test_hotpost_post_fields.py -q`

## 结论
- Phase 214 完成，字段增强已落地。
