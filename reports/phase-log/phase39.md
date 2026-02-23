# Phase 39 - Legacy 路由无痛搬家

## 目标
- 旧实现集中到 `app/api/legacy`，主链路清晰；旧入口保留“转发壳子”保证兼容。
- route metrics 继续能识别 legacy 调用。
- SOP 同步更新。

## 变更
- 新增：`backend/app/api/legacy/`（旧路由真实实现）
- `backend/app/api/routes/*.py`：改为兼容转发壳
- `backend/app/middleware/route_metrics.py`：legacy 识别新增 `app.api.legacy.*`
- `backend/tests/api/test_route_metrics.py`：覆盖 legacy 新路径
- `docs/sop/2025-12-13-facts-v2-落地SOP.md`：补 legacy 结构说明 + 观察/下线流程

## 测试
- `pytest -q backend/tests/api/test_route_metrics.py -k legacy`

## 结果
- legacy 路由结构集中、兼容入口不破，监控仍可区分 legacy。
- 运行时检查：启用 route_metrics 后模拟 legacy 调用 1 次，结果 `legacy_total=1`，路径为 `GET /api/guidance/input`。
- 本地验证（同分钟桶）：`golden_total=1 (delta 1)`、`legacy_total=1 (delta 1)`，说明本地统计链路正常。
