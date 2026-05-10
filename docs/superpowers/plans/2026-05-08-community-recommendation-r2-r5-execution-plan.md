# Community Recommendation R2-R5 Execution Plan

## Goal

把 `已有数据 + 语义库 -> 系统生成可服务标签 -> 推荐社区 + 理由 + 证据` 从只读预览推进到后端可验收版本。

## Scope

- R2：补 `15D` 活跃探测合同。
- R3：补语义证据密度，让每个推荐社区有可解释证据。
- R4：补推荐排序和长尾优先规则，泛社区只做热点保底，不霸榜。
- R5：补后端服务化输出合同，仍然只读，不做前端、不做 API、不写生产库。

## Phases

1. R2 活跃探测
   - 步骤：支持从 DB 近期帖子或外部活跃快照合并 `recent_posts_15d / latest_activity_at`。
   - 验证点：有近期活跃和证据的社区进入 `ready`；无近期活跃但有历史证据保持 `historical_depth`。

2. R3 语义证据密度
   - 步骤：把 `semantic_observation + semantic_terms` 转成可读证据短语，进入推荐理由和 JSON。
   - 验证点：推荐项包含 `semantic_terms` 和 `evidence_summary`，不是只给计数。

3. R4 排序规则
   - 步骤：长尾社区优先；泛社区保留热点价值但受预算限制；每个标签的泛社区默认不超过结果的 `30%`。
   - 验证点：推荐列表里泛社区不会挤掉长尾社区，且 `generic_budget` 可在输出中审计。

4. R5 后端服务化
   - 步骤：CLI 输出验收摘要，JSON/Markdown 包含 `ready_count / generic_count / longtail_count / acceptance`。
   - 验证点：一条命令生成可验收报告；不需要用户输入标签；不写 DB。

## Non-goals

- 不做前端。
- 不做 Web/API。
- 不做实时大抓取。
- 不写 Gold DB。
- 不把 `community_pool` 当推荐结果页。
