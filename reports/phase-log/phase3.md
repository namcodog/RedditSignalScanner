# Phase 3 自动抓取修复记录

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
