# Phase 35 - facts_v2 审计包 Task5 验收口径与配置清单

日期：2025-12-18  
范围：验收标准 + 配置清单（以代码为准）

## 一句话结论

已输出 facts 审计包的验收口径与配置清单，明确“怎么才算完成、哪些开关和阈值在起作用”。

## 产出文件

- `docs/reference/facts_audit_acceptance.md`

## 测试验证

- `PYTEST_RUNNING=1 APP_ENV=test DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/reddit_signal_scanner_test pytest -q backend/tests/tasks/test_monitoring_facts_audit.py backend/tests/tasks/test_celery_beat_schedule.py backend/tests/tasks/test_cleanup_facts_audit.py backend/tests/tasks/test_tasks_smoke.py`
- 结果：29 passed（含 3 个 warning：pytest 配置项、crypt 弃用、pytest-asyncio loop 提示）

## 核心内容（大白话）

- Gold/Lab/Noise 该存什么、什么时候存、存多久，全部写清楚。
- 清理任务什么时候跑、需要什么开关、会删哪些数据，都有明确口径。
- 监控任务的告警触发条件和阈值，清楚可查。

## 落地价值

- 以后讨论“有没有完成”只看这张验收表，不会再靠口头对齐。
- 运维开关/阈值一眼可见，避免误操作或漏报警。
