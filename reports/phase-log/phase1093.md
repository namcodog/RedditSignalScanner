# phase1093 - 社区推荐预览落地

这轮目的：把“已有数据 + 语义库 -> 系统生成可服务标签 -> 推荐社区 + 理由 + 证据”先做成后端只读预览，验证链路能不能跑通。

当前状态变化：新增 `community_recommendation_preview` 服务和 CLI，输出 `reports/community-recommendation/preview.md` / `.json`。当前跑出 `3` 个标签、`30` 条推荐样例，且修掉了宽松关键词导致 AI 标签误混电商社区的问题。

还没完成：Dev 数据近期活跃不足，`posts_hot_15d=0`，所以当前没有 `ready` 推荐，只能给出 `historical_depth / watching`。

下一步：补轻量 `15D` 活跃探测和语义证据密度，让推荐结果能从“历史可解释”推进到“当前可服务”。
