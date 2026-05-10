# Phase 646 - Topic-Pack 实施结果审计

## 审计结论

`topic-pack` 已经真实接进采集链，但当前还不能说“电商供给已完全按新目标稳定输出”。

本轮更准确的结论是：

- **实现已接通**
  - `source_scope -> search spec -> candidate` 这条链已经带上 `topic_pack_id`
  - quota 也已按合同生效
- **真实供给方向开始变化**
  - `selection-signals` 已经能抓到买家/爱好者社区内容
- **但还有两处明显噪音没收掉**
  - `category-winds / kill-signals` 仍然过度依赖 `AmazonSeller` 这类卖家社区的 listing 流
  - 置顶推广帖会直接污染候选

## 硬发现

### 1. 电商 spec 分布已经按合同切开

`ecommerce-sellers` 当前 spec 数量：

- `selection-signals`: 192
- `category-winds`: 72
- `kill-signals`: 84

这说明供给轴已经从代码层拆开，不再是一个混在一起的电商 scope。

### 2. 选品信号开始能抓到用户侧社区

抽样到的 `selection-signals` listing 来源：

- `BuyItForLife`

真实样本标题方向已经偏消费决策和具体产品，而不是纯卖家后台问题。

### 3. 卖家侧 pack 仍被 sticky/promo 噪音污染

`category-winds` 和 `kill-signals` 在 `AmazonSeller` 的 listing 抽样里，前几条直接出现：

- 社区推广帖
- shipping label 求助

这说明：

- pack 已拆
- 但 listing 入口还会把无价值置顶帖吞进来

### 4. 部分 query 还不够锋利

抽样搜索词里：

- `pet product`
- `product research`
- `amazon seller`

当前结果要么很空，要么很泛，说明 pack 方向对了，但 query 还没完全 productize。

### 5. `topic_pack_id` 目前停在 candidate 层

当前代码里，`topic_pack_id` 已进入：

- scope catalog
- search spec
- candidate mapping
- candidate collector

但还**没有继续参与**：

- draft seed 策略
- review 侧判定
- publish 侧展示或运营分析

这不算主链 bug，但属于“后续可继续用起来”的明确空位。

## 判断

这轮实现没有漏成“白做”，但也没到“完全收工”。

真正遗漏的不是代码断链，而是**噪音治理和 query 收紧**：

1. 卖家社区 listing 需要去 sticky/promo 噪音
2. `selection-signals / category-winds` 的 query 需要再收紧一轮
3. `topic_pack_id` 后面可以继续接进 review / publish 分析，但这不属于当前阻断
