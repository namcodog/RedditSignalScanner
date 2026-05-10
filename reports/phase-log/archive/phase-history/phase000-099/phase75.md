# Phase 75 - 打分口径统一

时间：2025-12-23

## 目标
- 点4：避免“入库粗分/正式评分”混用导致口径漂移

## 结论（简版）
- latest 视图改为“只用一种 rule_version”：若存在非 rulebook_v1，则只用非 rulebook_v1；否则回退 rulebook_v1
- 已在测试库与生产库同步迁移到新视图逻辑

## 变更点
- score_latest 视图规则：`backend/alembic/versions/20251223_000001_prefer_primary_scores_in_views.py`
- 视图读法说明同步：`backend/app/db/views.py`
- 单测覆盖“只用单一口径”：`backend/tests/models/test_score_latest_views.py`

## 测试
- python -m pytest backend/tests/models/test_score_latest_views.py

## 迁移执行
- 测试库：升级到 `20251223_000001 (head)`
- 生产库：升级到 `20251223_000001 (head)`

## 影响/注意
- 若正式评分存在，将完全屏蔽 rulebook_v1 粗分，避免混用
