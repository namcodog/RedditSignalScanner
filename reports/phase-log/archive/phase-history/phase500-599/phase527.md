# Phase 527 - Hotpost opportunity 证据集中度收口

## 背景

- Phase 526 已把 `rant` 拉回到 fast 可用态
- 下一步目标是继续收“结果够硬”
- 这轮先看 `opportunity`，避免继续在 prompt 上盲修

## 本轮执行

### 1. 最小 live 诊断

- 查询：`chargeback management tool`
- 结果：
  - `query_id = 3274fc94-9deb-4f28-96e5-199067d4c115`
  - `status = completed`
  - `final_report_layer = reasoning`
  - `total_workflow_ms = 61804`
- 诊断结论：
  - 输出里混进了明显脏证据：
    - `scarystories`
    - `stayawake`
    - `RedditStoryTime`
  - 直接看 `top_posts` 可确认根因不是 LLM 先坏了，而是上游 `why_relevant="命中关键词"` 把无关帖子顶进了 evidence pack

### 2. 轻量修复

- `backend/app/services/hotpost/report_workflow.py`
  - 新增 `_post_direct_hit_count()`
  - `opportunity` 的帖子排序改成：
    - 优先看 `title / body_preview / subreddit / signals` 的直接命中
    - 如果 `why_relevant` 只是“命中关键词”且正文完全不命中，不再给它加权
  - 当 `opportunity` 已经存在直接命中的帖子时，只把这些帖子送给模型
  - 评论层也补了同样的轻过滤：
    - `opportunity` 默认最短评论长度提升到 `24`
    - 如果已经存在直接命中的评论，只把这些评论送给模型

### 3. 测试

- `backend/tests/services/hotpost/test_hotpost_report_workflow.py`
  - 把“query 相关证据优先”测试扩到 `opportunity`
  - 固定一个典型坏样本：
    - 标题无关
    - `why_relevant` 伪装成“命中关键词”
  - 断言：
    - 无关帖子不会再进入 `posts_data`
    - 无关评论不会再进入 `comments_data`

- 回归：
  - `pytest backend/tests/services/hotpost/test_hotpost_report_workflow.py backend/tests/services/hotpost/test_hotpost_search_workflow.py -q`
  - `14 passed`

## live 复验

### 第一轮修复后

- 查询：`chargeback automation tool`
- 结果：
  - `query_id = 29f9c3e5-feed-40c9-8092-ace5b388a9f6`
  - `status = completed`
  - `final_report_layer = reasoning`
  - `total_workflow_ms = 66593`
- 改善：
  - `scarystories / stayawake` 已经消失
  - 前 3 个 unmet needs 已收成：
    - `自动化拒付/退款风险防控`
    - `AI驱动的模式识别与预警`
    - `账户交易与售后保障`
- 剩余脏点：
  - `top_quotes` 里还有一条 `Interested` 这类零价值评论

### 最后一刀

- 我已在输入层补了“有直接命中的评论就不再送零命中评论”
- 这一刀通过了定向测试
- 为保护 Reddit API，这一小改没有再额外追加第三次 live

## 结论

### 1. 发现了什么？

- `opportunity` 当前最核心的问题不是 prompt，而是 evidence pack 被“假关键词命中”污染
- 一旦把这个污染挡掉，结果会明显更像机会洞察，而不是随机话题混合

### 2. 是否需要继续修复？

- 需要，但已经不是大修
- 当前剩余问题只集中在：
  - `top_quotes` 的代表性
  - `market_opportunity` 的字段饱满度

### 3. 下一步系统性计划

1. 继续轻量收输出层：
   - 代表性原话
   - 下一步动作建议
2. 不再继续扩大 Hotpost 架构
3. 如果下一轮收益开始变低，就收口，不把这个模块做重

### 4. 这次执行的价值

- `opportunity` 这条线已经从“证据包本身歪”推进到“主要还剩结果打磨”
- 这一步符合当前约束：
  - 轻量
  - 不做重工程化
  - 不多打 Reddit API
