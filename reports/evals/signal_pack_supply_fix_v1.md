# Signal Pack Supply Fix V1

## 目标

修复两个最差 pack 的输入供给，让它们至少能首次产出通过 `signal input quality gate` 的 candidate。

- `business-growth-ops / paid-economics`
- `ai-automation / tools-efficiency`

## 改动

### 1. 缩社区

#### `paid-economics`

从：

- `marketing`
- `PPC`
- `FacebookAds`
- `googleads`
- `shopify`

改成：

- `PPC`
- `FacebookAds`
- `googleads`
- `adops`
- `AmazonAds`

#### `tools-efficiency`

从：

- `ChatGPT`
- `ClaudeAI`
- `automation`
- `productivity`

改成：

- `automation`
- `ClaudeAI`
- `OpenAI`
- `Productivitycafe`

### 2. 收 query

#### `paid-economics`

不再用：

- `roi`
- `roas`
- `ads`

改成更贴近投放经济判断的 query：

- `blended cac`
- `roas target`
- `paid search profitability`
- `cpc spike`
- `cpm spike`
- `budget cut paid social`
- `incrementality`

#### `tools-efficiency`

不再用：

- `ai tool`
- `workflow`
- `ai efficiency`

改成更贴近 workflow 摩擦的 query：

- `ai workflow`
- `automation workflow`
- `tool switching fatigue`
- `too many ai tools`
- `context loss between tools`
- `what workflow actually sticks`
- `stopped using ai tool`

### 3. 降 listing 噪音

这两个 pack 不再跑：

- `listing:hot:day`
- `listing:new:day`
- `listing:rising:day`
- `listing:top:day`

只保留：

- `listing:top:week`

其他 pack 不动。

## 验证

### 代码验证

```bash
SKIP_DB_RESET=1 pytest backend/tests/services/hotpost/test_reddit_search_spec_builder.py backend/tests/services/hotpost/test_source_scope_catalog.py backend/tests/services/hotpost/test_source_scope_candidate_collector.py backend/tests/services/hotpost/test_signal_pack_eval_builder.py -q
```

- 结果：`12 passed`

### 真实 collect 结果

#### `business-growth-ops`

- collect 后 pack 分布：
  - `paid-economics = 3`
  - `funnel-conversion = 3`
  - `organic-discovery = 2`

#### `ai-automation`

- collect 后 pack 分布：
  - `tools-efficiency = 3`
  - `agent-builder = 3`
  - `upstream-winds = 2`

## 产出结果

### `paid-economics`

- 通过 `signal input quality gate`：`2`
- 被挡：`1`

judge 结果：

- `0 pass / 2 fail`

高频失败：

- `reddit_restatement`
- `why_now_not_actionable`
- 少量 `reporty_title`

### `tools-efficiency`

- 通过 `signal input quality gate`：`1`
- 被挡：`2`

judge 结果：

- `0 pass / 1 fail`

高频失败：

- `reddit_restatement`
- `no_judgment_gain`

## 结论

这轮供给修复已经起效，但只起了一半。

### 已经改善的部分

- 这两个 pack 不再是 `3/3` 全部在 gate 前被挡掉
- `paid-economics` 已经能稳定产出 `2` 条可写样本
- `tools-efficiency` 也第一次产出 `1` 条可写样本

### 还没改善的部分

- 这些样本虽然“配写”，但还没“写好”
- 当前 judge 结果还是 `0 pass`

## 当前阶段判断

- `paid-economics`：已经接近可以进入 pack 定向 skill 实验
- `tools-efficiency`：供给仍然偏弱，先不急着进 skill 实验
