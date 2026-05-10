# Phase 518 - DB 架构如何根治主链与抓取链失配

时间：2026-03-27

## 这次要解决的问题

不是“怎么把 community_pool 再补回来”。

而是：

> 数据库应该怎么设计，才能优雅地承接我们的主链业务
> 以及和数据抓取链稳定协同？

## 当前架构为什么容易坏

### 1. `community_pool` 承担了太多职责

当前它同时像：

- 社区注册表
- 领域映射表
- 治理表
- 调度优先级表
- 社区质量表

这会带来一个问题：

只要其中一个职责出了问题，整张表的“真相”就会一起变脏。

### 2. `community_cache` 持有了不该持有的状态

`community_cache` 本来应该只是运行时抓取状态：

- last_crawled_at
- backfill_floor
- sample_posts
- sample_comments
- coverage_months

但现在它还带了：

- `is_active`

这会和 `community_pool.is_active` 形成双真相源。

只要两边不同步，系统就会出现：

- cache 说这个社区还能抓
- pool 说这个社区不是正式作战名单

然后主链就会变成“有时能跑，有时像开盲盒”。

### 3. `discovered_communities` 和分析副作用链会污染正式池

现在分析/探测流程会往 `community_pool` 写：

- `candidate`
- `inactive`
- `vertical = null`

这意味着：

正式作战名单和候选收件箱被混在同一张表里。

这不是优雅设计。

### 4. 领域映射没有做成强依赖

当前有：

- `community_category_map`
- `vertical_map`
- `warzones.yaml`

但这些东西没有真正形成一个强一致的“领域归属真相源”。

一旦空掉，系统还能继续跑，只是开始偷偷失真。

这就是危险点。

## 根治思路：把数据库分层

目标不是多几张表，而是：

### 每张表只负责回答一个问题

### 一、社区身份层

#### `community_registry`

只回答：

> 这个 subreddit 是谁？

字段应该包括：

- `id`
- `platform`
- `name`
- `name_key`
- `display_name`
- `canonical_status`（live / banned / private / deleted）
- `first_seen_at`
- `last_seen_at`

这层不该出现：

- tier
- active
- vertical
- backfill_status

因为这些都不是“身份”。

### 二、领域归属层

#### `domain_catalog`

只回答：

> 系统当前有哪些领域？

比如：

- `Ecommerce_Business`
- `Tools_EDC`
- `Family_Parenting`
- `AI_Workflow`

#### `domain_version`

只回答：

> 当前系统用的是哪一版领域规则？

这样以后你切到 `crypto / SaaS`，也不是“改几个 yaml 然后祈祷”，而是有版本概念。

#### `community_domain_membership`

只回答：

> 这个社区属于哪个领域？它扮演什么角色？

字段建议：

- `community_id`
- `domain_id`
- `role`（seed / core / expansion / candidate）
- `source`（yaml / manual / llm / heuristic / backfill）
- `confidence`
- `is_primary`
- `effective_from / effective_to`

这是最关键的一层。

以后不要再让 `community_pool.vertical` 这种单字段承担领域语义。

因为社区和领域本来就应该是多对多关系，而且带版本和置信度。

### 三、治理决策层

#### `community_governance_decision`

只回答：

> 这个社区能不能进入正式作战名单？

字段建议：

- `community_id`
- `decision`（pending / approved / rejected / blacklisted）
- `reason`
- `actor`
- `decided_at`
- `expires_at`

这层和 membership 分开后，系统才能分清：

- 这个社区“像不像这个领域”
- 这个社区“当前能不能上生产抓取”

这是两个问题，不该混在一列里。

### 四、运行状态层

#### `community_runtime_state`

只回答：

> 这个社区当前抓到什么程度？

它应该吸收现在 `community_cache` 的核心能力：

- `last_crawled_at`
- `last_attempt_at`
- `backfill_floor`
- `backfill_cursor`
- `backfill_status`
- `sample_posts`
- `sample_comments`
- `coverage_months`
- `crawl_priority`
- `ttl_seconds`

但不再持有：

- `is_active`

因为“能不能抓”应该由：

- `governance_decision`
- `community_domain_membership`

共同决定，而不是 cache 自己说了算。

### 五、候选收件箱层

#### `discovered_communities`

这张表应该保留，但角色要收窄成：

> 候选收件箱

它只能存：

- 新发现的社区
- 发现来源
- 发现次数
- 待审核状态

它不应该再直接或间接污染正式社区池。

### 六、原始内容层

#### `posts_raw`
#### `comments`

这两张表应该继续做：

> 不可变原始事实层

当前方向基本对，但有一条要更明确：

### 原始内容入库不能依赖社区池先完整

也就是：

- 先把内容收进来
- 再做社区映射

不能因为 community_pool 没准备好，就让内容语义层和抓取层一起崩。

### 七、分析上下文层

#### `analysis_route_context`

只回答：

> 这次分析为什么走这个领域、这些社区、这版规则？

字段建议：

- `task_id`
- `domain_id`
- `domain_version_id`
- `route_confidence`
- `selected_communities`
- `allowed_communities`
- `readiness_snapshot_id`
- `remediation_policy`

这样以后你再追“为什么这次漂了”，就不是看日志猜，而是看数据库。

### 八、准备度层

#### `readiness_snapshot`

只回答：

> 某个领域在某个时间点，准备到什么程度？

字段建议：

- `domain_id`
- `snapshot_at`
- `covered_communities`
- `posts_90d`
- `posts_180d`
- `comments_90d`
- `clickable_evidence_count`
- `on_topic_sample_count`
- `readiness_grade`
- `blocked_reason`

这张表会直接把你现在最痛的“开盲盒”问题消灭掉。

### 九、证据追踪层

#### `analysis_evidence_ledger`

只回答：

> 每个结论到底绑定了哪些原始证据？

字段建议：

- `analysis_id`
- `section_key`
- `claim_key`
- `source_type`（post/comment）
- `source_id`
- `reddit_url`
- `community_id`
- `rank`

这张表一旦有了，前后端一致性、证据可点击、为什么这条结论成立，都会稳定很多。

## 对业务主链的好处

这样拆完后，主链会变成：

1. 用户发起任务
2. 路由到某个领域
3. 读取该领域最新 readiness
4. 从 membership + governance 中选正式社区
5. 从 runtime_state 看哪些社区该抓、该补
6. 从 raw content 拿原始帖子/评论
7. 生成 analysis + evidence ledger
8. 输出 report

这个链条里每一步都能被数据库解释清楚。

## 对抓取链的好处

抓取链会变成：

1. seed / manual / heuristic / LLM 发现社区
2. 先进 `discovered_communities`
3. 审核后进入 `community_registry + membership + governance`
4. 运行时只看：
   - approved membership
   - runtime_state
5. 抓取结果写入 raw content
6. runtime_state 更新水位

这样就不会再出现：

- candidate 社区把正式池污染了
- cache 还活着但 pool 已经失忆了

## 迁移顺序

### Task 1：先建新真相源，不急着删旧表

先新增：

- `community_registry`
- `domain_catalog`
- `domain_version`
- `community_domain_membership`
- `community_governance_decision`
- `community_runtime_state`
- `readiness_snapshot`
- `analysis_route_context`
- `analysis_evidence_ledger`

### Task 2：做一次 reconciliation

把现有：

- `community_pool`
- `community_cache`
- `posts_raw`
- `warzones.yaml`
- seed 文件

一起对齐，回灌进新结构。

### Task 3：双写一段时间

先让运行时：

- 旧表继续可读
- 新表开始双写

等验证稳定后，再逐步下线旧字段：

- `community_pool.vertical`
- `community_pool.is_active`
- `community_cache.is_active`

## 最后一句话

这件事的根，不是“community_pool 这张表坏了”。

而是：

> 我们现在把太多不同层级的真相，压在了几张表上。

要根治，必须把：

- 身份
- 归属
- 治理
- 运行态
- 候选态
- 原始事实
- 分析上下文
- 证据追踪

拆开。

这样数据库才能真正服务业务主链，而不是反过来拖垮主链。
