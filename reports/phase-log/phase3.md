# Phase 3 自动抓取修复记录

## Phase 3 US1 洞察卡片接口对齐（2025-10-28）
- **1. 发现了什么问题 / 根因？**
  - 现有后端仍暴露 `GET /api/insights` + query 的旧契约，未对齐 Spec007 要求的 `GET /api/insights/{task_id}` 路径；同时缺少 `InsightService` 聚合层，前端/类型与 response 字段（`time_window`、`evidence`）不一致。
- **2. 是否已精确定位？**
  - ✅ 确认路由与 OpenAPI 基线仍指向旧路径，返回字段命名与最新 spec 不符。
  - ✅ 前端 `insightsService` 直接使用 axios，缺少 API 层封装，类型 `InsightCard` 仍使用 `evidences`、`time_window_days`。
- **3. 精确修复方法？**
  - 后端：新增 `InsightService`（`backend/app/services/insight_service.py`），重写路由为 `/api/insights/{task_id}` 与 `/api/insights/card/{insight_id}`，并输出新的 schema `InsightCardResponse`/`EvidenceItem`（`backend/app/schemas/insight.py`）。
  - 测试：更新 API & 集成用例以覆盖路径、字段改动（`backend/tests/api/test_insights.py`、`backend/tests/integration/test_insights_api.py`）。
  - 前端：补充 `frontend/src/api/insights.ts`、调整 `insightsService`、`InsightsPage`、`InsightCard`、`EvidenceList` 等组件与类型定义（`frontend/src/types/insight.types.ts`）。
  - 文档：新增 US1 验收记录模板 `reports/local-acceptance/us1-insights.md`，便于记录手动验收。
- **4. 下一步做什么？**
  - 运行 `pytest` / `npm run type-check` 验证链路（当前阻塞于 Pydantic 对 `date` 类型的 schema 生成问题，待与团队确认修复路径）。
  - 更新 OpenAPI 基线 & SDK 生成流程，确保后续契约化步骤（Phase5）顺利对接。

## Phase 3 T3.1-T3.6 行动记录（2025-10-20）
- **T3.1 抽样标注**：新增标注工具链，涵盖采样、导出、验证与加载流程（`backend/app/services/labeling/sampler.py`，`backend/app/services/labeling/validator.py`）；配套单测确保 500 条样本覆盖率与合法性（`backend/tests/services/labeling/test_labeling_workflow.py`）。
- **T3.2 阈值网格搜索**：实现评分、Precision@K、F1 与网格搜索逻辑（`backend/app/services/evaluation/threshold_optimizer.py`），结果写入 `reports/threshold_optimization.csv` 并更新 `config/thresholds.yaml`；加入严格单测覆盖（`backend/tests/services/evaluation/test_threshold_optimizer.py`）。
- **T3.3 每日跑分与定时任务**：构建 `DailyMetrics` 数据类与 Celery 计划任务（`backend/app/services/metrics/daily_metrics.py`、`backend/app/tasks/metrics_task.py`），落地 CSV 日志路径 `reports/daily_metrics/YYYY-MM.csv`，新增任务编排测试（`backend/tests/tasks/test_metrics_task.py`）。
- **T3.4 红线检查**：提供红线配置与自动降级策略（`backend/app/services/metrics/red_line_checker.py`），集成到每日任务并同步更新 `config/deduplication.yaml`、阈值配置；完备单测验证四条红线行为（`backend/tests/services/metrics/test_red_line_checker.py`）。
- **T3.5 行动位生成**：引入机会报告构建器（`backend/app/services/reporting/opportunity_report.py`），`run_analysis` 输出 `action_items` 并经 API 下发（`backend/app/api/routes/reports.py`）。
- **T3.6 前后端联调**：更新报告响应类型与导出工具（`frontend/src/types/report.types.ts`、`frontend/src/utils/export.ts`），新增 `ActionItemsList` 组件（`frontend/src/components/ActionItem.tsx`）并在报告页展示行动位（`frontend/src/pages/ReportPage.tsx`）。
- **验证**：关键链路通过 `pytest` 与 `vitest` 定向回归，详见本次提交测试记录。

## 1. 发现了什么问题 / 根因？
- `community_pool` 实际只有 100 条，追溯到 `CommunityPoolLoader` 依旧默认读取旧的 `seed_communities.json`（只有 100 条），并且种子规范没有兼容扩展文件的字段差异。
- `community_cache.quality_tier` 始终停留在 `normal`，增量抓取流程未调用 `TieredScheduler`，导致平均有效帖子数更新后没有反映到 tier。
- Celery Beat 验收窗口内看不到抓取任务，调度仍按 2 小时整点执行，缺少快速启动和 30 分钟以内的周期。

## 2. 是否已精确定位？
- ✅ 已定位至 loader 默认种子路径与字段归一化缺失。
- ✅ 已定位到 `_crawl_seeds_incremental_impl` 只写指标、不刷新 tier 逻辑。
- ✅ 已定位到 beat 配置的 cron 仍为 `*/2` 小时且缺少启动一次性的触发。

## 3. 精确修复方法？
- Loader：改为默认加载 `community_expansion_200.json`，补全字段归一化（tier→priority、daily_posts→estimated_daily_posts 等），导入 200 条并兼容旧格式。
- 增量抓取：在写入 `crawl_metrics` 后实例化 `TieredScheduler`，计算并应用 tier assignments，同步落库。
- Beat 调度：`auto-crawl-incremental` 调整为每 30 分钟执行，补充一次性 5 分钟 bootstrap 任务，并保留 warmup/legacy 任务以通过既有门禁。

## 4. 下一步要做什么？
- 观察下一轮自动抓取后的数据库指标，确认 `community_pool`≥200、`quality_tier` 分布符合阈值。
- 继续跟踪 Celery 日志，确认 5 分钟 bootstrap 成功触发并进入半小时循环。
- 如果后续需要扩展 tier 逻辑，可将 assignments 结果写入监控面板。

## 自检记录
- `pytest backend/tests/services/test_community_pool_loader.py`
- `pytest backend/tests/tasks/test_incremental_crawl_tiers.py`
- `pytest backend/tests/tasks/test_celery_beat_schedule.py`

---

## 结构化问题清单（2025-10-18）修复记录补充

### 问题 1：`crawl_metrics` 模型与数据表字段不一致
- **根因**：模型未同步 2025-10-17 的补字段迁移，导致 `total_communities / successful_crawls / empty_crawls / failed_crawls / avg_latency_seconds` 缺失。
- **修复**：在 `backend/app/models/crawl_metrics.py:21` 起补齐 5 个字段定义并设置 `Numeric(7, 2)` 精度与默认值。

### 问题 2：增量抓取任务未写入新字段
- **根因**：`_crawl_seeds_incremental_impl` 仅传入旧字段，数据库层出现 `NOT NULL` 约束错误。
- **修复**：`backend/app/tasks/crawler_task.py:262` 起补充 11 个指标字段写入，并计算空跑、失败、平均延迟。

### 问题 3：Session 异常未回滚
- **根因**：写入失败后直接继续使用同一 `AsyncSession`。
- **修复**：在异常分支调用 `await db.rollback()`，必要时捕获回滚异常以防二次报错。

### 问题 4：Beat 调度验收阻塞
- **状态**：调度配置已调整为 5 分钟 bootstrap + 30 分钟周期，后续需在线验证。
- **建议验证步骤**：
  1. `psql -U postgres -d reddit_scanner -c "TRUNCATE TABLE crawl_metrics CASCADE;"` 清空历史指标。
  2. `cd backend && ../venv/bin/python3 -c "import asyncio; from app.tasks.crawler_task import _crawl_seeds_incremental_impl; asyncio.run(_crawl_seeds_incremental_impl(force_refresh=False))"` 触发一次增量抓取，并关注输出中的 `tier_assignments`。
  3. `psql -U postgres -d reddit_scanner -c "SELECT quality_tier, COUNT(*) FROM community_cache WHERE avg_valid_posts > 0 GROUP BY quality_tier;"` 复核 tier 分布。
  4. `make warmup-clean-restart` 后等待 5 分钟，`tail -f /tmp/celery_beat.log | grep "auto-crawl-incremental"` 确认 bootstrap 与 30 分钟周期任务均被调度。

### 自检快照
- 已执行：`pytest backend/tests/tasks/test_incremental_crawl_tiers.py`
- 已执行：`pytest backend/tests/tasks/test_celery_beat_schedule.py`
- 待运行（需要真实服务环境）：上述 4 条数据库与 Celery 验证命令

### 追加修复（2025-10-18 验收反馈）
- **Bootstrap 被注释**：Celery Beat 不支持 `one_off`，改为在 `worker_ready` 信号中调用 `trigger_auto_crawl_bootstrap`，只在首次 worker 启动时发送 `tasks.crawler.crawl_seed_communities_incremental`。
  - 参考：`backend/app/core/celery_app.py:150`
  - 自检：`pytest backend/tests/tasks/test_celery_beat_schedule.py::TestCeleryBeatSchedule::test_auto_crawl_bootstrap_uses_worker_signal`
- **并发连接错误**：为每个社区抓取创建独立的 `AsyncSession`，并将默认并发降到 2，同时在 `_mark_failure_hit` 中使用 `AUTOCOMMIT` 减少锁竞争。
  - 参考：`backend/app/tasks/crawler_task.py:25`,`backend/app/tasks/crawler_task.py:171`,`backend/app/tasks/crawler_task.py:222`
  - 自检：`pytest backend/tests/tasks/test_incremental_crawl_tiers.py`
