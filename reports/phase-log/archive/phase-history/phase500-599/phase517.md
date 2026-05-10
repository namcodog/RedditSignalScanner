# Phase 517 - Dev DB 社区池 / 缓存 / 地图视图核查

时间：2026-03-27

## 本轮目标

回答一个很关键的问题：

> Dev DB 到底发生了什么？
> 是最近深度修复把社区列表、索引、地图视图清掉了吗？

## 核查范围

直接检查当前 `backend/.env` 指向的数据库，并确认：

- 当前到底连的是哪个库
- `community_pool`
- `community_cache`
- `community_category_map`
- `community_import_history`
- `community_audit`
- `posts_raw`
- `comments`

## 事实

### 1. 当前连接的确实是 Dev 库

- 数据库：`reddit_signal_scanner_dev`
- 用户：`rss_app`

### 2. 原始数据并没有空

- `posts_raw.total = 12153`
- `posts_raw.is_current = 8527`
- `comments.total = 163`

也就是说，不是“整个库被清空了”。

### 3. 真正出问题的是社区真相源

#### `community_pool`

- 总量：`266`
- active：`1`
- 唯一 active：`r/test`
- 其余 `265` 条基本都是：
  - `tier = candidate`
  - `is_active = false`
  - `vertical = null`

#### `community_category_map`

- 总量：`0`

#### `community_import_history`

- 总量：`0`

#### `community_audit`

- 总量：`0`

### 4. `community_cache` 还留着活跃社区，但和 pool 脱节了

`community_cache` 当前还有 6 条 active：

- `r/parenting`
- `r/newparents`
- `r/daddit`
- `r/beyondthebump`
- `r/babybumps`
- `r/test`

其中前 5 条 Family 相关社区，在 `community_pool` 里并不是 active。

这说明：

- cache 层还记得一部分活跃社区
- 但正式社区池层没有同步恢复

这是一个明确的异常态。

## 代码与文件侧证据

### 1. seed 文件其实还在

- `backend/data/community_expansion_200.json` 存在
- 条数：`200`

说明“种子社区定义文件”本身没有丢。

### 2. loader 不会自动恢复 seed

`CommunityPoolLoader` 的行为是：

- 只有显式执行 `load_seed_communities()`
- 或 runtime 走 `force_refresh`

才会把 seed 灌回 `community_pool`

否则运行时只是读当前 active pool。

### 3. pytest 误伤 dev 的可能性较低

测试配置里有很强的保护：

- 默认 `DATABASE_URL` 指向 `reddit_signal_scanner_test`
- 非 `_test` 库会直接拦截

所以“最近我们跑测试把 dev 库清了”的可能性，目前不高。

## 推断

当前最强推断是：

### Dev 库在 2026-03-17 前后经历过一次重建/重置

支持这个推断的信号：

- `community_pool.first_created_at = 2026-03-17`
- `alembic_version = 20260317_000001`
- `community_import_history = 0`
- `community_audit = 0`

这更像是：

1. Dev 库或这部分表被重新建过
2. 之后没有重新导入正式 seed 社区池
3. 后面分析/探测链自己往 `community_pool` 写了一批：
   - `candidate`
   - `inactive`
   - `vertical = null`

所以今天看到的不是一个“正常运营中的社区池”，而是一个：

### “原始帖子有一些，但正式社区脑图没有恢复”的 Dev 环境

## 结论

这次结论很明确：

- 不是“整个 Dev DB 没数据”
- 不是“这几次修 Full A 时顺手把所有数据清掉了”
- 真正的问题是：
  - `community_pool`
  - `community_cache`
  - `community_category_map`

这三层已经严重失配

## 下一步

1. 先冻结当前 Dev 状态
2. 恢复正式 seed pool
3. 重建 category map
4. 做 pool ↔ cache 一致性校验
5. 再进入 readiness scan 和 live 验收

在这之前，不适合继续把 open-question live 结果当成“系统真实能力”的最终判断。
