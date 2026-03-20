# Phase 406 - live report 稳定性打通与正式 E2E 复验

## 目标

- 按当前世界观继续推进，优先打通 `live report` 真链路不稳定问题。
- 修复 `make dev-real` / `crawl-start` 的环境阻塞，确保验收链路可重复执行。
- 在修复后跑完整验收：`make test-e2e-live-report` + `make test-e2e`。

## 发现

1. `crawl-start` 的 `DATABASE_URL` 报错根因不是 `.env` 缺失，而是 `backend/scripts/crawl/smart_crawler_workflow.py` 把 repo root 计算错了，实际在读 `backend/backend/.env`。
2. `live report` 验收失败时，典型状态是：
   - `stage=warmup`
   - `next_action=auto_rerun_scheduled`
   - `report_tier=C_scouting`
   - `analysis_blocked=insufficient_samples`
3. inline warmup 补量派发存在吞吐瓶颈：每轮只派发一批（默认 20）就返回，导致大部分 task 级 outbox 仍是 `pending`，warmup 重跑前补量不充分。
4. `test-e2e-live-report` 之前沿用“确保现有 worker 在跑”的方式，容易被历史队列积压和噪音任务污染，结果波动大。

## 修复

### 1) 修复 smart crawler 启动链路

- 文件：`backend/scripts/crawl/smart_crawler_workflow.py`
- 改动：
  - `REPO_ROOT` 从 `parents[2]` 修正为 `parents[3]`，恢复正确读取 `backend/.env`。
  - Celery 进程探测由 `pgrep -af` 改成 `pgrep -lf`（macOS 兼容），避免误判“未运行”导致重复起 worker。

### 2) 修复 inline warmup 补量派发吞吐

- 文件：`backend/app/tasks/analysis_task.py`
- 改动：
  - `_dispatch_task_backfill_outbox_inline` 从“单批返回”改为“循环 drain”，同轮按批次持续派发直到清空或达到上限。
  - 新增可配上限：`WARMUP_INLINE_BACKFILL_MAX_TARGETS`（默认 100）。
  - 保留原 `WARMUP_INLINE_BACKFILL_BATCH_SIZE`，按剩余额度动态批量拉取。

### 3) 修复 live report 验收目标执行方式

- 文件：`makefiles/test.mk`
- 改动：
  - `test-e2e-live-report` 改为隔离验收模式：
    - 先 stop + 强制清理 celery 进程
    - purge broker 待处理消息
    - 仅启动 `analysis-live` 与 `bulk-live` 两个关键 worker
  - 新增参数：
    - `LIVE_REPORT_BULK_QUEUE_LIST`（默认 `backfill_posts_queue_v2,backfill_queue,compensation_queue`）
    - `LIVE_REPORT_ACCEPTANCE_ARGS`（默认 `--required-tier A_full --max-analysis-attempts 3 --warmup-wait-timeout-seconds 420`）
  - 启动校验改为匹配 live hostname，避免 pgrep 误判。

## 验证结果

1. 定向后端回归：
   - `cd backend && ../.venv/bin/pytest tests/tasks/test_auto_rerun_impl.py tests/core/test_task_system.py::test_task_warmup_auto_rerun_schedules_followup -q`
   - 结果：`3 passed`
2. `make test-e2e-live-report`：
   - 结果：通过（第 2 次分析达到 `A_full`）
   - 成功任务：`8bf9a305-4893-4a3d-bc57-feb3d90a531a`
3. `make test-e2e`（当前正式前端 E2E）：
   - 结果：`21 passed`

## 结论

- `live report` 主阻塞已从“链路卡死/随机失败”推进到“可重复跑通并拿到 A_full”。
- 正式 E2E 保持全绿（`21 passed`），当前世界观下验收闭环成立。
- 下一步重点应转向：
  1. 清理历史 outbox/target 积压，降低 warmup 首轮超时率；
  2. 把 `dev-real` 的后台起服稳定性收口（避免偶发“后端未启动”误报）；
  3. 基于这次隔离验收模式，固化一套「准生产验收模板」用于持续打分。
