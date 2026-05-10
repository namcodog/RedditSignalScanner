# Phase 258 - 社区领域映射真相核实（Dev 库）

## 背景
- 在 Phase 257 之后，外部复核提出一个新判断：
  - `CommunityGovernanceService` 没有读取 `community_category_map`
  - 因此 `phase257` 的 8 大领域分布可能只是按社区名推断，不是真实 DB 映射

## 本次核实范围
- 数据库：`reddit_signal_scanner_dev`
- 核实对象：
  - `business_categories`
  - `community_category_map`
  - `vertical_map`
  - `community_pool.categories`
  - `CommunityGovernanceService._serialize_pool_row()`

## 核实结果

### 1. 代码层面
- `CommunityGovernanceService._serialize_pool_row()` 目前确实只读：
  - `row.categories`
- 它没有 `JOIN community_category_map`

### 2. 当前 Dev 库真实数据
- `business_categories`：`9`
- `community_category_map`：`0`
- `vertical_map`：`0`
- 当前有效池社区（`is_active=true AND deleted_at IS NULL AND is_blacklisted=false`）：`141`
- 其中 `community_pool.categories` 非空的有效社区：`141`

### 3. 当前 8 大领域分布的真实来源
- `phase257` 的 8 大领域分布，**不是按社区名推断出来的**
- 它来自当前 Dev 库里 `community_pool.categories` 这个 JSON 字段
- 当前 Dev 库并不存在可供治理快照读取的 `community_category_map` 真实映射数据，因为这张表现在是空的

### 4. 结论
- 外部判断“治理服务没接 `community_category_map`”这件事，**代码层面成立**
- 但外部判断“所以 phase257 的领域分布是靠社区名猜的”，**在当前 Dev 库上不成立**
- 当前 Dev 库里，Round 3 治理快照读到的分类是真实存在于 `community_pool.categories` 的

## 风险提示
- 当前系统在“社区领域分类”的真相源上，仍然存在历史口径混杂风险：
  - 有代码/迁移围绕 `business_categories` / `community_category_map`
  - 但当前 Dev 库实际生效的是 `community_pool.categories`
- 这不是 Phase 257 报告失真，但说明后续最好继续收口“分类真相源”：
  - 要么正式宣布 `community_pool.categories` 为当前治理快照唯一真相源
  - 要么补一层 fallback：
    - 优先 `community_pool.categories`
    - 如果为空，再读 `community_category_map`
    - 并输出 `category_source`

## 当前统一口径
- **对当前 Dev 库来说**：
  - 社区是否生效：看 `community_pool`
  - 社区属于哪个领域：当前治理快照看 `community_pool.categories`
- `community_category_map` / `vertical_map` 当前不承载有效治理快照数据

## 后续建议
1. 不需要推翻 `phase257` 的 8 大领域分布结论
2. 下一步如果继续做“社区分类真相源收口”，建议单开一个小修复：
   - 给治理快照补 `category_source`
   - 再决定是否支持 `community_category_map` fallback
