# Phase 407 - 验收链路稳固化（live report + dev-real）

## 目标

- 继续把 `Phase 406` 的通过结果收敛成“更稳定、可重复、少误报”。
- 重点处理两类稳定性问题：
  1. `test-e2e-live-report` 的收尾与时延波动
  2. `make dev-real` 的启动误报

## 本轮改动

### 1) live report 验收进一步稳固

- 文件：`makefiles/test.mk`
- 关键增强：
  - 增加 warmup 验收参数入口（可配）：
    - `LIVE_REPORT_WARMUP_BASE_DELAY_SECONDS`（默认 90）
    - `LIVE_REPORT_WARMUP_MAX_DELAY_SECONDS`（默认 300）
    - `LIVE_REPORT_BACKFILL_SETTLE_SECONDS`（默认 20）
    - `LIVE_REPORT_BACKFILL_MAX_TARGETS`（默认 120）
  - `analysis-live` worker 启动时显式注入上述参数，避免 warmup 在默认长延迟下波动太大。
  - 修复清理逻辑中的目录问题：
    - 原来在 `cd backend` 后执行 `$(MAKE) crawl-stop`，会误报 “No rule to make target `crawl-stop`”
    - 现在改为子 shell 执行验收命令，确保清理步骤在仓库根目录执行。
  - 验收结束后无论成功/失败都执行清理：
    - `crawl-stop`
    - 清理 `analysis-live`/`bulk-live` worker

### 2) dev-real 启动稳定性增强

- 文件：`scripts/makefile-common.sh`
  - 新增 `wait_backend_health` / `wait_frontend_health`（带重试）
- 文件：`makefiles/dev.mk`
  - `dev-real` / `dev-full` 的后端与前端健康检查改为“等待重试”而非单次探测。
  - analysis worker 启动判断由“tail 日志 grep ready”改为 `pgrep` 进程检测，减少假告警。

## 验证结果

1. `make test-e2e-live-report`（连续复验）
   - 结果：`3/3` 通过，且均为首轮即达 `A_full`
   - 任务：
     - `87337d33-351c-4382-94bd-d736c00856fb`
     - `6caa0f1d-8433-40fa-bbab-a6228d09446b`
     - `09a059e5-0ce2-474d-8462-17041ef72a95`
2. `make test-e2e`
   - 结果：复跑 `21 passed`
3. `make dev-real`
   - 结果：连续复跑可稳定显示：
     - `✅ Analysis Worker started`
     - `✅ Backend server started`
     - `✅ Frontend server started`
   - 不再出现之前的假失败/假告警路径。

## 结论

- 当前验收链路已从“能跑通”推进到“更可重复、更少噪音误报”。
- `live report` 现在在隔离模式下可稳定拿到 `A_full`，且清理流程完整。
- 下一步建议：
  1. 补一轮“连续 3 次 live report”稳定性压测并记录通过率；
  2. 增加一条队列积压监控（pending outbox / queued targets）作为验收前置门禁；
  3. 再做一次产品分数复盘（含 `live report` 真链路稳定性权重）。
