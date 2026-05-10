# phase892

1. 这轮达到的目的
- 把“供给薄”继续拆到代码级，确认当前不是单纯 recall 问题，也不是单纯 gate 偏严，而是检索面和证据形成同时收缩。

2. 当前状态变化
- 已核实当前盘面：`candidate_count = 11`，四个重点 cluster 仍是 `0`，publish surface 主阻断仍集中在 `single_thread/community weak evidence`、`exploration_requires_two_quotes`、`low_information_density`。
- 已确认检索面仍被 `search_subreddit_limit = 3`、`listing_subreddit_limit = 3`、`subreddit_candidate_cap = 2` 和 pack 级 `candidate_cap` 继续压窄。
- 已确认 raw candidate 在生成时固定 `thread_count = 1`、`community_count = 1`，且 `evidence_quotes` 只保留前 `2` 条；strong tier raw candidate 默认需要后续 grouped draft 才可能补出可过线证据。

3. 还没完成什么
- 还没验证扩宽 query / subreddit / candidate_cap 后，四个重点 cluster 能否先进候选池。
- 还没验证 grouped draft / quote 形成链为什么没把 strong tier 需要的多线程、多社区证据稳定补出来。

4. 下一步做什么
- 先做 recall 侧核查：针对四个重点 cluster 和四个薄 pack 看 pack/cluster 到 query / subreddit / listing 的映射是否还不够宽。
- 再做 evidence 侧核查：专门追 grouped draft、quote、thread/community 聚合链，确认 strong tier 供给为什么在 raw candidate 之后没有被补强。
