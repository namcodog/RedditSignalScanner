# Phase 72 - 默认开关全开

时间：2025-12-22

## 目标
- 把已实现的功能默认打开（不看旧文档）

## 结论（简版）
- 已把关键开关默认值改为开启，社区池自动调级默认开启，并补了迁移更新存量数据
- 已补默认开启单测并通过

## 变更点
- probe_hot 定时雷达默认开启（PROBE_HOT_BEAT_ENABLED）
- probe_hot fallback 默认开启（PROBE_HOT_FALLBACK_ENABLED）
- weekly discovery 默认开启（CRON_DISCOVERY_ENABLED）
- probe 自动触发 evaluator 默认开启（PROBE_AUTO_EVALUATE_ENABLED）
- 自动应用调级建议默认开启（ENABLE_AUTO_TIER_APPLICATION）
- 社区池读取默认走 DB（COMMUNITY_POOL_FROM_DB）
- community_pool.auto_tier_enabled 默认 true，迁移将存量 false 改为 true

## 代码位置
- backend/app/core/celery_app.py
- backend/app/tasks/crawler_task.py
- backend/app/tasks/discovery_task.py
- backend/app/tasks/crawl_execute_task.py
- backend/app/tasks/tier_intelligence_task.py
- backend/app/services/analysis/community_discovery.py
- backend/app/models/community_pool.py
- backend/alembic/versions/20251222_000004_enable_auto_tier_default.py
- backend/.env.example
- backend/scripts/smart_crawler_workflow.py

## 测试
- python -m pytest backend/tests/config/test_default_flags.py backend/tests/tasks/test_tier_intelligence_task.py backend/tests/models/test_tier_intelligence_models.py

## 影响/注意
- 默认全开意味着新社区发现、probe 自动评估与自动调级会自动跑；如需关闭可通过对应 env 置 0/false
