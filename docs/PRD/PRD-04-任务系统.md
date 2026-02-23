# PRD-04: 任务系统架构（后端现状对齐版）

## 1. 问题陈述

分析任务超过 HTTP 超时，需要异步执行；同时抓取/探针/监控任务并行存在，必须用队列隔离和可靠性配置保证系统稳定。

## 2. 目标
- **异步执行**：API 创建任务后立即返回。
- **队列隔离**：抓取/回填/探针/监控分队列。
- **可恢复**：失败重试 + 任务状态可追溯。
- **可观测**：任务状态缓存 + 诊断接口。

## 3. 解决方案（实际配置）

### 3.1 Celery + Redis
- Broker/Backend 默认：`redis://localhost:6379/1` / `redis://localhost:6379/2`
- Worker 并发：默认 `min(cpu, 2)`（避免 Reddit 限流冲突）
- 可靠性参数：
  - `task_acks_late=true`
  - `task_reject_on_worker_lost=true`
  - `visibility_timeout=3600`
  - `task_max_retries=3`
  - `task_default_retry_delay=60`

### 3.2 队列划分（现状）
- `analysis_queue`
- `patrol_queue`
- `backfill_queue`
- `probe_queue`
- `compensation_queue`
- `maintenance_queue`
- `cleanup_queue`
- `crawler_queue`
- `monitoring_queue`

### 3.3 关键任务类型
- **分析任务**：`tasks.analysis.run`
- **抓取/回填**：`tasks.crawler.execute_target` / `tasks.crawler.crawl_seed_communities_incremental`
- **探针/发现**：`tasks.probe.run_hot_probe` / `tasks.probe.run_search_probe` / `tasks.discovery.run_community_evaluation`
- **监控/指标**：`tasks.monitoring.*` / `tasks.metrics.generate_daily`
- **合同健康度**：`tasks.monitoring.monitor_contract_health`
- **DecisionUnit 产出**：`tasks.tier.emit_daily_suggestion_decision_units`

> 抓取口径与执行流程以 `docs/sop/数据抓取系统SOP_v3_修正版_v3.2.md` 为准。

### 3.4 Beat 调度（核心心跳）
- `tick-tiered-crawl`：每 30 分钟触发巡航
- `monitor-warmup-metrics`：每 15 分钟
- `generate-daily-metrics`：每日 00:00
- `emit-daily-tier-suggestion-decision-units`：每日 01:10（UTC）

### 3.5 任务状态
- DB：`tasks` 表记录状态/重试/失败原因
- 缓存：`TaskStatusCache` 用于 SSE 与 `/api/status` 快速读

---

**文档状态**：已按本地实现对齐（backend）。
