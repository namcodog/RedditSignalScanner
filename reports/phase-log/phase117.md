# Phase 117 - 本地数据库核查：community_pool / community_cache

日期：2026-01-19

## 目标
根据 DB Atlas 与数据库使用规范，核查本地数据库当前 community_pool 与抓取列表（community_cache 等）实际情况，回答“发生了什么、原来的社区数据去了哪里”。

## 口径依据
- `docs/sop/2025-12-14-database-architecture-atlas.md`
- `docs/sop/数据库使用规范_v2_全景版.md`

## 核查结论（关键事实）

### 1) community_pool 现状
- 总量：196
- 状态分布：lab 106 / active 54 / paused 36
- 活跃与黑名单：
  - `status=lab, is_active=true, is_blacklisted=false`：106
  - `status=active, is_active=true, is_blacklisted=false`：54
  - `status=paused, is_active=false, is_blacklisted=true`：30
  - `status=paused, is_active=true, is_blacklisted=false`：6
- `deleted_at` 为空（0 条），说明当前表里没有显式软删除痕迹。
- 最近更新时间：2026-01-19 22:36:22 +08（多条黑名单记录同一时间更新）。
- 黑名单样例（reason=auto: not in baseline）：r/bitcoin、r/cryptocurrency、r/wallstreetbets 等。

### 2) community_cache（抓取列表/状态）现状
- 总量：231
- 不在 community_pool 的缓存条目：35
  - 缓存存在，但对应社区不在 pool，说明是“残留缓存/历史社区”。
- backfill_status 分布：DONE_12M 145 / ERROR 69 / NEEDS 15 / DONE_CAPPED 2
- last_crawled_at 范围：2025-12-20 04:01:02 +08 ~ 2026-01-19 22:06:02 +08

### 3) 原来的社区数据去了哪里？
- 发现：`community_cache` 里存在 35 条“pool 中不存在”的社区；但 `community_pool` 中并无 `deleted_at` 记录。
- 说明：原来的部分社区已从 community_pool 中被移除（当前表不再存在），但抓取缓存仍保留。
- 辅证：`data_audit_events` 里存在 2025-12-25 的 `manual_soft_delete_20251225` / `manual_blacklist_cleanup_20251225` 记录，但这些 target_id 已不在当前 community_pool 表中，意味着后续可能做过硬清理或表重置。
- `discovered_communities` 中没有这些“缺失社区”的记录（name 不存在），说明它们并未迁移到发现池。

## 细节清单

### A) community_cache 中“找不到 pool 记录”的社区（共 35）
```
r/aliexpressbr
r/amateurroomporn
r/amazon_influencer
r/amazonanswers
r/amazonecho
r/amazonprime
r/amazonvine
r/amitheasshole
r/askmen
r/baking
r/childfree
r/cleaning
r/climbing
r/digitalmarketinghack
r/femalelivingspace
r/homeoffice
r/instantpot
r/mechanicadvice
r/mommit
r/organization
r/peopleofwalmart
r/ppc
r/ppcjobs
r/raisedbynarcissists
r/shopify_growth
r/shopify_hustlers
r/shopifybusiness
r/shopifydropshiphub
r/socialmediamarketing
r/spellcasterreviews
r/stepparents
r/teachers
r/tiktokshopsellersclub
r/walmart
r/walmart_rx
```

### B) discovered_communities
- 总量：37，全部为 pending
- name 为空：0
- deleted_at：0

### C) tier_suggestions / tier_audit_logs
- tier_suggestions：43（全部 pending）
- tier_audit_logs：0

## 结论（一句话）
本地 community_pool 已收缩到 196 条，其中 30 条被“自动黑名单 + paused”，还有 35 条历史社区只残留在 community_cache，说明原来的部分社区已从 pool 中移除但缓存仍在，未迁移到 discovered_communities。

---

## 补充：2026-01-03 “166 → 37” 的最可能原因（强指纹）

### 指纹1：只被“选择性清空”的表，时间都从 2026-01-03 开始
- `community_pool.min_created_at = 2026-01-03 23:15`
- `users.min_created_at = 2026-01-03 14:01`
- `analyses=0`，`tasks.min_created_at = 2026-01-18`，`reports.min_created_at = 2026-01-19`
- 但“历史资产”仍在：
  - `community_cache.min_created_at = 2025-12-06`
  - `posts_hot.min_cached_at = 2025-12-08`
  - `data_audit_events.min_created_at = 2025-12-11`

这不像“自然演进”，更像是有人对一组核心表做了清空/重置，但没动缓存与审计表。

### 指纹2：37 个 discovered_communities 从 2026-01-03 23:15 开始出现
- `discovered_communities.total = 37`
- `first_discovered_at = 2026-01-03 23:15`

解释（说人话）：当 community_pool 被清空后，系统为了“先能跑起来”，会把“探针/发现出来的社区”写进 community_pool（否则 discovered_communities 的外键会失败）。如果这条写入默认是 active，那就会把“候选盘”直接变成“正式盘”，于是出现“37 个垃圾盘顶上来当主盘”。

### 指纹3：repo 里存在一条会清空 community_pool 的脚本，且清空范围和指纹一致
- `scripts/cleanup_test_data.sh` 会执行：
  - `TRUNCATE reports/analyses/tasks/users/community_pool/pending_communities RESTART IDENTITY CASCADE;`
- 该脚本只要在环境里带着 `DATABASE_URL`（指向 `reddit_signal_scanner`）运行，就会得到“社区池被清空、历史任务消失，但缓存/审计还在”的同款指纹。

> 结论：目前最像的根因是 **2026-01-03 附近误运行了清库脚本/重置命令**，导致 166 社区池被清空；随后“探针发现盘”自动写回 community_pool 并被当成 active 使用，于是出现 37 的假主盘。

---

## 补充：已执行的止血/恢复动作（本地）

### 1) 社区池已恢复为“166 活跃盘 + 30 黑名单”
- `community_pool.total = 196`
- `active_not_blacklisted = 166`
- `blacklisted = 30`

同时已落盘两份快照，方便复盘/二次恢复：
- `reports/debug/community_pool_reddit_signal_scanner_before_restore.csv`（恢复前：37）
- `reports/debug/community_pool_rrs_backup_check_final_active_baseline.csv`（基线：166）

### 2) 防止“探针/发现盘污染正式盘”（代码层止血）
- `backend/app/services/analysis_engine.py`：发现社区写回 community_pool 时，默认 `tier=candidate + is_active=false`（只记录/待审核，不参与巡航与分析）
- `backend/app/services/crawl/execute_plan.py`：probe 写回 community_pool 时，默认 `is_active=false`
- 新增回归测试：`backend/tests/services/test_discovered_communities_pool_pollution.py`

### 3) 防止再次误清空主库（脚本护栏）
- `scripts/cleanup_test_data.sh` 新增“非测试库拒绝执行”护栏：
  - 默认只允许清理 `reddit_scanner` 或 `*_test`
  - 如果真要清理 `reddit_signal_scanner`，必须显式 `CLEANUP_ALLOW_NONTEST_DB=1`

---

## 建议（本地下一步怎么走）
1) **先别急着删数据**：现在 pool 已恢复，后续抓取/分析会回到 166 活跃盘；历史污染数据可以先当“噪音样本”留着。
2) 如果你希望 DB “看起来更干净”，再决定是否做一次“黑名单社区 cold 数据清理”（会删 rows，建议先备份/导出）。
3) 以后跑任何 “reset/cleanup” 脚本，都优先用 `reddit_signal_scanner_test`，避免再次误伤主库。
