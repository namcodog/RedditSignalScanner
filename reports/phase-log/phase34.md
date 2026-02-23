# Phase 34 - facts_v2 审计包 Task4 监控/告警落地

日期：2025-12-18  
范围：facts 审计清理监控 + 调度 + 测试

## 一句话结论

已补齐 facts 审计清理监控：能看到过期堆积、最近清理记录与状态，并在异常时告警。

## 证据位置（代码为准）

- `backend/app/tasks/monitoring_task.py:monitor_facts_audit_cleanup` 监控任务实现
- `backend/app/core/celery_app.py` 新增监控调度与监控队列路由
- `backend/tests/tasks/test_monitoring_facts_audit.py` 监控任务测试
- `backend/tests/tasks/test_celery_beat_schedule.py` 调度与路由测试更新

## 本次改动

- 新增监控任务：读取 `maintenance_audit` 最近记录 + 过期堆积量。
- 异常告警：清理缺失/过期堆积超阈值会报警。
- Dashboard 输出：写入 `facts_audit_cleanup` 指标快照。
- 新增调度：UTC 04:40 每日运行。

## 测试

- `PYTEST_RUNNING=1 APP_ENV=test DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/reddit_signal_scanner_test pytest -q backend/tests/tasks/test_monitoring_facts_audit.py backend/tests/tasks/test_celery_beat_schedule.py`

## 落地价值（大白话）

- 你能一眼看出“审计包有没有堆成山”和“清理是不是在按时跑”。
- 出问题会报警，避免数据无限积压导致库变慢。

## 下一步

- 进入任务5：补验收口径与配置清单（阈值/开关/说明）。
