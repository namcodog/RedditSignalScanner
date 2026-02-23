# Phase 32 - facts_v2 审计包 Task2 路由落地

日期：2025-12-18  
范围：backend 落库路由（FactsSnapshot / FactsRunLog）

## 一句话结论

已在分析落库阶段接入审计档位路由：Gold 必存审计包，Lab 抽样/告警存审计包，否则写最小日志，Noise 只写最小日志，并落 90/30/7 过期时间。

## 证据位置（代码为准）

- `backend/app/tasks/analysis_task.py:_store_analysis_results`：路由逻辑、过期时间、最小日志写入
- `backend/app/tasks/analysis_task.py:_should_sample_lab_snapshot`：5% 固定抽样
- `backend/tests/tasks/test_facts_snapshots.py`：新增 gold/noise/lab 路由测试

## 本次改动

- 新增路由：按 audit_level + tier/validator 决定写 FactsSnapshot 或 FactsRunLog。
- Gold 即使缺包也生成最小 facts_v2 包，保证可追溯。
- 统一写入 retention_days + expires_at（90/30/7）。

## 测试

- `PYTEST_RUNNING=1 APP_ENV=test DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/reddit_signal_scanner_test pytest -q backend/tests/tasks/test_facts_snapshots.py`

## 落地价值（大白话）

- Gold 不再“丢案发现场”，能稳定复盘。
- Lab 既能抽样留证据，又不把库撑爆。
- Noise 只留最小痕迹，够排查但不浪费存储。

## 下一步

- 进入任务3：补清理任务/指标与过期策略的执行入口（按 90/30/7 清理）。
