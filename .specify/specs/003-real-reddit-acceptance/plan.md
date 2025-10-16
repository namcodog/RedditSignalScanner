# Implementation Plan: Real Reddit Acceptance

## Summary
在本地环境去掉一切 mock/seed 注入，直接连真实 Reddit API，按“核心成果/业务价值”逐项验收并记录证据。

## Technical Context
- 后端：FastAPI + Celery，真实 Reddit 客户端 `app/services/reddit_client.py`
- 数据：PostgreSQL（`community_pool`, `community_cache` 等），Redis 作为缓存
- 命令：`make dev-real` 启动；`make crawl-seeds` 触发真实爬取

## Step-by-Step Plan
1) 预检
   - `specify check`（确认工具就绪）
   - 确认 `backend/.env` 有 `REDDIT_CLIENT_ID/SECRET/USER_AGENT`
2) 启动真实环境
   - `make dev-real`（不执行任何 seed/mock 注入）
3) 触发真实爬虫
   - `make crawl-seeds`；`make celery-logs` 观察 ready/处理进度
4) 验证社区池（≥100）
   - `GET /api/admin/communities/pool`（数量/字段完整）
5) 验证缓存与 TTL（24 小时）
   - Redis 键：`community:posts:{name}`；PG 表 `community_cache` 的 `ttl_seconds≈86400`
6) 自适应爬虫频率（1–4 小时）
   - 核对 `community_cache.crawl_frequency_hours/crawl_priority` 与命中率关联
7) 社区发现（TF-IDF + 搜索）
   - 触发分析→检查 `/api/admin/communities/discovered`
8) Admin 5 个端点
   - 模板下载/导入/查询/批准/拒绝/禁用均返回 2xx
9) 监控告警指标
   - `/api/admin/dashboard/stats` 出现限流/缓存/爬虫指标
10) 预热报告
   - 通过 `/api/report/{task_id}` 获取完整指标

## Success Criteria
- 分析耗时 30–60 秒（高缓存命中时）
- API 调用 < 60/分钟；社区池可扩展到 250+

## Notes
- 禁用：`make redis-seed`、`make db-seed-user-task`
