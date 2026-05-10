# phase737

## 本轮目标

按 `phase736` 的审计结论继续落实现层，不停在“知道问题在哪”，而是把 `hot / breakdown / 调度 / collect` 的关键错位真正修进主链。

## 已完成

1. `hot` 不再被 `search/listing` 提前一刀切
   - 去掉了 `card_lane_policy.py` 里“非 listing 且 pack 未开 search-hot 就直接回 signal”的前置拦截
   - 现在先看帖子本身热不热、讨论形状成不成立，再判是不是 `hot`

2. `hot` 不再复用 `signal_input_quality` 门禁
   - `review_queue_policy.py`
   - `card_content_generator.py`
   - 两处都改成：只有 `lane=signal` 才走 signal gate，`lane=hot` 直接按热点标准往下走

3. 最近 `20` 张 mix 真接进调度器
   - `card_selection_policy.py` 现在不再看全历史
   - 正式按文档口径跑：
     - lane `10 / 6 / 4`
     - scope `7 / 7 / 6`

4. `breakdown` 恢复供给入口
   - `organic-discovery` 重新允许进入 breakdown suggestion

5. collect 稳定性做了两层修复
   - 单个 spec 的 Reddit 失败/429，不再拖死整个 scope
   - 同一篇帖子被多个 spec 命中时，评论抓取按 `post_id` 去重，不再重复打评论接口

6. collect 吞吐做了第一轮收口
   - 默认评论抓取从 `8` 条降到 `5` 条
   - 单帖评论总超时从 `8s` 降到 `4s`
   - API 并发从 `4` 调到 `6`
   - 新增每个 scope 的 spec 预算：
     - search `120`
     - listing `36`
   - 实际 spec 数量变成：
     - `ai-automation: 268 -> 156`
     - `business-growth-ops: 388 -> 156`
     - `ecommerce-sellers: 334 -> 144`

## 验证结果

- 定向回归：
  - `test_source_scope_candidate_collector.py`
  - `test_card_lane_policy.py`
  - `test_review_queue_policy.py`
  - `test_card_content_generator.py`
  - `test_card_selection_policy.py`
  - `test_breakdown_candidate_clusterer.py`
- 结果：
  - `60 passed`

## 当前结论

这轮已经把“会炸”和“会误挡”的问题收住了：

- `hot` 的判断层不再被检索方式劫持
- `hot` 不再被 `signal` 规则二次误伤
- 调度器终于按最近 `20` 张的固定 mix 在工作
- collect 遇到 Reddit 429，不会整轮报废

但 collect 吞吐还没有完全稳态：

- spec 预算已经收了一轮，但真实 `daily_collect` 依然会被大量评论超时和 Reddit 限流拖慢
- 也就是说，当前从“会炸”进到了“能跑但还不够快”

## 下一步

1. 继续收 `collect` 吞吐
   - spec 优先级
   - 评论抓取策略
   - Reddit 限流下的节流/跳过策略

2. 停止继续补 `signal`，优先补 `hot + breakdown`

3. 重新跑：
   - `hot-ops`
   - `breakdown-ops`
   看最近 `20` 张能不能从 `17 / 3 / 0` 往目标 mix 拉回去

## 本轮价值

这轮不是再修一点 prompt，也不是再补几张卡。

真正完成的是：

- 把 `phase736` 审计里最关键的错位修进了代码
- 把 collect 从“一个 subreddit 429 就整轮挂掉”修成“部分失败仍能继续产出”
- 把“稳定供卡”推进到一个更接近工程闭环的状态
