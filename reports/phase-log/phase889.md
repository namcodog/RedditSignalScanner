# phase889

## 这轮达到的目的

把 `publish-surface-gate-tiering-v1` 的 winner `contract_tiered_surface_v3` 回灌进默认 publish surface gate。

## 当前状态变化

- gate 已从一刀切改成分层：
  - 硬垃圾过滤层继续硬挡
  - 强证据档继续高门槛
  - 探索档只对薄 pack / 新节点开放轻放
- 定向测试 `22 passed`
- 默认计划 / gate 验证已通过，当前仍是 `all-scope + stable`

## 还没完成什么

- 还没拿到后续 `5` 个新 release 的 live 证据，暂时只能证明“规则已吃进主链”，还不能证明“每天出卡已持续变厚”。

## 下一步做什么

- 固定跟后续 `5` 个新 release 的 gate 放行数、实际发布数、转化率，以及薄 pack / 新节点是否持续出现，同时继续守住 `stable` 和 watch 阈值。
