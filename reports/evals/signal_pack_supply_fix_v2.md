# Signal Pack Supply Fix V2

## 目标

继续修：

- `business-growth-ops / paid-economics`
- `ai-automation / tools-efficiency`

这轮不再只改社区和 query，而是直接改产出顺序，让搜索词真正主导候选。

## 这轮改动

### 1. 两个 pack 改成 `search-first`

- 不再给这两个 pack 产 `listing` spec
- 只保留 `search:relevance:week`
- 搜索 spec 改成按：
  - `keyword -> subreddit`
  的顺序交错生成

目的不是“多抓点”，而是先把不同社区轮一遍，避免 quota 被前几个 listing 或同社区帖子吃满。

### 2. 每个 spec 只允许贡献 1 条 candidate

- `paid-economics`
- `tools-efficiency`

这两个 pack 现在每个 spec 最多只取 `1` 条帖子，不再像之前那样一个 spec 直接吞掉 `2` 条。

目的很明确：

- 提高社区多样性
- 降低单社区前两帖直接占满 quota 的概率

### 3. 继续收紧 pack 配置

#### `paid-economics`

- 社区改成：
  - `PPC`
  - `FacebookAds`
  - `googleads`
  - `Google_Ads`
  - `adops`
- query 改成更像投手重做判断：
  - `blended cac`
  - `channel profitability`
  - `incrementality test`
  - `offline conversion import`
  - `paid search profitability`
  - `over reliant on paid ads`
  - `platform roas vs blended roas`
  - `attribution gap`
  - `search partners wasting budget`
  - `scale and lower roas`
  - `cutting paid spend what happened`
  - `moved budget off meta`
  - `what is still profitable in paid social`
  - `when to lower roas target`
  - `budget reallocation after cpc spike`

#### `tools-efficiency`

- 社区改成：
  - `automation`
  - `ClaudeAI`
  - `OpenAI`
  - `artificial`
- query 改成更像真实 workflow 摩擦：
  - `ai workflow that stuck`
  - `automation workflow that stuck`
  - `one ai tool i kept`
  - `ai tool stack`
  - `prompt workflow`
  - `tool switching fatigue`
  - `context loss between tools`
  - `too many ai subscriptions`
  - `copy paste context between tools`
  - `stopped paying for ai tools`
  - `replaced three tools with one workflow`
  - `which ai tool did you cancel`
  - `what workflow actually sticks`
  - `dropped copilot`
  - `stopped using ai tool`

## 验证

### 定向测试

```bash
SKIP_DB_RESET=1 pytest \
  backend/tests/services/hotpost/test_reddit_search_spec_builder.py \
  backend/tests/services/hotpost/test_source_scope_catalog.py \
  backend/tests/services/hotpost/test_source_scope_candidate_collector.py \
  backend/tests/services/hotpost/test_signal_pack_eval_builder.py -q
```

- 结果：`13 passed`

### 真实 collect 后的结果

#### `paid-economics`

- collect 后拿到 `3` 条候选
- 都带 `matched_keywords`
- 社区已分散到：
  - `PPC`
  - `FacebookAds`
  - `googleads`
- pack eval：
  - `case_count = 3`
  - `generation_failure_count = 0`

#### `tools-efficiency`

- collect 后拿到 `3` 条候选
- 都带 `matched_keywords`
- 社区已分散到：
  - `ClaudeAI`
  - `artificial`
- pack eval：
  - `case_count = 3`
  - `generation_failure_count = 0`

## 结论

这轮已经不是“稍微好一点”，而是阶段边界变了：

- 两个 pack 都已经从“进不了盘子”
  变成
- “都能稳定过 gate 并生成 eval case”

但两条线的状态已经分开：

- `paid-economics`
  - 已经足够重开 pack skill 实验
- `tools-efficiency`
  - 现在只是刚刚进盘子
  - judge 仍然是 `0/3 pass`
  - 还不适合直接下结论说“供给修好了”
