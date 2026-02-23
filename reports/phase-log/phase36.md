# Phase 36 - 升级版门牌影子入口

## 目标
- 保留 `/api` 为主入口，同时提供 `/api/v1` 影子门牌，便于长期演进和兼容校验。

## 变更
- `backend/app/main.py`：新增 `/api/v1` 路由挂载与 `/api/v1/healthz`。
- `backend/tests/api/test_analyze.py`：新增 `/api/v1/analyze` 入口验证测试。

## 测试
- `pytest -q backend/tests/api/test_analyze.py -k v1_alias`

## 结果
- `/api/v1/analyze` 可用，与 `/api/analyze` 行为一致。
- 主链路 `/api` 不受影响。
