# Phase 6 - 数据存储维护闭环（2025-10-24）

## 今日目标
- 关闭 P0-1 ~ P0-4 的存储层缺口
- 完整接通物化视图刷新与冷热库清理任务
- 确认分析引擎采集链路真正命中 posts_hot / posts_raw

## 实际产出
- 新增并排期 `refresh_posts_latest` / `cleanup_old_posts` Celery 任务（每小时和每日 03:30）
- 热缓存清理改为直接执行 SQL 函数（每小时第 15 分钟）
- DataCollectionService 拉取顺序重排为 Redis → posts_hot → posts_raw → Reddit API，并回写缓存
- Alembic 迁移补充：先安全删除 `posts_latest` 再转换 `text_norm_hash` 类型，避免物化视图锁定

## 新增优化（P1）
- 热缓存补齐 `author_id` / `author_name`，采集链路与缓存均携带作者信息
- `collect_storage_metrics` 定时任务写入 `storage_metrics` 表，记录冷热库指标与去重率
- `archive_old_posts` + `posts_archive` 表上线，历史版本先归档再交由清理任务删除
- 抓取流程检测到新增/更新后自动调度 `refresh_posts_latest`，保持物化视图新鲜
- `check_storage_capacity` 任务每 6 小时评估数据库大小并按阈值预警

## 验收与验证
- `pytest backend/tests/tasks/test_refresh_posts_latest.py backend/tests/tasks/test_cleanup_old_posts.py backend/tests/tasks/test_cleanup_posts_hot.py backend/tests/tasks/test_celery_beat_schedule.py`
- `pytest backend/tests/services/test_data_collection.py`
- `pytest backend/tests/services/test_incremental_crawler_dedup.py::TestIncrementalCrawlerDedup::test_hot_cache_persists_author_metadata`
- `pytest backend/tests/tasks/test_storage_metrics.py`
- 全部通过（提示：pytest 自带 warning 来自 async 配置，可忽略）

## 风险与后续
- 迁移脚本依赖 Alembic 执行，已在 `backend/tests/conftest.py` 中调用 `alembic upgrade head`，上线需同步执行
- 后续观察：`posts_latest` 行数 > 0、`posts_hot` 自动缩减、`posts_raw` 90 天窗口生效
- 归档任务默认批次 1000，如数据量激增需调大 `batch_size`
- 容量预警阈值默认为 50GB，可通过 `STORAGE_CAPACITY_THRESHOLD_GB` 覆盖

## 下一步建议
1. 在 `make dev-backend` 环境执行一次 `refresh_posts_latest` 与 `cleanup_old_posts` 手动触发，确认行数变化
2. 观察 Redis 命中率与 Reddit API 调用量是否下降，验证采集链路调整效果
3. 将此次测试命令与结果写入上线 checklist，确保运维交接

## 后续迭代（缓存 & 查询优化）
- CacheManager 全面升级为 `redis.asyncio` 客户端，采集/分析及监控链路改为 `await` 非阻塞调用
- 数据采集任务热/冷库命中后自动回写 Redis，并在测试中覆盖 Redis→热层→冷层兜底流程
- Insights API 统计改用 `COUNT(*)` 并支持 `min_confidence` 过滤，新增接口验收用例
- CommunityPoolLoader 重新导入时清空软删除标记，测试验证软删社区可恢复可见
- 数据库连接默认启用连接池，测试环境通过 `SQLALCHEMY_DISABLE_POOL=1` 切回 NullPool，避免生产频繁建连

### 相关测试
- `pytest backend/tests/services/test_cache_manager.py`
- `pytest backend/tests/services/test_data_collection.py`
- `pytest backend/tests/api/test_insights.py`
- `pytest backend/tests/services/test_community_pool_loader_full.py`

## 2025-10-24 扩大验收补充修复
- Insights API 增加 `subreddit` 查询参数并回填过滤逻辑，前后端契约对齐
- Admin 仪表盘分页接口新增 `offset/total` 支持，避免全量加载
- Analysis 任务状态机补充合法转换校验（PENDING→PROCESSING 等），防止非法回退
- CommunityPoolLoader 更新 existing 记录时刷新 `updated_at`
- Admin 社区审批异常捕获新增结构化日志 `safe_int` 辅助函数
- MonitoringService 切换到 `redis.asyncio` 并返回异步统计，测试覆盖同步/异步客户端
- DataCollectionService 增加缓存失败容错，自动退化到 hot/cold storage 并记录 warning
- 新增 trigram 索引用于 community_cache 模糊搜索（`idx_community_cache_name_trgm`）
- 配置默认值改为读取 `POSTGRES_*` / `REDIS_*` 环境变量，可灵活覆盖
- Monitoring 定时任务串联 `cleanup_expired_posts_hot_impl` 与 `collect_storage_metrics_impl`，确保 SQL 函数常态执行

### 新增测试矩阵
- `pytest backend/tests/api/test_admin.py -k paginates`
- `pytest backend/tests/api/test_admin_community_pool.py::test_approve_logs_when_discovered_count_conversion_fails`
- `pytest backend/tests/tasks/test_task_status_transitions.py`
- `pytest backend/tests/services/test_monitoring.py`
- `pytest backend/tests/services/test_data_collection.py::test_collect_posts_handles_cache_failures`
- `pytest backend/tests/migrations/test_community_cache_indexes.py`
- `pytest backend/tests/core/test_db_session.py`
- `pytest backend/tests/core/test_config_defaults.py`
