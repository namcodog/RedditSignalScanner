# phase908

1. 这轮达到的目的
   把“补上线卡”的硬规则和配置边界单独梳理清楚，防止后面继续补卡时把主链规则带偏。

2. 当前状态变化
   已新增补卡合同 `docs/reference/hotpost-card-supplement-contract.md`，明确“硬规则不动，补卡只改 collect 输入层，长尾新社区属于结果层价值，不是 gate 豁免”。同时补卡 profile loader 已新增 `scope / pack / cluster / time_filter` 前置校验，内置四档 profile 也已全量自检通过。

3. 还没完成什么
   现在收住的是“规则边界”和“配置入口”，不是已经把 `small-goods` 长尾补卡全部跑完；后面仍要按合同继续看真实出卡结果，筛掉噪音和伪需求。

4. 下一步做什么
   接下来继续按 `selection-30d-small-goods-demand` 和 `selection-30d-small-goods-tail` 跑补卡；优先发有真实需求判断、同时能带出新社区价值的小商品卡，不改 gate，不改发布合同。
