# Phase 496 - hotpost 稳定启动门禁化

## 时间
- 2026-03-27

## 目标
- 把 hotpost 从“服务起来后手工碰碰看”升级成“有正式 smoke、能稳定确认正常态启动”。

## 执行内容

### 1) 根因归位
- 回看 hotpost 历史解耦记录：
  - `phase328`：拆摘要 workflow
  - `phase333`：拆证据收集 workflow
- 结论：
  - 那几轮改的是 `backend/app/services/hotpost/` 的业务编排边界
  - 这次启动误报来自健康检查和启动门禁层，不是 hotpost 解耦本身打坏了主链

### 2) 收 hotpost smoke 前置门禁
- 文件：`backend/scripts/acceptance/run_live_hotpost_acceptance.py`
- 新增 preflight：
  - 后端健康检查：优先 `/api/v1/health`，再兼容 `/api/v1/healthz`、`/api/healthz`
  - OpenAPI 路由检查：
    - `/api/hotpost/search`
    - `/api/hotpost/result/{query_id}`
    - `/api/hotpost/stream/{query_id}`
    - `/api/hotpost/deepdive`
- 新增 payload 校验：
  - `query_id` 必须存在
  - `status` 必须是 `completed/success/degraded`
  - `summary` 必须非空
  - `evidence_count` 必须存在且不能为负数
  - `communities` 必须是列表

### 3) 把入口收成 Makefile 合同
- 文件：`makefiles/test.mk`
- 新增：
  - `acceptance-hotpost-smoke`
- 当前作用：
  - 直接对当前 backend 跑 hotpost 正常态 smoke
  - 不用再手工拼 query/polling/preflight 命令

### 4) 同步启动口径
- 更新文件：
  - `README.md`
  - `docs/本地启动指南.md`
  - `docs/OPERATIONS.md`
  - `docs/reference/PORT_CONFIGURATION.md`
  - `docs/API-REFERENCE.md`
  - `scripts/makefile-common.sh`
  - `backend/scripts/acceptance/manage_live_runtime.py`
  - `makefiles/acceptance.mk`
- 当前统一口径：
  - 首选 backend health：`/api/v1/health`
  - hotpost 正常态 smoke：`make acceptance-hotpost-smoke`

## 测试与验证

### 定向测试
- `SKIP_DB_RESET=1 pytest backend/tests/scripts/acceptance/test_run_live_hotpost_acceptance.py backend/tests/scripts/acceptance/test_manage_live_runtime.py backend/tests/api/test_golden_path_contract.py -q`
- 结果：
  - `18 passed`

### 真实 smoke
- 命令：
  - `make acceptance-hotpost-smoke`
- 结果：
  - `query_id = c305bdb0-a558-4a73-ad71-4a2aa3adef2e`
  - `status = completed`
  - `evidence_count = 30`
  - `community_count = 1`
  - `health_path = /api/v1/health`

## 四问回顾
1. 发现了什么？
- hotpost 的业务解耦没有把系统搞坏；真正缺的是“启动后如何快速确认 hotpost 正常态”的正式门禁。

2. 是否需要修复？
- 需要。否则每次都只能靠人工撞接口，容易把启动问题和业务问题混在一起。

3. 精确修复方法？
- 给 hotpost acceptance 脚本补 preflight 和 payload 校验；
- 给 Makefile 增加固定 smoke 入口；
- 把文档和启动脚本统一到同一套健康检查口径。

4. 下一步系统性计划是什么？
- 以后排 hotpost 启动问题先跑：
  - `make acceptance-hotpost-smoke`
- 如果这条过了：
  - 说明 backend、health、OpenAPI、hotpost 路由、fresh query 主链都站住了
- 如果不过：
  - 先看 preflight 报错，再决定查启动、依赖还是业务链路

5. 这次执行的价值是什么？
- hotpost 现在不只是“理论上能起”，而是已经有一条真实 smoke 证明“正常态可稳定启动”。
