# Phase 260 - 48 个残留社区性质 + 生效社区 8 领域覆盖核实

## 背景
- Phase 259 已完成 Dev 库真实整治：
  - 删除 `community_pool` 垃圾 142
  - 删除 `community_cache` 190
  - 删除 `discovered_communities` 垃圾 39
  - 剩余 `community_pool` 垃圾 48
- 用户进一步要求查清两件事：
  1. 这 48 个剩余社区到底是什么？
  2. 当前 141 个生效社区，是否都已经映射到 8 大领域？

## 结论先说

### 1. 剩余 48 个社区是什么？
- 它们不是有效社区
- 它们不是候选社区
- 它们是 **历史引用壳**
- 更具体地说：
  - `is_active = false` 或 `is_blacklisted = true`
  - 但下面还挂着 `posts_raw`
  - 所以数据库不允许直接物理删除

### 2. 当前生效社区是否都映射到 8 大领域？
- **是，当前 141 个生效社区，100% 都映射到了 8 大领域**
- 当前 Dev 库核实结果：
  - 生效社区总数：`141`
  - `categories` 非空：`141`
  - `categories` 为非空数组：`141`
  - `categories` 为空：`0`
  - 非数组脏值：`0`
  - 多领域社区：`0`

## 48 个残留社区的真实性质

### 数据层事实
- 总数：`48`
- `has_posts_raw = true`：`48`
- `has_community_audit = true`：`0`
- `has_category_map = true`：`0`

### 统一口径
- 这 48 个社区当前的正确身份应该是：
  - **历史引用壳 / blocked_garbage / historical_shells**
- 它们的作用只有一个：
  - 给历史 `posts_raw` 提供外键依附
- 它们**不应该**再被当成：
  - 当前有效社区
  - 候选社区
  - 可运营社区

## 48 个残留社区名单
- `r/aliexpressbr`
- `r/amazon_influencer`
- `r/amazonanswers`
- `r/amazonargentina`
- `r/amazonecho`
- `r/amazonfba`
- `r/amazonfbaonlineretail`
- `r/amazonfbatips`
- `r/amazonmerch`
- `r/amazonprime`
- `r/amazonseller`
- `r/amazonsellercentral`
- `r/amazonvine`
- `r/amitheasshole`
- `r/askmen`
- `r/baking`
- `r/bbq`
- `r/beer`
- `r/bigseo`
- `r/breadit`
- `r/childfree`
- `r/climbing`
- `r/cocktails`
- `r/decorating`
- `r/digital_marketing`
- `r/fixedgearbicycle`
- `r/fulfillmentbyamazon`
- `r/geartrade`
- `r/matcha`
- `r/mechanicadvice`
- `r/mommit`
- `r/peopleofwalmart`
- `r/raisedbynarcissists`
- `r/seo_marketing_offers`
- `r/shopify`
- `r/shopifyappdev`
- `r/shopifydev`
- `r/shopifyecommerce`
- `r/shopifyseo`
- `r/sideproject`
- `r/spellcasterreviews`
- `r/stepparents`
- `r/teachers`
- `r/thrifty`
- `r/toolporn`
- `r/trueoffmychest`
- `r/walmart`
- `r/walmart_rx`

## 8 大领域覆盖核实

### 当前 141 个生效社区的领域分布
| 领域 | 数量 |
| --- | ---: |
| `AI_Workflow` | 5 |
| `Ecommerce_Business` | 21 |
| `Family_Parenting` | 19 |
| `Food_Coffee_Lifestyle` | 13 |
| `Frugal_Living` | 14 |
| `Home_Lifestyle` | 30 |
| `Minimal_Outdoor` | 19 |
| `Tools_EDC` | 20 |

### 额外确认
- 当前生效社区里，没有一个社区是“没领域”的
- 当前生效社区里，也没有一个社区同时落多个领域
- 所以当前 Dev 库的 8 大领域池子，是完整而且干净的

## 当前应如何理解数据库

### 真正生效的社区
- 看 `community_pool`
- 条件：
  - `is_active = true`
  - `deleted_at is null`
  - `is_blacklisted = false`
- 当前数量：`141`

### 候选社区
- 看 `discovered_communities`
- 当前数量：`126`

### 历史引用壳
- 就是这剩余的 `48`
- 它们不是“还在用”
- 它们只是“还不能删”

## 下一步建议
1. 先把这 48 个在治理快照里单独命名成 `historical_shells`
2. 后面人和 AI 一眼就知道：
   - 141 个是当前生效
   - 126 个是候选
   - 48 个只是历史壳
3. 再做“分类真相源”口径统一

## 结论
- 48 个残留社区，不是漏删的有效社区，而是挂着历史帖子外键的旧壳
- 当前 141 个生效社区，已经 100% 映射进 8 大领域
