# Signal Failure Taxonomy V1

## 使用方式

- 先读 [signal_eval_review_packet_v1.md](/Users/hujia/Desktop/RedditSignalScanner/reports/evals/signal_eval_review_packet_v1.md)，再往下归类坏样本。
- 一张卡可以挂多个 failure tag。
- 如果遇到新失败类型，先记到“待新增标签”，不要直接改旧标签定义。

## 样本覆盖

- `ai-automation / agent-builder`: `2`
- `ai-automation / tools-efficiency`: `3`
- `ai-automation / unknown`: `6`
- `ai-automation / upstream-winds`: `2`
- `business-growth-ops / funnel-conversion`: `2`
- `business-growth-ops / organic-discovery`: `2`
- `business-growth-ops / paid-economics`: `3`
- `business-growth-ops / unknown`: `5`
- `ecommerce-sellers / category-winds`: `1`
- `ecommerce-sellers / kill-signals`: `1`
- `ecommerce-sellers / selection-signals`: `4`
- `ecommerce-sellers / unknown`: `5`

## V1 Failure Tags

### `reddit_restatement`

- 定义：
  输出主要在复述 Reddit 帖子或评论本身，没有把原话压成面向用户的信号句。
- 何时命中：
  `summary_line` 或 `why_now` 里出现明显的“某社区有人说”“帖子里评论称”，而且读完还是只知道 Reddit 上发生了什么，不知道这对用户的判断有什么推进。
- 不该误判成：
  正常引用证据。短引用可以有，但引用只是证据，不该成为整段主体。
- 代表样本：
  - `signal-eval-card-cand-ai-automation-1se2nxm-validate`
  - `signal-eval-card-cand-business-growth-ops-1s1lelq-validate`
  - `signal-eval-card-cand-ecommerce-sellers-1saj0xa-validate`

### `no_judgment_gain`

- 定义：
  卡片说得不假，但没有帮用户完成任何新的判断，读完只有“知道了”，没有“所以呢”。
- 何时命中：
  输出停在现象概述，没有把症状翻成更高一层的判断线索，也没有完成“值得继续追/可以划走”的前移判断。
- 不该误判成：
  证据保守。保守不等于没价值，真正命中是“保守且空”。
- 代表样本：
  - `signal-eval-card-cand-ai-automation-1sdwgvg-validate`
  - `signal-eval-card-cand-business-growth-ops-1sdu99f-validate`
  - `signal-eval-card-cand-ai-automation-1sem20t-validate`

### `audience_not_who_is_talking`

- 定义：
  `audience` 写成了目标用户、营销 persona 或推测受众，而不是 Reddit 上真实在聊这件事的人。
- 何时命中：
  读起来像“谁该买/谁该看这张卡”，而不是“谁在社区里提出这个问题、谁在抱怨、谁在比较”。
- 不该误判成：
  适度压缩的人群描述。可以提炼，但必须仍然贴着真实说话的人。
- 代表样本：
  - `signal-eval-card-cand-ecommerce-sellers-1se2c91-validate`
  - `signal-eval-card-cand-business-growth-ops-1s1lelq-validate`
  - `signal-eval-card-cand-ai-automation-1sejdgs-validate`

### `why_now_not_actionable`

- 定义：
  `why_now` 还是模板化的时间描述，没有真正回答“为什么现在值得看”。
- 何时命中：
  弱证据样本里仍然套用“近 7 天反复出现”“这 24 小时又冒出来了”，但没有把“意图温度/风险程度/信号读数”说清楚。
- 不该误判成：
  正常的信号强度说明。命中点在于 boilerplate 太重，读完还是没判断。
- 代表样本：
  - `signal-eval-card-cand-business-growth-ops-1s9i53h-validate`
  - `signal-eval-card-cand-ai-automation-1sdwgvg-validate`
  - `signal-eval-card-cand-ai-automation-1sem20t-validate`

### `reporty_title`

- 定义：
  标题像报告摘要、研究条目或论坛记录，不像一条能让人停下来的信号句。
- 何时命中：
  标题堆概念、压缩过度、保留了帖子原句结构，或者读起来像“某社区对某事发表观点”。
- 不该误判成：
  信息密度高。高密度不等于报告腔，关键看有没有具体症状和判断张力。
- 代表样本：
  - `signal-eval-card-cand-business-growth-ops-1s9i53h-validate`
  - `signal-eval-card-cand-ecommerce-sellers-1saj0xa-validate`
  - `signal-eval-card-cand-ai-automation-1se8175-validate`

### `evidence_overclaim`

- 定义：
  证据只有单帖、单社区、少量 quote，但输出把它写成行业趋势、群体共识或宽口径结论。
- 何时命中：
  输入 bundle 明显弱，但标题、summary 或 why_now 已经在说“多数人”“大家都在”“这事正在发生”。
- 不该误判成：
  合理提炼。提炼可以有，但不能超出证据承载力。
- 代表样本：
  - `signal-eval-card-cand-ai-automation-1sdwgvg-validate`
  - `signal-eval-card-cand-business-growth-ops-1s9i53h-validate`
  - `signal-eval-card-cand-ai-automation-1se8175-validate`

### `generic_copy`

- 定义：
  语气安全、完整、顺，但换到别的卡上也基本成立，缺少这条信号特有的刺点。
- 何时命中：
  常见模板句占主体，比如“大家开始把它当成一个新变化”“当前更像验证渠道，不像放量渠道”，但缺少这条 case 独有的判断抓手。
- 不该误判成：
  简洁。简洁可以很锋利，generic 是“怎么写都对，但没记忆点”。
- 代表样本：
  - `signal-eval-card-cand-business-growth-ops-1sbspma-validate`
  - `signal-eval-card-cand-business-growth-ops-1sdu99f-validate`
  - `signal-eval-card-cand-ai-automation-1sdv3lo-validate`

### `quote_not_used_well`

- 定义：
  quote 虽然被用了，但用法很差：太长、太生、带机器人回帖、或者直接把英文整段塞进正文。
- 何时命中：
  `summary_line` 明显被长引用拖累，可读性下降；或者引用本身没有帮助判断，反而像把原帖搬过来。
- 不该误判成：
  简短的原话锚点。短锚点通常是加分项，问题在于“引用成了主体”。
- 代表样本：
  - `signal-eval-card-cand-ai-automation-1se6nq5-validate`
  - `signal-eval-card-cand-ecommerce-sellers-1sela7g-validate`
  - `signal-eval-card-cand-ai-automation-1se8175-validate`

## 当前观察

- 当前最容易高频出现的是：
  - `why_now_not_actionable`
  - `quote_not_used_well`
  - `reddit_restatement`
- 当前最值得继续验证的是：
  - `audience_not_who_is_talking` 是否已从“普遍问题”降到“少量滑坡”
  - `reporty_title` 是否只剩在 candidate_generated 的长尾样本里

## 待新增标签

- `scope_pack_mismatch`
  - 某些卡本身就像 topic-pack 选错，不完全是写法问题
- `tone_too_beliefy`
  - 输出像立场宣言或情绪宣泄，不像信号判断
