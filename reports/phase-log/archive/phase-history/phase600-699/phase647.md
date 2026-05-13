# Phase 647 - 电商 Topic-Pack 尾巴治理

## 结果

针对 Phase 646 审计里暴露出来的两条尾巴，已经完成一轮定向治理：

- 卖家社区 listing 的 sticky / promo 噪音已加过滤
- 电商 3 个 topic-pack 的 query 已从泛词收紧成更像真实信号的词

## 本轮修复

### 1. 卖家社区置顶推广帖去噪

当前对以下 pack 生效：

- `category-winds`
- `kill-signals`

当前会过滤的标题噪音包括：

- `community promotion post`
- `weekly megathread`
- `megathread`
- `share your store`
- `promotion post`

这一步的目标不是做复杂 NLP，而是先把最明显、最稳定的脏源挡掉，避免 `AmazonSeller` 一上来就把候选池污染。

### 2. 电商 query 收紧

#### `selection-signals`

从泛词：

- `pet product`
- `espresso machine`
- `camping gear`

收紧到更具体的需求型词：

- `dog travel accessory`
- `pet hair remover tool`
- `espresso machine for small kitchen`
- `coffee grinder apartment setup`

#### `category-winds`

从泛词：

- `product research`
- `niche`

收紧到更像类目判断的词：

- `niche saturation`
- `seasonal demand shift`
- `amazon niche trend`

#### `kill-signals`

从泛词：

- `amazon seller`
- `fulfillment`

收紧到更像约束风险的词：

- `fulfillment cost`
- `unit economics ecommerce`
- `return rate problem`
- `margin squeeze`

## 验证

已通过定向测试：

```bash
SKIP_DB_RESET=1 pytest \
  backend/tests/services/hotpost/test_source_scope_candidate_collector.py \
  backend/tests/services/hotpost/test_source_scope_catalog.py \
  backend/tests/api/test_hotpost_card_candidates.py -q
```

结果：`12 passed`

## 当前判断

这轮修的是“供给噪音”，不是“内容风格”。

也就是说：

- 电商 feed 现在更不容易被 seller promo 帖带偏
- `selection-signals` / `category-winds` / `kill-signals` 的 query 更接近产品判断语境

下一步如果继续，才值得再做一轮实施结果审计，看真实候选是不是更干净。
