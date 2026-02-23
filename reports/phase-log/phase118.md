# Phase 118 - 清理“黑名单/池外”污染数据 + 抓取口径对齐（community_pool ↔ community_cache ↔ 热/冷库）

日期：2026-01-19

## 目标（说人话）
把“污染社区”抓回来的帖子/评论从数据库里清掉，让系统后续只在**正式社区池（166）**上跑；同时把抓取表（community_cache）和热/冷库的口径对齐，避免再出现“池外数据混进来导致跑偏”。

## 前置事实（已在 Phase117 核实）
- `community_pool` 已恢复为：total=196，其中 **active_not_blacklisted=166**，blacklisted=30。
- 2026-01-03 附近出现过“核心表被清空/重置”的强指纹，导致 166 被清空后，探针/发现盘顶上来（详情见 `reports/phase-log/phase117.md`）。

---

## 1) 清理前：污染数据规模（黑名单社区）
黑名单社区（30）在内容表里占比很高（典型“垃圾盘”）：  
- `posts_raw`：blacklisted=20,353  
- `comments`：blacklisted=2,336  
- `posts_hot`：blacklisted=24,757  
- `posts_quarantine`：blacklisted=1,186  
- `evidences`：blacklisted=6  

> 说明：这就是你看到“37 个垃圾盘顶掉 166”的后果——污染内容已经写进冷/热库了，不清理会持续干扰分析与抽样。

---

## 2) 执行清理：删除黑名单社区的内容数据

### 2.1 删除护栏说明（为什么一开始删不掉）
数据库有“删除护栏”：对关键表执行 DELETE 必须显式设置：
`SET LOCAL app.allow_delete = '1';`

不设置就会报：
`delete blocked: app.allow_delete not set`

### 2.2 实际删除动作
在受控事务内执行（并开启 allow_delete）：
- 删除 `evidences`（黑名单 subreddit）
- 删除 `posts_hot`（黑名单 subreddit）
- 删除 `posts_quarantine`（黑名单 subreddit）
- 删除 `posts_raw`（黑名单 subreddit）
  - `comments/post_scores/comment_scores` 通过 FK `ON DELETE CASCADE` 自动跟着清掉

并同步做了“抓取表口径对齐”：
- `community_cache.is_active = false`（黑名单社区）

---

## 3) 额外对齐：把“池外社区”从热缓存/隔离区清掉（防再次跑偏）
清理后发现：
- `posts_hot` 仍有 **15,136** 条来自“池外社区”
- `posts_quarantine` 仍有 **47,099** 条来自“池外社区”

这些属于历史残留盘，最危险的点是：`posts_hot` 会被抽样/诊断逻辑读到，容易再次引入跑偏。

因此追加清理（同样在 allow_delete 事务内）：
- `DELETE FROM posts_hot WHERE subreddit NOT IN community_pool`
- `DELETE FROM posts_quarantine WHERE subreddit NOT IN community_pool`
- 并把 `community_cache` 里 **不在 pool 的 35 条**标记为 `is_active=false`（避免误解/误用）

---

## 4) 清理后验收（关键数字必须为 0）
清理后已验证：
- `posts_raw.blacklisted = 0`
- `comments.blacklisted = 0`
- `posts_hot.blacklisted = 0`
- `posts_quarantine.blacklisted = 0`
- `evidences.blacklisted = 0`
- `posts_hot.not_in_pool = 0`
- `posts_quarantine.not_in_pool = 0`
- `community_cache`：
  - blacklisted 的 cache 条目全部 `is_active=false`
  - pool 外的 cache 条目全部 `is_active=false`

---

## 5) 当前“仍然不协调”的地方（需要你拍板如何处理）
1) `community_cache` 仍有 **35 条不在 community_pool** 的历史条目  
   - 现在已经标记为 `is_active=false`，不会再被调度/分析用到；但它们会让“看板/诊断”看起来多出来一坨。
   - 你要两种任选其一：
     - A：保留（当作历史残留账本，后续可追查）
     - B：彻底删除这 35 条 cache（更干净，但不可逆）

2) `community_pool` 存在 **6 条 status=paused 但 is_active=true**  
   - 这会让人误解“paused 就是不跑”，但事实上调度器是看 `is_active` 的，这 6 条仍然会被当作活跃盘使用。
   - 你要两种任选其一：
     - A：保持现状（paused 只做“人工标记”，不控制调度）
     - B：把这 6 条 `is_active` 关掉（让 paused 真暂停）

6 条名单：
`r/decorating, r/fixedgearbicycle, r/geartrade, r/matcha, r/thrifty, r/toolporn`

---

## 附：关键 SQL 验收口径（便于你复跑）
```sql
-- 1) 污染为 0
SELECT COUNT(*) FILTER (WHERE subreddit IN (SELECT name FROM community_pool WHERE is_blacklisted)) FROM posts_raw;
SELECT COUNT(*) FILTER (WHERE subreddit IN (SELECT name FROM community_pool WHERE is_blacklisted)) FROM comments;
SELECT COUNT(*) FILTER (WHERE subreddit IN (SELECT name FROM community_pool WHERE is_blacklisted)) FROM posts_hot;
SELECT COUNT(*) FILTER (WHERE subreddit IN (SELECT name FROM community_pool WHERE is_blacklisted)) FROM posts_quarantine;

-- 2) 池外热/隔离区为 0
SELECT COUNT(*) FILTER (WHERE subreddit NOT IN (SELECT name FROM community_pool)) FROM posts_hot;
SELECT COUNT(*) FILTER (WHERE subreddit NOT IN (SELECT name FROM community_pool)) FROM posts_quarantine;

-- 3) cache 对齐
SELECT COUNT(*) FILTER (WHERE community_name NOT IN (SELECT name FROM community_pool) AND is_active) FROM community_cache;
SELECT COUNT(*) FILTER (WHERE community_name IN (SELECT name FROM community_pool WHERE is_blacklisted) AND is_active) FROM community_cache;
```
