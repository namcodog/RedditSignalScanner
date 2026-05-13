# phase788 - 第一轮供给补位（signal + 缺失 pack）

## 本轮目标

按 key-os 的 `pack programming v1` 与 `supply repair budget v1` 结果，先把系统补到“稳定日更 10 张”这一档。

最小补货预算：

- `signal lane +5`
- `ai-automation:agent-builder +2`
- `business-growth-ops:funnel-conversion +1`
- `ecommerce-sellers:category-winds +1`

## 实际改动

本轮只做供给补位，不改 prompt、不改 lane 定义、不改 schema。

生产文件：

- `backend/config/hotpost_supply_discovery_v2.yaml`
  - 扩了 `agent-builder / funnel-conversion / category-winds` 的 search 面和 candidate cap
  - 给缺口 pack 增加了更宽的 subreddit、keyword 和 template query 预算
- `backend/app/services/hotpost/named_topic_watchlist.py`
  - 新增专项补位 watchlist：
    - `mcp-workflows`
    - `checkout-conversion`
    - `category-demand-shift`
  - 新增 preset：
    - `supply-repair-v1`

测试文件：

- `backend/tests/services/hotpost/test_reddit_search_spec_builder.py`
- `backend/tests/services/hotpost/test_named_topic_watchlist.py`

## 执行过程

1. 修正当前 search allocator 的脆弱测试断言。
2. 运行三条 scope 的安全采集：
   - `ai-automation`
   - `business-growth-ops`
   - `ecommerce-sellers`
3. 运行专项补位：
   - `collect_named_topics.py --preset supply-repair-v1 --mode safe --json`
4. 回填题材元数据：
   - `sync_topic_metadata.py --json`
5. 运行离线发布计划：
   - `run_offline_publish_plan.py --limit 10 --output backend/tmp/offline-publish-plan.json`

## 结果

### 测试

- `13 passed`

### 候选库存变化

基线：

- 总候选：`15`
- lane：
  - `signal = 10`
  - `hot = 5`
- pack：
  - `ai-automation:agent-builder = 0`
  - `business-growth-ops:funnel-conversion = 0`
  - `ecommerce-sellers:category-winds = 0`

补位后：

- 总候选：`28`
- lane：
  - `signal = 21`（`+11`）
  - `hot = 7`（`+2`）
- pack：
  - `ai-automation:agent-builder = 4`（`+4`）
  - `business-growth-ops:funnel-conversion = 4`（`+4`）
  - `ecommerce-sellers:category-winds = 4`（`+4`）

### 专项补位命中

- `watch_count = 3`
- `candidate_count = 10`
- 实际补进：
  - `agent-builder = 4`
  - `funnel-conversion = 4`
  - `category-winds = 2`

### metadata 同步

- `candidates total = 28`
- `with_topic_pack_id = 28`
- `with_topic_cluster_id = 28`
- `with_named_topic_ids = 10`

### 离线发布计划（limit=10）

- 计划文件：
  - `backend/tmp/offline-publish-plan.json`
- lane：
  - `hot = 5`
  - `breakdown = 5`
- scope：
  - `ai-automation = 5`
  - `business-growth-ops = 3`
  - `ecommerce-sellers = 2`
- pack：
  - `ai-automation:tools-efficiency = 1`
  - `ai-automation:upstream-winds = 3`
  - `ai-automation:agent-builder = 1`
  - `business-growth-ops:paid-economics = 2`
  - `business-growth-ops:organic-discovery = 1`
  - `ecommerce-sellers:selection-signals = 2`

## 判断

- 第一轮供给补位目标已达到。
- `signal lane +5` 已超额完成，实际补到 `+11`。
- 三个关键缺失 pack 都已经补出来，且都超过最小预算。
- 当前 `offline publish plan(limit=10)` 仍显示 `signal = 0`，不是因为 signal 缺货，而是因为现有 10 张投影会优先吃掉现成的 `hot / breakdown` ready draft 与货架底线。
- 这说明本轮问题主要已经从“缺 pack、缺 signal”切到了“离线投影对 signal 露出不足”，不再是供给断层。

## 发布链影响

- 本轮没有改发布内容，也没有重建 release。
- 当前 release 维持：
  - `release-6fb115e4b88a`

## 结论

- 先补供给，再谈更高阶编排，这条路线是对的。
- 第一轮补位已经把系统从“缺关键 pack”拉到了“可以支撑 10 张日更供给”的门槛线上。
