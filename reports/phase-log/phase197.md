# Phase 197

## 目标
- 落地排队 + SSE 推送（queue_update / progress / completed）。

## 变更
- 新增排队状态跟踪器：`backend/app/services/hotpost/queue.py`
- 在搜索流程中注入排队状态更新：`backend/app/services/hotpost/service.py`
- 新增 SSE 端点：`GET /api/hotpost/stream/{query_id}`
  - `backend/app/api/v1/endpoints/hotpost.py`
- Hotpost 响应新增可选字段：`status/position/estimated_wait_seconds`
  - `backend/app/schemas/hotpost.py`
- 新增单测：`backend/tests/services/hotpost/test_hotpost_queue.py`

## 验证
- `PYTHONPATH=backend pytest backend/tests/services/hotpost/test_hotpost_queue.py -q`

## 结论
- 排队状态会写入 Redis（hotpost:queue:{query_id}），SSE 可实时推送队列状态。

## 影响范围
- 仅爆帖速递模块。
