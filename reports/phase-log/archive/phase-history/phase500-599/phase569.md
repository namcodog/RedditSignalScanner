# Phase 569 - Rant 社区入口收紧与迁移原话去兜底

## 1. 发现了什么？

这轮继续往下看后，问题已经更具体了：

1. `resolution.subreddits` 仍然太像 LLM 原始建议，不应该直接拿来做 `rant` 的 live 搜索入口
2. `migration_intent.key_quote` 还在用评论首条做兜底，这违反当前“不要写兜底代码”的收口原则
3. 把这两层收掉之后，真正剩下来的主阻塞会更清楚地露出来

## 2. 是否需要修复？

需要，而且这轮适合用小刀收：

- 不用重做整个 retrieval
- 也不用碰 `trending`
- 只把 `rant` 的社区入口和迁移原话兜底先切干净

## 3. 精确修复方法？

这轮做了 3 个后端点的最小改动：

1. `query_planner`
   - `rant` 会先把 LLM subreddit 做直接匹配过滤
   - 已经有贴题社区时，不再继续拼接泛 fallback

2. `search_workflow`
   - `rant` 现在优先使用 planner 收紧后的 subreddits
   - 不再直接吃原始 `resolution.subreddits`

3. `response_bundle`
   - 删除 `migration_intent.key_quote` 的评论兜底
   - 没稳定 destinations 时，`key_quote` 回到 `null`

## 4. 下一步系统性的计划是什么？

下一步固定为：

1. 继续只打 `rant` 的 query 语义层
2. 收掉：
   - `high`
   - `low`
   - `content`
   这类伪锚点
3. 再跑无缓存 live query，看 `top_posts` 是否真正回到“购买/转化”问题本身
4. `trending` 继续单独立案，不和 `rant` 混改

## 5. 这次执行的价值是什么？

这轮的价值是把 `rant` 再往“真实问题模式”推进了一层：

- 社区入口更窄了
- 脏的 migration 原话没了
- 现在留下来的问题，终于更像真正的 query/retrieval 质量问题，而不是系统自己制造的噪音

## 验证

- `SKIP_DB_RESET=1 pytest tests/services/hotpost/test_hotpost_query_planner.py tests/services/hotpost/test_hotpost_search_workflow.py tests/services/hotpost/test_hotpost_response_bundle.py -q`
  - `27 passed`

- `SKIP_DB_RESET=1 pytest tests/services/hotpost/test_hotpost_query_planner.py tests/services/hotpost/test_hotpost_retrieval_precision.py tests/services/hotpost/test_hotpost_detail_builder.py tests/services/hotpost/test_hotpost_query_resolver.py tests/services/hotpost/test_hotpost_preview_projection.py tests/services/hotpost/test_hotpost_response_bundle.py tests/services/hotpost/test_hotpost_mode_contract.py tests/services/hotpost/test_hotpost_search_workflow.py -q`
  - `53 passed`

- 无缓存 `rant`：
  - query=`为什么tiktok上做的内容有流量但却没有转化购买？`
  - `from_cache=false`
  - `subreddits=["r/tiktok","r/tiktokhelp"]`
  - `candidate_subreddits=["r/tiktok","r/tiktokhelp"]`
  - `migration_intent.key_quote=null`

- 无缓存 `trending`：
  - query=`shopify chargeback evidence response workflow`
  - `from_cache=false`
  - `candidate_subreddits=["r/technology","r/startups","r/entrepreneur"]`
  - live 结果仍偏题
  - 这说明本轮没有误伤 `trending`，它还是自己的旧问题
