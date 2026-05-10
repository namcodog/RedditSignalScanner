# Phase 534 - 金库 vs Dev 社区层对账

## 背景

- 当前正在推进 DB 真相源重构。
- 用户提出一个关键建议：
  - 不只盯着 Dev 库看
  - 先把金库 `reddit_signal_scanner` 与 Dev 库 `reddit_signal_scanner_dev` 的社区层做只读对账
  - 确认哪些是原始正式资产，哪些是 Dev 漂移

## 本轮执行

### 1. 只读核查两边数据库

- 金库：
  - `community_pool = 228`
- Dev：
  - `community_pool = 345`

这说明 Dev 当前社区池规模已经明显偏离金库。

### 2. 对账表范围

本轮只对这 4 张表做只读差异：

- `business_categories`
- `community_pool`
- `community_cache`
- `community_category_map`

输出文件：

- [db_gold_vs_dev_community_diff_20260328.json](../../backend/reports/local-acceptance/db_gold_vs_dev_community_diff_20260328.json)

## 关键结果

### 1. 分类字典一致

- 金库与 Dev 的 `business_categories` 都是 9 条 active key：
  - `AI_Workflow`
  - `E-commerce_Ops`
  - `Ecommerce_Business`
  - `Family_Parenting`
  - `Food_Coffee_Lifestyle`
  - `Frugal_Living`
  - `Home_Lifestyle`
  - `Minimal_Outdoor`
  - `Tools_EDC`

这说明分类字典层不是当前差异主因。

### 2. `community_category_map` 在金库和 Dev 都是空的

- 金库：
  - `community_category_map_rows = 0`
- Dev：
  - `community_category_map_rows = 0`

这条结果非常关键：

- 文档里虽然已经把 `community_category_map` 写成正式真相源
- 但真实数据库现状并不是这样
- 至少当前金库和 Dev 都还没真正启用这张表

也就是说，之前“只要把 map 接起来就恢复到线上口径”的假设，并不成立。

### 3. 金库的真实运行口径仍然是 `community_pool.categories`

- 金库有效社区数：
  - `160`
- 金库有效社区中带非空 `categories` 的数量：
  - `160`

- Dev 有效社区数：
  - `101`
- Dev 有效社区中带非空 `categories` 的数量：
  - `0`

这说明：

- 金库当前仍然是“有效社区 + pool.categories”在支撑分类口径
- Dev 的核心问题不是“表没建”
- 而是 **有效社区的 categories 已整体丢空**

### 4. Dev 社区层发生了双重漂移

#### 4.1 正式有效社区明显缩水

- 金库有效社区：
  - `160`
- Dev 有效社区：
  - `101`

差异：

- 只在金库有效、Dev 丢失：
  - `132`
- 只在 Dev 有效、金库没有：
  - `73`

#### 4.2 Dev 多出了一大批“非原正式资产”

Dev-only sample：

- `r/androiddev`
- `r/artificial`
- `r/cloudcomputing`
- `r/cryptocurrency`
- `r/datascience`
- `r/devops`
- `r/indiehackers`
- `r/investing`
- `r/javascript`
- `r/machinelearning`

这说明 Dev 当前有效池中混入了大量“技术泛社区 / 发现链候选 / 非当前正式盘”。

### 5. 抓取列表也跟着漂了

- 金库 active cache：
  - `160`
- Dev active cache：
  - `105`

差异：

- 只在金库 active cache：
  - `129`
- 只在 Dev active cache：
  - `74`

另外 Dev 里还有 4 条 active cache 已经找不到有效 pool：

- `r/babybumps`
- `r/beyondthebump`
- `r/daddit`
- `r/newparents`

状态都还是：

- `is_active = true`
- `crawl_priority = 50`
- `backfill_status = NEEDS`

这说明 Dev 的“正式社区层”和“抓取运行层”已经脱钩。

## 结论

### 1. 金库可以作为对账源，但不能直接等于未来真相源设计

因为这轮确认了：

- 金库本身也还没有真正切到 `community_category_map`
- 它代表的是“当前线上真实运行口径”
- 不是“理想化的新架构状态”

### 2. Dev 当前最严重的问题已经明确

不是单个脚本，不是单个 CSV，不是单个 prompt。

而是：

- `community_pool` 的正式有效盘漂了
- `community_cache` 的抓取运行盘也漂了
- `community_pool.categories` 在 Dev 有效盘里整体丢空
- `community_category_map` 又还没有真正承担真相源职责

### 3. 下一步收口方向

当前 DB 真相源重构不能再抽象讨论，下一步应该明确分两段：

1. 先以金库为只读对照，恢复 Dev 的正式社区身份与抓取运行口径
2. 再把“当前真实口径”迁移到新真相源，而不是拿空的 `map` 直接硬切

## 本轮价值

- 这轮第一次把“金库真实状态”和“Dev 当前漂移状态”同时摆出来了。
- 也把一个关键误区打掉了：
  - 问题不只是 Dev 脏
  - 而是“文档口径”和“真实数据库口径”并不完全一致
- 从现在开始，DB 收口可以按真实差异推进，不再靠猜。
