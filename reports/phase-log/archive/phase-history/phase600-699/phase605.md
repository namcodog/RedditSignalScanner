# Phase 605 - 主链样本盘恢复与 readiness 真正过线

## 发现了什么？

- 之前主链一直卡在 `truth-source/readiness`，不是因为恢复脚本没跑，而是 dev 的分类字典本身不完整。
- `community_domain_membership` 缺失的 36 条，不是随机脏数据，而是两类 canonical business category 在 dev 里根本没激活：
  - `Food_Coffee_Lifestyle`
  - `Minimal_Outdoor`
- 语义 coverage 卡住，也不是分析链坏了，而是：
  - `post_scores_latest_v` 里没有足够 recent `core/lab`
  - `semantic_observation` 对 recent posts 基本没有有效覆盖

## 是否需要修复？

- 需要，而且这次修的是主链真实依赖，不是补丁。

## 精确修复方法？

### 1. 修正 business category 根字典

- 新增：
  - `backend/app/services/community/business_category_catalog.py`
  - `backend/alembic/versions/20260330_000001_seed_canonical_business_categories.py`
- 修改：
  - `backend/app/services/community/gold_dev_community_restore_service.py`
- 结果：
  - restore 前先补齐 8 个 canonical business categories
  - `community_domain_membership` 不再因为字典缺键而漏写

### 2. 修回 dev 社区真相层

- 执行：
  - `ALLOW_GOLD_DB=1 scripts/community/restore_dev_community_truth_from_gold.py --write`
- 结果文件：
  - `backend/reports/local-acceptance/gold_dev_restore_1774866488.json`

### 3. 修回样本盘与语义 coverage

- 执行：
  - `make data-score`
  - `make data-score SCORE_POSTS_LIMIT=2500 SCORE_COMMENTS_LIMIT=1000`
  - 直跑 `label_posts_batch(limit=150)`
- 结果：
  - `post_scores_latest_v` 的 recent `core/lab` 样本恢复
  - recent `semantic_observation` 覆盖提升到门禁线以上

## 验证

- `backend/tests/services/community/test_gold_dev_community_restore_service.py`
  - `3 passed`
- `alembic upgrade head`
  - 成功写入 canonical category migration
- `scripts/acceptance/live_report_preflight_gate.py --json-only`
  - `ok = true`
  - `enabled_registry_count = 160`
  - `registry_with_current_membership_count = 160`
  - `approved_registry_count = 160`
  - `active_runtime_count = 160`
  - `recent_posts_count = 1696`
  - `recent_posts_with_semantic_count = 104`
  - `recent_posts_semantic_coverage_ratio = 0.0613`

## 下一步系统性的计划是什么？

1. 不再继续怀疑 DB / 语义底盘，直接回到 open-question live 主链。
2. 如果 live 还失败，只看：
   - query framing / warzone route
   - 报告质量链

## 这次执行的价值是什么？达到了什么目的？

- 把主链 readiness 从“看起来修好了”推进到“真实过线”。
- 之后 live 失败时，可以更有把握地说：底盘不是主因了。
