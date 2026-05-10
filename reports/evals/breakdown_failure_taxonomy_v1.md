# Breakdown Failure Taxonomy V1

## 使用方式

- 先读 review packet，再往下归类坏样本。
- 一张拆解卡可以挂多个 failure tag。
- 如果遇到新失败类型，先记到“待新增标签”，不要直接改旧标签定义。

## 样本覆盖

- `ai-automation / agent-builder`: `1`
- `ai-automation / unknown`: `10`
- `business-growth-ops / unknown`: `5`
- `ecommerce-sellers / selection-signals`: `1`
- `ecommerce-sellers / unknown`: `1`

## V1 Failure Tags

### `weak_thesis`

- 定义：thesis 看起来像判断，但只是把几条现象重新拼成一句更抽象的话，没有真正往更深一层推进。
- 何时命中：读完 thesis 仍然只是在换种方式复述 signal，没有形成更稳定的解释框架。
- 不该误判成：正常保守。保守可以成立，但空话式抽象不算成立的 thesis。
- 代表样本：
  - `breakdown-eval-suggestion-suggestion-ai-automation-94bfe667d1`
  - `breakdown-eval-suggestion-suggestion-ecommerce-sellers-258155f585`

### `quote_pack_not_supporting_claim`

- 定义：quote_pack 看起来很多，但并没有真正共同支撑 thesis，或者只是热闹堆砌。
- 何时命中：引用之间只是同主题共现，没有形成共同指向；或者 thesis 明显比 quote 说得更重。
- 不该误判成：引用少。少而准可以 pass，问题在于证据关系没撑住结论。
- 代表样本：
  - `breakdown-eval-suggestion-suggestion-ai-automation-94bfe667d1`

### `no_judgment_gain`

- 定义：整张拆解卡没有真正给出新判断，只是把多条 signal 汇总得更长。
- 何时命中：读完只有“这些帖子都在说类似的事”，没有“原来真正卡在这里”。
- 不该误判成：简洁。短不等于没判断，空才算。
- 代表样本：
  - `breakdown-eval-published-clue-roadmap-lightweight-alignment`

### `reddit_restatement`

- 定义：正文主要还是在复述 Reddit 讨论，没有把 grouped evidence 压成用户可直接拿走的判断。
- 何时命中：summary_line/why_now 的主体像论坛摘要，读完仍然停留在 Reddit 上发生了什么。
- 不该误判成：短引用锚点。引用可以有，但不能变成正文主体。
- 代表样本：

### `why_now_not_actionable`

- 定义：why_now 只是在说最近大家都在聊，没有完成拆解层应有的信号读数。
- 何时命中：why_now 停在时间句或讨论增多，没有说明为什么这组 grouped discussion 现在不能忽视。
- 不该误判成：正常的时效说明。问题在于只有时间，没有判断。
- 代表样本：

### `audience_not_who_is_talking`

- 定义：audience 写成目标 persona，而不是真实在聊这件事的人。
- 何时命中：读起来像营销受众画像，而不是 Reddit 里提出问题、抱怨、比较的人群。
- 不该误判成：适度抽象的人群描述。只要仍然贴着真实发言者，就不算。
- 代表样本：

### `stitched_not_coherent`

- 定义：这组 signal 被硬拼到一起，看起来相关，但其实不是同一个决策问题。
- 何时命中：候选看似同类，真正张力却不同；或 thesis 靠拼接而不是靠共指成立。
- 不该误判成：多角度但同问题。多个角度共同指向一个判断时可以成立。
- 代表样本：
  - `breakdown-eval-suggestion-suggestion-ai-automation-94bfe667d1`
  - `breakdown-eval-suggestion-suggestion-ecommerce-sellers-258155f585`
  - `breakdown-eval-published-clue-roadmap-lightweight-alignment`
  - `breakdown-eval-published-clue-sales-followup-slip`

### `reporty_title`

- 定义：标题像分析报告、研究摘要或论坛目录，而不是一条有判断张力的拆解句。
- 何时命中：标题堆概念、像条目索引，或者把 thesis 写得像学术摘要。
- 不该误判成：信息密度高。高密度不等于报告腔。
- 代表样本：
  - `breakdown-eval-published-clue-sales-followup-slip`

## 待新增标签

- （人工阅读后补）
