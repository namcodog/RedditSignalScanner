# Phase 514 - Hotpost 第三刀：加 Reddit 风控护栏，并把首轮 recall 收轻

## 本轮目标

按 Phase 513 暴露出来的真实问题，推进第三刀：

- 不再让首轮 live 抓取过重
- 给 Reddit 调用补硬风控，优先保护账号和 client
- 把补证继续留在预算内，不拿 429 风险换结果

## 已完成

### 1. Hotpost Runtime 新增 Reddit 风控配置

已修改：

- `backend/config/hotpost_quality.yaml`
- `backend/app/services/hotpost/hotpost_config.py`

新增配置块：

- `reddit_guardrails`

当前已收口的配置项：

- `initial_query_parts_limit`
- `initial_subreddits_limit`
- `remediation_query_parts_limit`
- `remediation_subreddits_limit`
- `max_posts_per_subreddit`
- `max_comment_posts`
- `circuit_breaker_cooldown_seconds`

这意味着：

- 首轮 query parts 有明确上限
- 首轮 subreddit fanout 有明确上限
- 评论深拉也有明确上限
- 429 后不会继续硬撞 Reddit

### 2. 首轮 recall 已收轻

已修改：

- `backend/app/services/hotpost/search_workflow.py`
- `backend/app/services/hotpost/evidence_collection_workflow.py`
- `backend/app/services/hotpost/service.py`

当前行为：

- 首轮 evidence collection 只吃受限后的 `query_parts`
- 首轮候选 subreddit 也只保留前几项，不再一上来横向铺开
- remediation 回合同样受独立的 query/subreddit 限制
- 评论抓取从原来的固定深拉，改成吃 `max_comment_posts`

关键口径：

- 首轮尽量轻
- 扩搜更多下沉到 remediation
- 评论抓取永远有边界

### 3. 增加 Reddit circuit breaker

已修改：

- `backend/app/services/hotpost/service.py`

当前行为：

- subreddit 搜索或评论抓取如果命中 Reddit rate limit
- 会直接打开本地 circuit breaker
- breaker 打开期间：
  - 跳过 subreddit 搜索
  - 跳过评论抓取
- 避免一次 429 后继续连撞 Reddit

日志口径也已补齐：

- 会明确记录 circuit opened
- 会明确记录当前操作是因为 circuit open 被跳过

## 测试

### 定向修复与验证

修掉了第三刀引入的 5 个测试断点：

- 搜索服务 rate-limit 测试补齐预算 mock，避免 Redis fake 误撞限流器内部实现
- evidence collection 测试补齐 `max_comment_posts`

定向验证：

```bash
cd backend && SKIP_DB_RESET=1 pytest tests/services/hotpost/test_hotpost_runtime_config.py tests/services/hotpost/test_hotpost_search_service.py tests/services/hotpost/test_hotpost_search_workflow.py tests/services/hotpost/test_evidence_collection_workflow.py -q
```

结果：

- `18 passed`

### Hotpost 全回归

```bash
cd backend && SKIP_DB_RESET=1 pytest tests/services/hotpost tests/scripts/acceptance/test_run_hotpost_quality_smoke.py -q
```

结果：

- `94 passed`

## 当前判断

第三刀已经把 Hotpost 的一个关键风险面收住了：

- 现在不是“为了提质先猛抓一轮再说”
- 而是先把 Reddit 调用边界写死，再在边界内谈 recall 和 remediation

当前还没有跑新的真实 live smoke，原因很明确：

- 现在更该先确认工程口径稳定
- 再用低成本 live 去看时延和收益
- 避免一边调风控，一边额外消耗 token 和 Reddit 调用预算

## 当前价值

这轮的价值不在“多找了多少帖子”，而在：

- Hotpost 已经开始把“保护 Reddit id / client”当成硬约束
- 首轮 recall 变轻了
- 429 风险开始有熔断，不再裸奔

## 下一步

第四刀建议分两步，不要混着做：

1. 低成本 live 校准
   - 跑极小样本 hotpost smoke
   - 看首轮时延、reasoning 触发率、Reddit 调用成本
2. 继续提结果质量
   - 在新的安全边界内，继续打 `trending / rant / opportunity` 的结果价值
   - 尤其是 `trending/rant` 当前低置信度和样本稀薄问题

## 一句话结论

Hotpost 第三刀已经落地：**Reddit 风控配置、轻首轮 recall、rate-limit circuit breaker 全部进主链，且回归通过。**
现在系统开始真正按“先保账号安全，再谈结果质量”的方式运行。
