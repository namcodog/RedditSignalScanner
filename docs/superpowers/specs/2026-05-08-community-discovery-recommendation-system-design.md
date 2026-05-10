# Community Discovery And Recommendation System Design

日期：2026-05-08
状态：当前系统设计

后端架构入口：`docs/reference/community-recommendation-backend-architecture-2026-05-08.md`。后续 API / 前端只能接这里定义的应用服务入口，不能重新实现一套推荐链路。

## 1. 目标

交付一个社区发现和推荐系统，不是一个开放搜索框。

用户不输入标签。系统根据已有数据、语义库和社区覆盖能力，告诉用户“你能在这里获得什么信息和价值”。用户只点击系统提供的标签 / 赛道，然后得到推荐社区和理由。

最小产品链路：

```
已有数据 + 语义库
  -> 系统生成可服务标签
  -> 用户点击标签 / 赛道
  -> 推荐相关社区
  -> 给出为什么值得看
  -> Hotpost 继续发现新社区并回流 community_pool
```

## 2. 现有资产

当前不是从零建设。仓库里已经有这些可复用能力：

- `community_pool`：社区总池。Dev 当前 active pool 已到 `356`，但它不是推荐结果页。
- `semantic_terms` / `UnifiedLexicon`：语义库，支持品牌、功能、痛点、L1-L4 层级和权重。
- `content_labels`：帖子 / 评论上的 pain、solution 等标签，是痛点密度和 P/S 比例来源。
- `content_entities`：品牌 / 实体识别，可用于判断社区是否有真实商业讨论。
- `semantic_observation`：统一语义观察账本，能把 rule / LLM / import / reconciled 的观察归一。
- `EmbeddingService` / 混合检索历史能力：可支持关键词之外的语义召回。
- `community_ranker.compute_ranking_scores`：已有社区信号密度评分，包含主题命中、名称相关、痛点强度、相关讨论量、品牌渗透。
- `HotpostCommunityActivityProvider`：能从 Hotpost published cards 聚合社区证据。
- Hotpost topic / named-topic 体系：能提供当前运营正在验证的真实方向。

这些能力的价值是：系统可以先根据“自己有什么数据”生成标签，而不是让用户猜关键词。

## 3. 产品合同

### 用户看到什么

用户先看到一组系统生成的标签 / 赛道，例如：

- 跨境电商选品
- AI 工具工作流
- 宠物 / 小商品需求
- 广告投放与增长
- 众筹 / 预售验证

每个标签都必须有覆盖状态：

- `ready`：有社区池、语义证据和近期活跃证据，能直接推荐。
- `historical_depth`：旧 DB 有深度，但近期活跃还没补证据。
- `watching`：Hotpost 或发现链正在探测，暂时只展示为观察方向。

### 用户得到什么

点击标签后输出社区推荐列表，每个社区至少包含：

- 社区名
- 推荐理由
- 证据来源：Hotpost 卡、旧 DB 帖子 / 评论、语义标签、实体、发现链
- 近期活跃状态：默认看 `15D`
- 社区角色：长尾垂直、泛热点、工具链、平台 / 卖家 / 增长操作
- 风险提示：泛社区、历史数据偏旧、活跃度未知、证据不足

## 4. 系统组件

### 4.1 Capability Tag Builder

职责：生成系统可服务标签，而不是接收用户输入标签。

输入：
- `semantic_terms`
- `content_labels`
- `content_entities`
- `semantic_observation`
- topic profiles / Hotpost named topics
- `community_pool` 覆盖
- Hotpost published card 社区证据

输出：
- 标签名
- 标签解释
- 可服务状态：`ready / historical_depth / watching`
- 关联语义词、实体、topic profile
- 覆盖社区数、近期活跃社区数、证据计数

原则：
- 没有数据覆盖的方向不展示。
- 只有旧数据的方向可以展示为 `historical_depth`，但不能伪装成当前热。
- 标签是产品入口，不是用户自由搜索参数。

### 4.2 Community Evidence Assembler

职责：为候选社区聚合证据。

候选来源：
- `community_pool`
- Hotpost 出卡社区
- `discovered_communities`
- supply config

证据来源：
- 旧 DB posts / comments
- `content_labels` 的 pain / solution
- `content_entities` 的品牌 / 产品 / 平台实体
- `semantic_observation` 的语义账本
- Hotpost published cards
- 近期 `15D` 活跃探测结果

输出：
- 每个社区的证据包
- 证据来源明细
- 近期活跃状态
- 历史深度状态

### 4.3 Community Recommendation Ranker

职责：从候选社区里排出推荐列表。

基础可复用：
- `community_ranker.compute_ranking_scores`

推荐分数建议由 5 个部分组成：

- 语义相关性：标签语义词、实体、观察账本与社区内容是否匹配。
- 社区活跃度：默认 `15D` 是否还有新帖 / 新评论。
- 业务密度：pain / solution / brand / entity 的密度。
- 长尾价值：长尾垂直社区优先，泛社区不能打满。
- 证据可信度：Hotpost、旧 DB、语义账本、发现链是否互相印证。

泛社区规则：
- 泛社区可以进推荐，但只能作为热点 / 大盘真相源。
- 泛社区不能挤掉长尾社区。
- 当泛社区承载当下最热视频 / 最热讨论时，可以通过 hot-floor 进入结果，但要标记原因。

### 4.4 Recommendation Renderer

职责：把推荐结果变成用户能看懂的解释。

输出格式：

```
r/example
为什么推荐：这里集中讨论某类真实需求，最近仍有活跃讨论。
证据：15D 新帖数 / pain 标签 / brand 实体 / Hotpost 卡 / 旧 DB 深度
角色：长尾垂直社区
状态：ready
```

原则：
- 不只给排名。
- 不说“高价值”这种空话，必须说清楚价值来自哪里。
- 历史深度和当前活跃必须分开说。

### 4.5 Application Service Boundary

职责：把数据加载、领域计算、审核表和输出摘要收成一个后端用例入口。

当前入口：

```text
backend/app/services/community/community_recommendation_service.py
```

要求：
- CLI、后续 API 和前端适配层都调用同一个 service。
- service 只读，不持有 `SessionFactory`，不调用治理写库脚本，不 `commit`。
- 脚本只负责参数解析和写报告，不再复制推荐算法。

## 5. 数据流

```
semantic_terms + content_labels + content_entities + semantic_observation
        |
        v
Capability Tag Builder
        |
        v
系统标签 / 赛道列表
        |
用户点击
        |
        v
Community Evidence Assembler
        |
        v
Community Recommendation Ranker
        |
        v
Recommendation Renderer
        |
        v
社区推荐列表 + 理由 + 证据 + 状态
```

Hotpost 回流链：

```
Hotpost 出卡
  -> 识别新社区 / 高价值社区
  -> 回流 community_pool
  -> 进入下一轮标签覆盖和社区推荐
```

## 6. 当前不做

- 不做开放搜索框。
- 不让用户输入标签。
- 不做实时全网抓取。
- 不写 Gold DB。
- 不先上前端 / API。
- 不新建复杂表结构。
- 不把 Phase 0 / 1 / 2 治理状态当推荐结果。

## 7. 第一版交付

第一版只交付离线预览。

输入：
- 系统生成的标签 / 赛道列表。

输出：
- 每个标签下推荐 `10-20` 个社区。
- 每个社区有推荐理由、证据来源、近期活跃状态、社区角色。
- 每个标签有覆盖状态：`ready / historical_depth / watching`。

验收切片：
- 以 `backend/config/community_interest_tags.json` 当前可服务标签为准。
- 验收时重点看标签是否能映射到后台证据，而不是只看某三个旧切片。

验收标准：
- 用户不需要输入任何标签。
- 标签能解释“我们这里能提供什么价值”。
- 推荐结果不是 `community_pool` 库存清单。
- 长尾社区没有被泛社区淹没。
- 旧 DB 深度和 `15D` 当前活跃分开表达。
- 每个推荐社区至少有一条可追溯证据。

## 8. 后续演进

第一版跑通后，再考虑：

- 把推荐结果做成持久化 snapshot。
- 接 API / 前端。
- 加用户行为反馈。
- 让 Hotpost 新社区发现自动进入候选池。
- 定期刷新 `ready / historical_depth / watching` 状态。

这些都在离线预览验收后再做。
