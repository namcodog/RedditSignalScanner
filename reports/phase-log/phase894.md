# phase894

1. 这轮达到的目的
- 按 `gstack 想 -> superpowers 做` 的新主链，重新审计“小程序问题”，把“供给薄”的主因从泛化的 `recall + evidence` 继续拆到更精确的代码与运行层。

2. 当前状态变化
- 已重新跑当前真实盘面：`candidate_count = 11`、`candidate_publish_surface_count = 0`、`publish_list_len = 0`；四个重点 cluster 仍是 `0`。
- 已确认主阻断仍集中在：`single_thread_weak_evidence = 8`、`single_community_weak_evidence = 8`、`exploration_requires_two_quotes = 3`、`low_information_density = 2`。
- 已确认当前不是所有重点 pack 都“检索入口天然太窄”：
  - `upstream-winds = 108 specs / quota 3`
  - `tools-efficiency = 96 specs / quota 4`
  - `category-winds = 48 specs / quota 3`
  - `funnel-conversion = 12 specs / quota 4`
  - `selection-signals = 189 specs / quota 7`，但 `small-goods` 当前仍是 `0` 命中
- 已确认更准确的 recall 问题是：spec 展开后，重点 cluster 仍会在 pack 共享 quota 与 subreddit cap 中被更强 cluster 吞掉。
- 已确认 evidence 问题仍是结构性硬伤：raw candidate 生成时仍固定 `thread_count = 1`、`community_count = 1`，且 `evidence_quotes` 只保留前 `2` 条；当前候选池 `11` 条全部都是 `1 帖 / 1 社区`，天然难过 strong tier。

3. 还没完成什么
- 还没验证把重点 cluster 从 pack 共享 quota 中解耦后，`key-people-and-route / platform-policy-shifts / ai-product-and-adoption` 是否能先进候选池。
- 还没验证把多帖 / 多社区证据前移到 shortlist 或候选聚合层后，publish surface 是否会从 `0` 恢复到可发布。
- `small-goods` 仍未解释清楚：它当前更像“spec 很多但真实命中弱/噪声高”，不能和其他重点 cluster 混成同一种问题。

4. 下一步做什么
- 先做 recall 侧实验：把重点 cluster 从 pack 共享 quota 里拆出来，至少做 cluster-aware quota / shortlist，验证重点 cluster 是否不再被同 pack 内的强 cluster 吞掉。
- 再做 evidence 侧实验：把多帖 / 多社区证据前移到 shortlist 聚合或候选层，而不是继续只靠后置 grouped draft 补强。
- `small-goods` 单独做 query 质量与噪声审计，不再和 `upstream-winds / tools-efficiency` 共用同一套解释。
