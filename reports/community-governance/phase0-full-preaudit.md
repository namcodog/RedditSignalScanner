# 社区治理 Phase 0 完整预审包

日期：2026-05-07

## 范围

这是社区池治理预审，不是社区淘汰报告。

本轮只读 Phase 0 审计结果，不写 DB，不改 `community_pool`，不改 supply 配置，不触碰 Hotpost 日运营链和小程序。

输入：
- `reports/community-governance/phase0-audit.md`
- `reports/community-governance/phase0-promote-review.md`
- `docs/reference/community-governance-rules-2026-05-07.md`

## 纠正后的核心口径

`入池` 不等于高频采集，也不等于让某个社区打满内容面。

本轮把 `入池` 定义为：

> 这个社区被承认为有业务价值，可以进入系统学习、采集、分析和后续证据积累范围。

后续再用权重、限额、采集频率和业务线绑定来控制怎么用。

因此 Phase 0 的目标不是砍掉社区，而是把已有初始社区治理成一个能持续学习、能扩长尾、能防泛社区打满的社区资产池。

## 当前资产盘面

当前五类结果仍然有用，但它们只是证据来源，不是等级高低：

| 类型 | 数量 | 正确解释 |
|---|---:|---|
| `promote_candidate` | 69 | Hotpost 已经命中过，但还不在活跃 pool；应优先纳入社区池治理视野。 |
| `keep_active` | 39 | 已在 pool 且有当前证据；默认保持。 |
| `needs_evidence` | 31 | supply / discovery 里已出现，但还缺 Hotpost 证据；不降级，进入活跃度和帖质验证。 |
| `stale_review` | 115 | 旧 pool 里还没被 Hotpost 新链路验证；不代表没价值，不自动删除。 |
| `observation_queue` | 10 | 当前证据弱或待归属；只做低频观察和补证据，不是噪音或黑名单。 |

## PM 只需要审 4 个决策

| 决策 | 默认建议 | 说明 |
|---|---|---|
| 是否把 `promote_candidate=69` 纳入社区池治理候选 | 是 | 它们已经被 Hotpost 命中过，至少值得系统学习。 |
| 是否默认保留 `keep_active=39` | 是 | 它们已经在 pool，且有当前证据。 |
| 是否把 `needs_evidence=31` 做活跃度 / 帖质验证 | 是 | 缺的是证据，不是价值判断。 |
| 是否把 `stale_review=115` 只做旧证据复查 | 是 | 小程序和 Hotpost 是后来模块，没出卡不能推导无价值。 |

## 社区池治理规则

### 1. 泛社区可以入池，但必须限额

泛社区的价值是热点入口、趋势入口、共识变化入口。

它们的问题不是“不能用”，而是容易打满社区池和采集面。

需要限额的社区类型：
- 广告 / 增长泛社区：`r/PPC`, `r/DigitalMarketing`, `r/Google_Ads`, `r/googleads`, `r/adops`
- AI 平台 / 新闻泛社区：`r/OpenAI`, `r/ClaudeAI`, `r/artificial`, `r/singularity`
- 泛工具 / 泛工作流社区：`r/ProductManagement`, `r/productivity`, `r/projectmanagement`
- 泛 SEO / 内容增长社区：`r/content_marketing`, `r/juststart`, `r/Substack`, `r/seogrowth`

预审建议：
- 这些社区可以入池。
- 入池后必须设业务线、采集频率或 topic cap。
- 不允许泛社区把长尾社区挤出默认采集面。

### 2. 长尾社区是重点资产

长尾社区不能因为 Hotpost / 小程序暂时没发卡就被降级。

长尾社区应该看：
- 活跃度：近期发帖数、评论数、回复深度、独立作者数。
- 帖子质量：是否有具体问题、购买摩擦、工具选择、工作流变化、产品取舍。
- 垂直密度：社区是否长期围绕一个具体场景反复产生信号。
- 可学习性：系统能否从里面学到稳定的实体、需求、痛点、话题和相邻社区。

典型长尾候选：
- 电商 / 商品 / 用户需求：`r/AsianBeauty`, `r/SkincareAddiction`, `r/VacuumCleaners`, `r/CampingGear`, `r/ManyBaggers`, `r/EDC`, `r/hobonichi`, `r/stationery`
- 家居 / 工具 / DIY：`r/ApartmentHacks`, `r/homeoffice`, `r/fountainpens`, `r/planners`, `r/3Dprinting`, `r/DIY`, `r/Coffee`, `r/espresso`
- AI 工具链 / 工作流：`r/ClaudeCode`, `r/cursor`, `r/OpenWebUI`, `r/vibecoding`, `r/comfyui`, `r/selfhosted`, `r/n8n`, `r/mcp`
- 卖家 / 平台 / 增长操作：`r/EtsySellers`, `r/AmazonSeller`, `r/FulfillmentByAmazon`, `r/shopify`, `r/b2bmarketing`, `r/sales`, `r/Emailmarketing`

预审建议：
- 长尾社区优先进入系统学习范围。
- 入池前后都用活跃度和帖质验证，不用 Hotpost 出卡数做唯一门槛。

### 3. 旧 pool 不是垃圾池

`stale_review=115` 这个名字容易误导。更准确叫：

> 旧社区池待复查资产。

它只表示这些社区还没被 Hotpost 新链路验证。

第一轮复查只做三件事：
- 查社区是否还活跃。
- 查帖子是否仍有具体需求或场景。
- 查旧 DB / 历史报告里是否有分析价值。

不做三件事：
- 不自动删除。
- 不自动降级。
- 不因为小程序没出卡就判无价值。

## 入池建议

### A. 建议纳入 / 保持社区池

这批是当前社区资产的主体：
- `promote_candidate=69`
- `keep_active=39`

它们合计 `108` 个社区，默认都应进入社区池治理视野。

区别只在后续怎么用：
- 泛社区：入池但限额。
- 长尾社区：入池并重点学习。
- 跨业务社区：入池但绑定业务线。
- 旧证据较弱社区：入池后低频观察。

### B. 建议补活跃度和帖质证据

这批不是 pass 掉，而是等活跃度 / 帖质确认：
- `needs_evidence=31`
- `stale_review=115`

处理方法：
- 先按业务线分组。
- 每组抽样查近期帖子和评论。
- 有活跃、有具体问题、有垂直密度，就继续保留或入池。
- 没活跃、没具体问题、明显跑题，再考虑暂缓。

### C. 暂不直接入池

只有明显错配或无法解释业务价值的社区才暂缓。

当前 `observation_queue=10` 里：
- 可转观察：`r/aiToolForBusiness`, `r/BusinessIntelligence`, `r/carcamping`, `r/dataengineering`, `r/linear`, `r/VacuumCleaners`
- 暂不入池：`r/AynThor`, `r/Denmark`, `r/Leuven`, `r/Yorkies`

这不是黑名单，也不是噪音池，只是不作为第一轮社区池扩充对象。

## 需要修正的旧预审结论

之前的 `promote_ready / guarded_promote / observe_only` 容易被理解成“只批准一小部分社区，其余 pass 掉”。这个口径不再作为当前决策入口。

新的口径是：
- 不用 Hotpost 出卡数砍社区。
- 不用小程序发卡比例砍社区。
- 不把泛社区排除，只限制泛社区使用量。
- 重点让系统学习长尾社区。

## 下一步

如果 PM 接受本口径，下一步不是直接写 DB，而是产出一份只读入池方案：

1. 把 `108` 个已有证据社区分成泛社区、长尾社区、跨业务社区、低频观察社区。
2. 给泛社区设 cap，防止打满。
3. 给长尾社区设活跃度 / 帖质验证字段。
4. 对 `needs_evidence` 和 `stale_review` 做抽样复查方案。
5. 产出 dry-run 表，确认写入 `community_pool` 前后的差异。
