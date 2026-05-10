# phase868

1. 这轮达到的目的
- 对题材树治理落地做了一次代码级保险审计，并把两个真实漏口修掉。

2. 当前状态变化
- 治理审计现在会把 ready draft / breakdown suggestion 算进真实供给池，不再漏算。
- supply / source health 审计不再把同一条计划项在 planned 和 candidate 两侧重复计数。
- `named topic collect` 不再按旧 hot 目标数触发，改成只在真实 hot freshness 缺口下触发。

3. 还没完成什么
- `rotation` 仍是 `rewrite`，当前 `PPC / FacebookAds` 疲劳还在。
- `source_health` 仍是 `rewrite`，`funnel-conversion` 来源仍偏窄。

4. 下一步做什么
- 先收 `rotation rewrite`，再收 `source_health rewrite`，继续按当前活跃 slice 跑治理审计。
