# Phase 71 - 六点核对（1/2/5/6）

时间：2025-12-22

## 目标
- 仅核对 backend 代码层是否落地（不看旧文档）

## 结论（简版）
- 1 社区/热源：机制存在但默认不开（probe_hot 定时与 fallback、weekly discovery 都受开关控制）
- 2 缓存/限流/降级：已实现 cache-first + stale fallback + 429 退避，确实存在“缓存优先/失败回退旧缓存”的路径
- 5 facts_v2 门禁：只有 topic_profile 存在时才触发；否则不会走完整门禁
- 6 反馈回路：有“建议生成 + 人工应用 + 可选自动应用”，默认不自动写回

## 证据（代码位置）
- probe_hot 默认关：backend/app/core/celery_app.py
- probe_hot fallback gate：backend/app/tasks/crawler_task.py
- discovery weekly gate：backend/app/tasks/discovery_task.py
- cache-first + stale fallback：backend/app/services/data_collection.py
- 429 backoff/限流：backend/app/services/reddit_client.py
- facts_v2 gate（topic_profile 才启用）：backend/app/services/analysis_engine.py
- 报告门禁：backend/app/services/report_service.py
- 建议与应用：backend/app/tasks/tier_intelligence_task.py、backend/app/api/legacy/admin_community_pool.py

## 影响/缺口
- 默认开关未启用会导致新社区发现慢、热源重复
- 门禁依赖 topic_profile，未设置时不会触发
