# phase896

1. 这轮达到的目的
- 在 `hotpost` 主链做 recall 第一刀：只动 collector，让重点 recall cluster 在同 pack quota / backfill budget 里不再被普通 cluster 先吃掉，并用真跑验证它是否真能恢复进池。

2. 当前状态变化
- 已补回归测试并通过：同 pack quota / backfill budget 现在会优先 `key-people-and-route / ai-product-and-adoption / platform-policy-shifts`。
- `all-scope safe + dry_cycle=1` 后，离线计划变成 `candidate_count = 15`、`candidate_publish_surface_count = 3`、`weak_candidate_count = 11`。
- 全局空白重点 cluster 从 `4` 个降到 `2` 个，当前剩：`platform-policy-shifts / small-goods`。
- 但证据层没动，所以当前 `15 / 15` 候选仍然全是 `1 帖 / 1 社区`。

3. 还没完成什么
- `platform-policy-shifts` 仍没真正恢复，说明 recall 第一刀只修到一半。
- `small-goods` 还没动，仍是独立 query / 噪声问题。
- evidence 仍是下一主阻断：候选虽增厚，但 publish surface 还只有 `3`。

4. 下一步做什么
- 单独审 `platform-policy-shifts` 为什么在 recall 优先后仍为 `0`。
- 不把 `small-goods` 混进同一修法，单独做 query / 噪声审计。
- 进入 evidence 前移实验，把多帖 / 多社区证据从 grouped draft 前移到 shortlist / candidate 层。
