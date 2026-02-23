# Phase 33 - facts_v2 审计包 Task3 过期清理任务落地

日期：2025-12-18  
范围：facts_snapshots / facts_run_logs 清理入口 + 日常调度

## 一句话结论

已新增 facts 审计包/运行日志过期清理任务，并接入 UTC 定时调度，确保 90/30/7 到期后自动清理。

## 证据位置（代码为准）

- `backend/app/tasks/maintenance_task.py:cleanup_expired_facts_audit_impl` 过期清理实现
- `backend/app/tasks/maintenance_task.py:cleanup_expired_facts_audit` Celery 任务入口
- `backend/app/core/celery_app.py` 定时调度 `cleanup-expired-facts-audit`
- `backend/tests/tasks/test_cleanup_facts_audit.py` 测试：过期删除 + 调度存在
- `backend/tests/tasks/test_tasks_smoke.py` 维护任务烟测覆盖

## 本次改动

- 新增清理逻辑：按 `expires_at < NOW()` 删除 facts_snapshots / facts_run_logs。
- 增加安全门：环境变量 `ENABLE_FACTS_AUDIT_CLEANUP` 未开启默认跳过。
- 支持 dry_run：可预演统计待清理数量与样本。
- 接入 UTC 定时调度：每天 04:20 (UTC) 触发。

## 测试

- `PYTEST_RUNNING=1 APP_ENV=test DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/reddit_signal_scanner_test pytest -q backend/tests/tasks/test_cleanup_facts_audit.py backend/tests/tasks/test_tasks_smoke.py`

## 落地价值（大白话）

- Gold/Lab/Noise 的审计包按 90/30/7 自动清走，不会越存越炸库。
- 有安全门+预演，不会误删核心数据。

## 下一步

- 进入任务4：补监控指标/告警口径（清理量、失败率、过期堆积）。
