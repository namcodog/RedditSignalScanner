# Phase 119 - 黑名单“污染回流”二次止血：断源 + 清库 + 口径对齐（paused/is_active）

日期：2026-01-20

## 目标（说人话）
把 Phase118 已经清干净的“黑名单/垃圾社区数据”**再次长回来的问题彻底断根**，并把 `community_pool.status` 和 `is_active` 的语义对齐，避免出现“写着暂停但系统还在抓”的假暂停。

## 发生了什么（现象）
1) Phase118 清理后，本应为 0 的黑名单内容又出现：
- `posts_raw` 黑名单：961
- `posts_hot` 黑名单：964
- `posts_quarantine` 黑名单：3

2) `community_pool` 出现“语义打架”：
- `status=paused` 但 `is_active=true`（paused 写着暂停，但系统仍会把它当活跃盘）
- 更严重：部分 `is_blacklisted=true` 的社区被重新打成 `is_active=true`（黑名单变活跃）

3) `crawler_run_targets` 里还残留大量历史“作业单”：
- 黑名单社区：`queued` 23
- 不在 pool 的社区：`queued` 125、`running` 2（时间戳在 2025-12-26~12-30，属于历史卡单/残留）

## 根因（已精确定位）
### 1) “黑名单被重新激活”的根因：发现/审核写回逻辑有 bug
`backend/app/services/discovery/evaluator_service.py::_approve_community` 的 upsert 逻辑在 `ON CONFLICT DO UPDATE` 时**无条件写 `is_active=true`**，导致：
- 即使该社区已经 `is_blacklisted=true`，也会被“审核通过/写回”链路重新激活；
- 一旦激活，巡航/回填就可能再次抓回黑名单内容，形成“污染回流”。

### 2) “残留作业单还在排队”的根因：历史 queued/running targets 未被清理
这些 targets 虽然不应再跑，但 worker/beat 起来后，仍可能继续被消费（或占着状态），造成噪音与不确定性。

## 精确修复（断源 + 兜底）
### A) 断源（代码层）
1) 自动回填规划器跳过黑名单社区：
- `backend/app/services/discovery/auto_backfill_service.py`：`plan_auto_backfill_posts_targets()` 会过滤 `community_pool.is_blacklisted=true` 的社区。

2) 候选验毒回填不对黑名单下单：
- `backend/app/services/discovery/candidate_vetting_service.py`：`ensure_candidate_vetting_backfill()` 增加 hard gate（pool 黑名单直接 return）。

3) 发现审核不再能“激活黑名单”：
- `backend/app/services/discovery/evaluator_service.py`：
  - 若 pool 已 blacklisted：直接拦截，不走 approve；
  - upsert 的 UPDATE 增加 `WHERE community_pool.is_blacklisted IS FALSE`，防止覆盖黑名单状态。

4) 运行时兜底：即使旧 target 还在，也不允许黑名单执行：
- `backend/app/tasks/crawl_execute_task.py`：执行 target 前检查 `community_pool.is_blacklisted`，命中则直接 `fail`（避免“旧 outbox/queued target 把黑名单抓回来”）。

5) 回归测试补齐（防回归）：
- 更新并通过：`backend/tests/tasks/test_discovery_auto_backfill_task.py`
- 更新并通过：`backend/tests/services/test_candidate_vetting_service.py`
- 通过：`backend/tests/services/test_discovery_auto_backfill_service.py`
- 通过：`backend/tests/services/test_evaluator_service.py`

### B) 清库（数据层）
在 `SET LOCAL app.allow_delete='1'` 的受控事务里，二次删除黑名单内容：
- `posts_raw`（cascade 带走 comments/post_scores 等）
- `posts_hot`
- `posts_quarantine`
- `evidences`（本轮为 0）

并批量把历史残留的 targets 直接标记为 failed（避免继续排队/误跑）：
- 黑名单社区的 `crawler_run_targets`：queued/running -> failed（error_code=blocked_blacklisted）
- pool 外社区的 `crawler_run_targets`：queued/running -> failed（error_code=blocked_not_in_pool）

### C) 口径对齐（paused 真暂停）
把“paused 但 active”的矛盾彻底消掉：
- `community_pool`：`status='paused' OR is_blacklisted=true` 的一律 `is_active=false`
- `community_cache`：同步把上述社区 `is_active=false`

## 验收结果（关键数字）
1) 黑名单内容再次归零：
- `posts_raw_blacklisted=0`
- `comments_blacklisted=0`
- `posts_hot_blacklisted=0`
- `posts_quarantine_blacklisted=0`
- `evidences_blacklisted=0`

2) 不再存在“暂停但还在跑”的矛盾口径：
- `pool_paused_active=0`
- `pool_blacklisted_active=0`
- `cache_active_blacklisted=0`
- `cache_active_not_in_pool=0`

3) 不再存在“黑名单/池外还在排队执行”的作业单：
- `crawler_run_targets active_blacklisted_targets=0`
- `crawler_run_targets active_not_in_pool_targets=0`

## 下一步（不做会复发的点）
1) **必须重启 Celery worker/beat** 才能加载新补丁（否则旧进程仍按旧逻辑跑）。
2) 建议加一个本地 daily 自检（SQL）：如果黑名单 posts_hot/posts_raw > 0，直接报警（宁可停、不要污染）。
3) 6 条 `paused + not blacklisted` 社区（r/decorating/r/fixedgearbicycle/r/geartrade/r/matcha/r/thrifty/r/toolporn）当前已被“真暂停”，后续是否要升级为黑名单（按业务口径再拍板）。

