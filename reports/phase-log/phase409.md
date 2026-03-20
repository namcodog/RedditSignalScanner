# Phase 409 - Phase 21 执行：live A_full 门禁与阻塞打通

## 目标
- 按 `Phase 21` 计划先落地门禁和执行入口，不再靠人工判断验收环境。
- 把 `live report` 验收从单次通过升级为可连跑的硬门槛。

## 本轮落地

### 1) 新增 live 验收前置门禁
- 新脚本：`backend/scripts/acceptance/live_report_preflight_gate.py`
- 关键点：
  - 不再看 `queued` 总量，而是看会真正卡住验收的 stale backlog：
    - `task_outbox_pending_stale`
    - `crawler_run_targets_queued_not_enqueued_stale`
  - 支持 `--strict`，超阈值直接 fail。

### 2) 新增锁阻塞解锁工具
- 新脚本：`backend/scripts/acceptance/unblock_live_acceptance_locks.py`
- 关键点：
  - 检测 `idle in transaction` + 长时间 `Lock` wait 的会话。
  - 支持 `--apply` 执行 `pg_terminate_backend`，清理阻塞连接。

### 3) 新增 stale backlog 清淤工具
- 新脚本：`backend/scripts/acceptance/cleanup_live_acceptance_backlog.py`
- 关键点：
  - 仅清理 stale 噪音：
    - `task_outbox(status=pending)`
    - `crawler_run_targets(status=queued AND enqueued_at IS NULL)`
  - 支持 dry-run / apply。

### 4) Make 入口固化
- 更新：`makefiles/test.mk`
- 新增目标：
  - `test-e2e-live-report-preflight`
  - `test-e2e-live-report-unblock-locks-dryrun`
  - `test-e2e-live-report-unblock-locks-apply`
  - `test-e2e-live-report-cleanup-dryrun`
  - `test-e2e-live-report-cleanup-apply`
  - `test-e2e-live-report-5x`
  - `demo-live-a-full`

## 验证结果

### A. 门禁 + 清淤链路已打通
- 初始 preflight（失败）：
  - `task_outbox_pending=504`
  - `queued_not_enqueued=484`
- 解锁 + 清淤后：
  - `task_outbox_pending=4`
  - `queued_not_enqueued=4`
  - preflight `ok=true`

### B. live A_full 结果门槛当前未通过
- `make test-e2e-live-report-5x` 在第 `1/5` 失败
- 单轮重试（`--max-analysis-attempts 6`）仍失败
- 失败形态一致：
  - 每次 `status=completed`
  - `report_tier=B_trimmed`
  - 无 `analysis_blocked`

## 结论
- 本轮已把 `Phase 21` 的“验收基础设施”全部落地并验证可用。
- 当前主阻塞已明确收敛为：
  - 不是链路挂掉，也不是验收噪音
  - 而是 live 新任务稳定停在 `B_trimmed`，尚未恢复 `A_full` 产出
- 下一步要做的是“tier 上限问题定位”，而不是继续加验收脚本。
