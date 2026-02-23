# facts_v2 审计包验收口径与配置清单（以代码为准）

更新日期：2025-12-18  
说明：本文件基于当前代码行为整理，用于验收与运维对齐。

## 1) 范围

- 审计包落库与路由：`backend/app/tasks/analysis_task.py`
- 清理任务入口：`backend/app/tasks/maintenance_task.py`
- 监控/告警：`backend/app/tasks/monitoring_task.py`
- 定时调度：`backend/app/core/celery_app.py`
- API 默认 audit_level：`backend/app/api/v1/endpoints/analyze.py`

## 2) 验收口径（可量化）

### A. 审计档位与路由

- `audit_level` 允许显式传入；未传时默认：
  - 有 `topic_profile_id` → `gold`
  - 无 `topic_profile_id` → `lab`
- `gold`：必须写 `FactsSnapshot`（即使 facts_v2 包缺失，也要生成最小包）。
- `lab`：`validator_level` 为 `warn/error` 或命中 5% 抽样 → 写 `FactsSnapshot`；否则写 `FactsRunLog`。
- `noise`：只写 `FactsRunLog`。

### B. 质量/状态

- `tier = X_blocked` → `status = blocked`，否则 `status = ok`。
- `validator_level` 默认规则：
  - `X_blocked` → `error`
  - `B_trimmed` / `C_scouting` → `warn`
  - `A_full` → `info`

### C. 保留期

- `gold` 90 天、`lab` 30 天、`noise` 7 天。
- `expires_at = created_at + retention_days`。

### D. 清理行为

- 仅删除 `expires_at < NOW()` 的记录。
- 默认需要开关 `ENABLE_FACTS_AUDIT_CLEANUP` 才执行。
- 每次清理会写入 `maintenance_audit`。

### E. 监控/告警

- 监控任务会输出：
  - `expired_snapshots` / `expired_run_logs` / `backlog_total`
  - 最近一次清理时间与删除量
  - `status`：`ok | disabled | missing | stale`
- 告警触发：
  - `status = missing | stale` 且清理开关已开启
  - `backlog_total > FACTS_AUDIT_BACKLOG_THRESHOLD`

## 3) 配置清单（阈值/开关/说明）

| 配置项 | 默认值 | 作用 | 代码位置 |
| --- | --- | --- | --- |
| `ENABLE_FACTS_AUDIT_CLEANUP` | 未设置(关闭) | 开启/关闭 facts 审计清理 | `backend/app/tasks/maintenance_task.py` |
| `FACTS_AUDIT_BACKLOG_THRESHOLD` | `5000` | 过期堆积告警阈值 | `backend/app/tasks/monitoring_task.py` |
| `FACTS_AUDIT_MAX_STALE_HOURS` | `36` | 清理超时告警阈值(小时) | `backend/app/tasks/monitoring_task.py` |
| `audit_level` | `lab` | 任务审计档位（可显式覆盖） | `backend/app/api/v1/endpoints/analyze.py` |
| `Lab 抽样` | `task_id % 20 == 0` | 5% 抽样存审计包 | `backend/app/tasks/analysis_task.py` |

## 4) 调度（UTC）

| 任务 | 时间 | 说明 |
| --- | --- | --- |
| `cleanup-expired-facts-audit` | 04:20 | 清理过期审计包/运行日志 |
| `monitor-facts-audit` | 04:40 | 监控清理状态与堆积 |

## 5) 运维参数（手动触发）

清理任务支持参数：
- `batch_size`（默认 5000）
- `max_batches`（默认 100）
- `dry_run`（默认 false）

入口：`tasks.maintenance.cleanup_expired_facts_audit`
