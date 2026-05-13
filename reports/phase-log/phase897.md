# phase897

1. 这轮达到的目的
把 `hotpost` 出卡的系统性主阻断真正打穿：先修 recall，再把 evidence 前移到 candidate 层，并用真实重跑验证结果。

2. 当前状态变化
`platform-policy-shifts` 已不再是 `0`；`all-scope safe + dry_cycle=1` 连续两次重跑都稳定在：
- `candidate_count = 20`
- `candidate_publish_surface_count = 7`
- `blank_priority_clusters = ['small-goods']`
- 候选池里已出现 `4` 张 `group-*` 强证据候选，不再是全量 `1 帖 / 1 社区`

3. 还没完成什么
`small-goods` 仍然是 `0`，但它已经从全局结构性阻断降成单 pack 的 query / 噪声专项问题；另有 1 条 AI upstream 候选仍会被历史 rejection 隐藏。

4. 下一步做什么
后续不再回头改 recall / evidence 主链，只单独做：
- `small-goods` query / subreddit / noise 审计
- 观察 `group-*` 候选在后续运营轮次里是否持续把发布面维持在非零厚度
