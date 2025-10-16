# Real Reddit Acceptance (Spec)

## Goal
在本地环境彻底移除一切 mock/seed 数据，连接真实 Reddit API，按业务“核心成果”逐项验收。

## Preconditions
- backend/.env 配置：`REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, `REDDIT_USER_AGENT`
- Redis、Celery、Backend、(可选) Frontend 可启动

## Commands (Golden Flow)
1) 启动环境（不注入任何 seed/mock）：
   - `make dev-real`
2) 触发真实爬取（100+ 种子社区）：
   - `make crawl-seeds`
3) 查看进度与日志：
   - `make celery-logs`
   - `tail -f /tmp/backend_uvicorn.log`

## Acceptance Stages
1. 社区池系统
   - 预期：最少 100 个种子社区已载入 DB（`community_pool`）
   - 验证：`psql` 查询或调用 Admin 社区池 API `/api/admin/communities/pool`

2. 智能缓存（Redis + TTL 24h + PG 元数据）
   - 触发后：`community_cache` 存在记录，`ttl_seconds≈86400`
   - 验证：Redis 有键 `community:posts:{name}`；PG 表 `community_cache` 统计字段增长

3. 自适应爬虫（1-4 小时）
   - 验证：`crawl_frequency_hours` 与 `crawl_priority` 随命中率/质量调整（查看 `community_cache` 字段）

4. 社区发现（TF-IDF + Reddit 搜索）
   - 操作：调用分析入口让系统生成关键词→发现候选社区
   - 验证：`/api/admin/communities/discovered` 有新候选

5. Admin 管理（5 个端点）
   - 验证：模板下载、导入、查询、审批/拒绝、禁用社区接口均 2xx

6. 监控告警
   - 验证：限流、缓存健康、爬虫状态指标经 Admin 仪表盘 `/api/admin/dashboard/stats` 可见

7. 预热报告
   - 验证：触发一次完整分析，`/api/report/{task_id}` 返回完整指标

## Success Criteria
- 端到端耗时 30-60 秒（高缓存命中时）；API 调用保持 < 60/分钟
- 社区池可增长到 250+（自动发现 + 人工审批）

## Notes
- 严禁执行：`make redis-seed`、`make db-seed-user-task`（会注入 mock）

