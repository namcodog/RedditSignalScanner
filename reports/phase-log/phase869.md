# phase869

1. 这轮达到的目的
- 把三步治理真正压进默认 workflow，并做了一轮真实审计查漏补缺。

2. 当前状态变化
- 计划重平衡现在只做“优先换”，不再为了治理直接删计划。
- `rotation` 补采改成只拉 `day` 新货；`source_health` 补采继续负责补新社区。
- lane 选择不再绕过 `named topic budget`，同一治理题材不能再为了补位被强塞多次。
- `business-growth-ops` 当前已变成：`allocation=publish`、`rotation=rewrite`、`supply=publish`、`source_health=publish`。

3. 还没完成什么
- gate 还没回到 `publish`，当前仍被 `hot_over_age_limit` 和 `stale_ratio_above_threshold` 卡住。
- `rotation` 还剩 `paid-economics` 的 `signal + breakdown` 社区重复没有收掉。

4. 下一步做什么
- 先处理当前 `PPC` 重复项，再继续补 fresh `hot`，直到 gate 从 `rewrite` 回到 `publish`。
