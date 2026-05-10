# Phase 536 - 社区真相源统一方案

## 这轮要解决的不是一个 bug

这轮已经确认，社区层存在 6 类核心歧义：

1. 文档写 `community_category_map` 是正式分类真相源，但真实运行仍依赖 `community_pool.categories`
2. 金库只能代表“当前线上运行口径”，不能代表“未来理想架构”
3. 系统长期存在三套分类表达：
   - `community_pool.categories`
   - `community_category_map`
   - `community_registry / membership / governance / runtime`
4. `business_categories` 中存在边界模糊 key：
   - `E-commerce_Ops`
   - `Ecommerce_Business`
5. `categories` 字段历史上既出现过数组，也出现过对象，schema 不统一
6. Dev 曾出现正式社区盘、抓取盘、分类盘相互脱节

所以这轮不能再用“修哪块算哪块”的方式推进，必须彻底统一口径。

## 统一后的唯一真相源

社区相关逻辑以后只允许认这一套 truth-source：

### 1. `community_registry`

负责回答：

- 这个社区是谁
- 它的 canonical identity 是什么
- 是否仍处于启用状态

### 2. `community_domain_membership`

负责回答：

- 这个社区当前属于哪个领域
- 主领域 / 次领域分别是什么

### 3. `community_governance_decision`

负责回答：

- 当前这个领域归属是否正式批准
- 是 review / approved / blocked / archived 哪一种状态

### 4. `community_runtime_state`

负责回答：

- 当前抓不抓
- 抓取优先级是多少
- 运行状态、样本量、成员数、回填状态如何

## 四层数据边界

为了避免再次混乱，社区相关数据必须被固定分层：

### A. Bootstrap 层

只做初始化/恢复/对账：

- `community_expansion_200.json`
- `reddit_200_new.csv`
- 金库只读快照

这些资产不能直接参与主链判断。

### B. Raw Evidence 层

只存真实抓到的事实：

- `posts_raw`
- `comments`
- `semantic_observation`

这一层不负责“社区属于哪个领域”。

### C. Runtime Projection 层

这是旧表过渡层：

- `community_pool`
- `community_cache`
- `community_category_map`

它们目前还保留，是为了兼容恢复与过渡。

但最终不能再承担主判断。

### D. Canonical Truth 层

这是唯一正式真相源：

- `community_registry`
- `community_domain_membership`
- `community_governance_decision`
- `community_runtime_state`

未来主链必须只读这一层。

## 主链切换顺序

### Step 1. 先冻结口径

先把所有社区相关模块的注释、文档、phase-log、key-os 同步到同一套说法：

- Bootstrap 资产不是运行真相源
- `community_pool.categories` 只是旧运行投影
- 主链最终只能认 truth-source 四表

### Step 2. 再切主链读路径

按顺序切：

1. readiness / preflight
2. warzone / route selection
3. auto backfill / community governance
4. report preparation / community recommendation

要求：

- 新代码不得直接以 `community_pool.categories` 作为判断依据
- 必须通过 truth-source read service 读取

### Step 3. 最后退役旧结构

旧表最终只能保留两种角色：

- 兼容投影
- 历史归档

不允许再同时承担：

- 社区身份
- 分类判断
- 正式启停
- 主链决策

## 当前已经具备的前提

- Dev 的正式运行盘已经恢复到和金库一致：
  - `pool_effective = 160`
  - `cache_active = 160`
- Dev 的分类层已恢复：
  - `community_category_map = 228`
- 新真相源当前启用态也已对齐：
  - `registry_enabled = 160`
  - `runtime_enabled = 160`
  - `membership_current = 160`
  - `governance_current = 160`

这说明现在已经具备切主链读路径的条件。

## 下一步执行任务

### Task 1

统一口径和注释：

- 所有社区层服务、脚本、phase-log、key-os 都明确：
  - 谁是 bootstrap
  - 谁是 runtime projection
  - 谁是 canonical truth

### Task 2

把主链读路径切到 truth-source：

- 先从 preflight / readiness / route selection 开始
- 再扩到 remediation / report 相关社区读取

### Task 3

做物理压缩与旧结构退役：

- 清理已停用历史行
- 收口旧表职责
- 避免长期双真相源

## 这轮价值

这轮最大的价值是把“社区层到底该信谁”彻底说死了。

从现在开始：

- JSON/CSV 不再冒充真相源
- 金库不再冒充理想架构
- 旧表不再冒充正式判断层
- 主链最终只认 truth-source 四表

这才是后面所有领域都能稳住的前提。
