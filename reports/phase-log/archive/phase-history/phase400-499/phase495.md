# Phase 495 - hotpost 启动探活 404 收口

## 时间
- 2026-03-27

## 目标
- 解决 `make dev-backend-start` 后“服务其实起来了，但健康检查 404”造成的误判。
- 明确 hotpost 当前启动问题到底是服务故障，还是探活门牌不兼容。

## 执行内容

### 1) 先确认是不是服务没起来
- 查看 `logs/backend.log`：
  - `Application startup complete`
  - `GET /docs` -> `200`
  - `GET /openapi.json` -> `200`
  - `GET /api/v1/health` -> `404`
- 结论：
  - Uvicorn 和 FastAPI 都正常起来了。
  - 404 不是“后端挂了”，而是“探活 URL 打错了”。

### 2) 用代码确认真实健康检查门牌
- 文件：`backend/app/main.py`
- 当前真实健康检查：
  - `/api/healthz`
  - `/api/v1/healthz`
- 缺失路径：
  - `/api/v1/health`

### 3) 最小修复
- 在 `backend/app/main.py` 新增：
  - `GET /api/v1/health`
- 返回与正式门牌保持一致：
  - `{ "status": "ok" }`
- 同时把根路径 `/` 返回的端点列表补上这条兼容门牌，避免再误导。

### 4) 测试固化
- 文件：`backend/tests/api/test_golden_path_contract.py`
- 新增测试：
  - `test_health_aliases_return_same_ok_payload`
- 固定三条路径都返回同样结果：
  - `/api/healthz`
  - `/api/v1/healthz`
  - `/api/v1/health`

## 验证
- 先跑：
  - `pytest backend/tests/api/test_golden_path_contract.py -q`
- 首次失败原因：
  - 测试会话默认连 `reddit_signal_scanner_test`，当前沙箱不允许访问本地 5432
  - 这不是本次改动回归
- 按项目安全口径改跑：
  - `SKIP_DB_RESET=1 pytest backend/tests/api/test_golden_path_contract.py -q`
- 结果：
  - `5 passed`

## 四问回顾
1. 发现了什么？
- hotpost 这次并不是“后端没启动”，而是健康检查打到了不存在的 `/api/v1/health`。

2. 是否需要修复？
- 需要。只靠口头提醒“你地址打错了”不稳，下一次脚本或人手工排查还会再踩。

3. 精确修复方法？
- 保留正式门牌 `healthz`，同时补一个轻量兼容别名 `/api/v1/health`，并用契约测试钉住。

4. 下一步系统性计划是什么？
- 启动 hotpost 时优先用：
  - `http://localhost:8006/docs`
  - `http://localhost:8006/api/v1/health`
  - `http://localhost:8006/api/healthz`
- 若仍异常，再看 `logs/backend.log`，不要再把单个 404 直接等同于“服务没起来”。

5. 这次执行的价值是什么？
- 把一次“误报型故障”收成了兼容合同，后续启动判断更稳，hotpost 排障成本会明显下降。
