# Hotpost 补卡合同

更新日期：2026-05-01

这份合同只管一件事：
**补上线卡时，哪些东西是硬规则，绝对不能碰；哪些东西只是补卡配置，可以按需求切。**

## 1. 先记住一句话

补卡是：

- 在既有硬规则上补检索面
- 在既有发布合同上补候选
- 在既有 review / publish 链上补上线卡

补卡不是：

- 改 gate
- 改 lane 定义
- 改发布门槛
- 改日常运营停机规则
- 改发布真相源

## 2. 硬规则层

下面这些属于底层定律，补卡时默认不动：

- `value-threshold publishing`
- `freshness gate workflow`
- `topic tree governance`
- `signal / hot / breakdown` 的正式 lane 定义
- 人审标准与发布前检查
- `release -> mini_snapshot -> miniRelease` 同步链
- `candidates / drafts / releases` 的存储边界

一句话：
**补卡可以补入口，不能改裁判。**

## 3. 可配置层

当前补卡只允许改这些输入项：

- `watch-profile`
- `watch-profile-config`
- `topic-cluster`
- `time-filter`
- `subreddit`
- `query`
- `candidate_cap`

这些配置的作用只有一个：
**决定去哪里找候选。**

它们不负责决定：

- 候选能不能进 publish surface
- draft 能不能发
- gate 最终是 `publish / rewrite / fail`

## 4. 当前补卡入口

当前正式补卡入口是：

```bash
python backend/scripts/hotpost/collect_named_topics.py --watch-profile <profile_id> --json
```

当前配置文件是：

- `backend/config/hotpost_card_supplement_profiles.yaml`
- `backend/config/hotpost_mini_surface_v1.yaml`
- `backend/config/hotpost_named_topic_watchlists.yaml`

当前 loader 是：

- `backend/app/services/hotpost/named_topic_watch_profiles.py`
- `backend/app/services/hotpost/named_topic_watchlist.py`

它的职责只有：

- 读 YAML
- 校验 scope / pack / cluster / time_filter
- 生成 named-topic watch
- 解析默认 preset 和 named-topic registry

它不负责：

- 改 gate
- 改 review
- 改 publish

## 5. 补充展示面合同

当前补卡除了“补候选”，还允许多一层**独立后台分桶**，但规则固定：

- 主前台 freshness 不改
- 老一点但仍有价值的卡，不硬塞回主前台
- 后台继续保留 `supplement surface`
- 前端不新增单独 tab，仍并入原来的卡片列表

当前补充面的合同保留为兼容层，但它**不再决定小程序前台能看到哪些卡**。当前前台口径是：

- 小程序展示全部已发布卡
- `supplement surface` 不再作为前台裁剪器
- `supplement` 相关配置只保留兼容，不再把旧卡挡在小程序外面

原补充面的口径如下，当前仅作历史兼容说明：

- 时间窗：`15d`
- 只承接：
  - 已发布
  - 仍有价值
  - 但超出主前台 freshness 窗口
- 不承接：
  - 未发布候选
  - review 未过的 draft
  - 为了补量硬塞的旧货

当前配置真相源：

- `backend/config/hotpost_mini_surface_v1.yaml`

当前运行边界：

- `main surface` 继续代表“主前台新鲜面”
- `supplement surface` 代表“15 天内仍有价值的补充面”
- 两者共用同一份 `mini snapshot`，但必须靠 `surface_bucket` 解耦
- `supplement surface` 是后台口径，不是前端新增栏目
- 前端只保留原来的 `全部 / 潜力快帖 / 跨区热议 / 近期爆帖`
- 补充卡按自身 `lane / card_type` 并回现有列表，不单独露出“15天补充”

一句话：
**补充面是新选项，不是主 freshness 的豁免。**

## 6. 当前结果层价值

补卡当前默认追 4 类价值：

1. 领域树覆盖更完整
2. 信息更有判断增量
3. 新鲜度仍在可接受窗口内
4. 找到有价值的新社区，尤其是长尾社区

这里要特别记住：

**长尾新社区本身是价值。**

但它是：

- `result-layer value`

不是：

- `gate override`

也就是说：

- 发现了新社区，是加分
- 但信息如果不硬、太旧、太水，还是不能发

## 7. 当前内置补卡 profile

### 跨境 SKU 选品纠偏口径

“选品”不是“送礼建议”。跨境 SKU 选品默认按三层真相源走：

1. 用户/爱好者社区先发现需求：看真实购买、替代、耐用性、复购、场景痛点。
2. 卖家/平台社区只验证商业可行性：看利润、退货、变体、主图、价格、转化、类目拥挤度。
3. 众筹/预售社区只验证早期产品信任：看定价、设计、原创性、交付、backer 反对点。

固定边界：

- `GiftIdeas` 不再是日常跨境 SKU 选品默认来源，只能在明确“礼品线”任务里使用。
- `AmazonSeller / FulfillmentByAmazon / EtsySellers / shopify / ecommerce / TikTokShop` 不能作为品类发现第一入口；它们只做 seller validation。
- 平台税务、客服、发货状态、账号风控、平台抱怨，不算 SKU 选品信号。
- 明天定向补薄优先跑 `crossborder-sku-selection-7d`；跑完再视盘面切 `selection-30d-core / selection-30d-small-goods-demand / selection-30d-brand-opinion`。

当前内置 profile 分这些入口：

- 明日纠偏入口：
  - `crossborder-sku-selection-7d`
- 核心补卡：
  - `selection-30d-core`
  - `selection-30d-small-goods-demand`
- 非 EDC 扩展：
  - `selection-30d-small-goods-broad`
- 品牌 / 众筹补卡：
  - `selection-30d-brand-opinion`
- 跨境礼品补卡：
  - `selection-30d-gift-crossborder`（显式礼品任务才用）
- 情绪价值礼品补卡：
  - `selection-30d-gift-emotional-value`（显式礼品任务才用）
- 长尾探索：
  - `selection-30d-small-goods-tail`
- 可选扩展：
  - `selection-30d-home-decisions`

理解方式固定为：

- `core` = 更稳、更干净
- `crossborder-sku-selection-7d` = 日常 SKU 选品纠偏入口，先用户需求，再卖家验证，再众筹验证
- `small-goods-demand` = 小商品主补卡面，但不再默认让 EDC 吃满
- `small-goods-broad` = 宠物 / 户外 / 家居小物 / 耐用品小配件这些非 EDC 方向
- `brand-opinion` = 品牌溢价、平替、众筹、预售、品牌舆论
- `gift-crossborder` = 显式礼品线，不再默认算 SKU 选品
- `gift-emotional-value` = 显式情绪价值礼品线，不再默认算 SKU 选品
  - 当前更像两类：
    - 升级现有用品
    - comfort / keepsake 但仍是具体商品
- `tail` = 主动探索长尾社区价值
- `home-decisions` = 可选扩展，不默认混进核心流

如果当前盘面已经被 `EDC / flashlight / ManyBaggers` 吃重，默认不要继续硬抬 EDC query，先切：

- `crossborder-sku-selection-7d`
- `selection-30d-small-goods-broad`
- `selection-30d-brand-opinion`

只有用户明确要礼品线，才切：

- `selection-30d-gift-crossborder`
- `selection-30d-gift-emotional-value`

## 8. 审计清单

每次准备补卡前，固定先问这 7 个问题：

1. 这次改的是硬规则，还是只改补卡配置？
2. 这次是为了补覆盖，还是为了硬凑数量？
3. 这次引入的新社区，是否真的带来新判断，而不是只是换了地方重复说？
4. 这次扩大时间窗，是否只是把噪音一起放大了？
5. 这次候选最后仍要不要走同一条 review / publish 链？
6. phase-log 和 key-os 口径有没有跟上，避免“代码已经变了，文档还停在旧世界”？
7. 如果这次要让旧一点但仍有价值的卡可见，是不是走了独立 `supplement surface`，而不是偷偷放宽主 freshness？

## 9. 当前结论

当前补卡的正确姿势就是：

1. 硬规则不动
2. 只在 collect 输入层加配置和选项
3. 用 profile 去补 coverage / freshness / long-tail community discovery
4. 旧一点但仍有价值的卡，走独立 `supplement surface`
5. 最后仍然回到同一套 gate、review、publish 合同

只要这 5 条不破，补卡就不会把主链带偏。
