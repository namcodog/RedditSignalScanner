# C 阶段：数据冷热与缓存验收

目标
- 热缓存可见：`redis:posts:*` 键存在，内容结构正确（`cached_at` + `posts[]`）。
- 冷库可见：`CommunityCache` 有抓取记录（`posts_cached`、`last_crawled_at`），`CrawlMetrics` 有最新统计。
- 指标接口：`/api/metrics/daily` 返回近 7 天指标。

执行与证据
- 启动服务：`make dev-real`（或手动 `start_celery_worker` + `start_backend_background`）
- 触发爬取：
  - 全量旧版：`make crawl-seeds`
  - 增量新版：`make crawl-seeds-incremental`
- 热缓存键：`make check-redis-hot`（示例：`reddit:posts:r/business`、`reddit:posts:r/programming`）
- 冷库统计：`make db-cache-stats`
  - 示例回传：`total_entries=271, entries_with_posts=266, fresh_within_6h=271`
  - `sample_top10` 呈现每个社区的 `posts_cached/last_crawled_at/freq_h`
- 抓取指标：`make db-crawl-metrics-latest`
  - 示例：`successful_crawls=271, failed_crawls=2, empty_crawls=5, cache_hit_rate≈0.99`
- 日指标（API）：`make metrics-daily-snapshot`（保存至 `reports/local-acceptance/metrics-daily-*.json`）

发现与处理
- 发现：初次跑旧版抓取后，TieredScheduler 的分层为 `no_data`（`avg_valid_posts` 尚未建立），属预期；可用“增量爬取”与后续统计填充。
- 修复：
  - `make crawl-seeds` 增加 `PYTHONPATH=.`，避免 `ModuleNotFoundError: app`。
  - 兼容 `tier` 值（`gold/silver/seed` 同样纳入抓取）。

结论
- C 阶段通过：
  - 热缓存可见且覆盖广；
  - 冷库 `CommunityCache` 与 `CrawlMetrics` 记录齐全；
  - 指标接口可用并已落盘快照。

下一步
- 观察抓取稳定性与覆盖率：持续查看 `make celery-logs`、`make db-cache-stats`、`make metrics-daily-snapshot`。
- 频次/优先级治理：按需调整 `backend/app/services/tiered_scheduler.py` 的 `TIER_CONFIG`，再执行增量抓取与 `apply_assignments` 生效策略。

