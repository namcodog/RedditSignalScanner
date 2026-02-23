# Phase 31 - noise 清理口径加固：绝不误删 lab/core（以 comments.business_pool 为准）

日期：2025-12-18  
范围：后端维护任务逻辑；不修改历史数据，只是让后续清理更“稳”。

## 一句话结论

发现 `comment_scores_latest_v` 与 `comments.business_pool` 存在不一致（库里有 `1705` 条 “comments 还是 lab/core，但 score 标成 noise” 的记录）。  
为了严格遵守“**别动 lab/core**”的原则，后续 noise 清理**只按 `comments.business_pool='noise'`** 来删，评分结果不再参与删除判定。

---

## 统一反馈（大白话 5 问）

### 1）发现了什么问题/根因？
- 评分表是“派生口径”，并不总是与 `comments` 表当前的 `business_pool` 一致。
- 如果清理逻辑按 “scores 优先” 的口径，就会出现：**comments 明明标的是 lab/core，也可能被当成 noise 删掉**（只要 score 标 noise 且过期）。

### 2）是否已精确定位？
- 不一致现象可用 SQL 直接验证（示例）：
  - `comments.business_pool IN ('lab','core') AND comment_scores_latest_v.business_pool='noise'`
- 清理判定点在：`backend/app/tasks/maintenance_task.py:cleanup_noise_comments_impl`

### 3）精确修复方法？
- 清理候选的判定改为：
  - **只按** `COALESCE(comments.business_pool,'lab')='noise'`
  - 不再 `JOIN comment_scores_latest_v` 来决定删不删
- 结果：后续清理不会误删任何 `lab/core`（以 `comments.business_pool` 为准）。

### 4）下一步做什么？
- 等你恢复 Celery beat 后，建议把清理任务作为“日常保洁”跑起来（小批量、持续跑），但仍保留环境变量开关：`ENABLE_COMMENTS_NOISE_CLEANUP=1` 才执行。
- 那 1705 条 “lab/core 但 score=noise” 的不一致数据，建议单独做一次对账：到底以哪个口径为准（再决定要不要修正/重算 score）。

### 5）这次修复的效果是什么？达到了什么结果？
- 未来清理严格满足你的底线：**不动 lab/core**。
- 单测通过：`backend/tests/tasks/test_noise_comments_cleanup.py`

---

## 本次改动清单（代码证据）

- `backend/app/tasks/maintenance_task.py`
- `backend/tests/tasks/test_noise_comments_cleanup.py`

