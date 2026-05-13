# Signal Judge Spec V1

## 目标

这份 judge spec 只服务于 `📡 信号`，不用来评 `🔍 拆解`。

judge 的任务不是挑文风喜好，而是判断：

**给定这包证据，这张卡有没有完成“判断前移”，还是只是在转述 Reddit。**

## 输入

每条 case 都必须同时看：

- `input_bundle`
- `baseline_output`

禁止只看成品卡下判断。

## 输出

judge 先只产出两层结果：

- 字段级 `pass/fail`
  - `title`
  - `summary_line`
  - `audience`
  - `why_now`
- 整卡级 `overall_pass/fail`

另外必须返回：

- `failure_tags`
- `review_notes`

## 字段级标准

### 1. `title`

`pass` 条件：

- 能一眼看懂这张卡在说什么症状
- 不像报告标题，不像论坛帖子索引
- 没有超出证据去写成宏大结论

`fail` 常见原因：

- `reporty_title`
- `evidence_overclaim`
- 过长、过硬、概念堆叠

### 2. `summary_line`

`pass` 条件：

- 把输入证据压成 1-2 句用户能读懂的话
- 有判断推进，不只是把帖子内容换个说法
- quote 只作为锚点，不拖累可读性

`fail` 常见原因：

- `reddit_restatement`
- `no_judgment_gain`
- `quote_not_used_well`
- `generic_copy`

### 3. `audience`

`pass` 条件：

- 写的是 Reddit 上真实在聊这件事的人
- 贴着场景和角色，不是营销 persona

`fail` 常见原因：

- `audience_not_who_is_talking`
- 过度推断“谁该买/谁该看”

### 4. `why_now`

`pass` 条件：

- 说清这条信号为什么现在值得看
- 能让用户判断“继续追 or 划走”
- 不靠模板化时间句硬撑

`fail` 常见原因：

- `why_now_not_actionable`
- `evidence_overclaim`
- `generic_copy`

## 整卡级标准

`overall_pass` 只有在下面同时成立时才通过：

1. 这张卡不是单纯复述 Reddit
2. 这张卡至少帮用户完成一次轻量判断前移
3. 输出没有明显超出证据强度

下面任一命中，整卡直接 `fail`：

- `reddit_restatement`
- `evidence_overclaim`
- `no_judgment_gain`

## Failure Tags 使用约束

- 一张卡可以挂多个 tag
- 但不要把所有问题都挂满
- 只挂最主要的 `1-3` 个失败原因

优先级建议：

1. 先挂结构性失败
   - `evidence_overclaim`
   - `no_judgment_gain`
   - `reddit_restatement`
2. 再挂字段性失败
   - `audience_not_who_is_talking`
   - `why_now_not_actionable`
   - `reporty_title`
   - `quote_not_used_well`
   - `generic_copy`

## Calibration Seed

judge calibration 第一轮建议先挑这几类代表样本：

- `reddit_restatement`
  - `signal-eval-card-cand-business-growth-ops-1s1lelq-validate`
- `quote_not_used_well`
  - `signal-eval-card-cand-ai-automation-1se6nq5-validate`
- `why_now_not_actionable`
  - `signal-eval-card-cand-ai-automation-1sem20t-validate`
- `audience_not_who_is_talking`
  - `signal-eval-card-cand-ecommerce-sellers-1se2c91-validate`
- `evidence_overclaim`
  - `signal-eval-card-cand-ai-automation-1sdwgvg-validate`

## 暂不做的事

- 不上 1-5 分量表
- 不让 judge 直接改写卡片
- 不把 judge 接到发布链

judge 在当前阶段只做一件事：

**稳定判断好卡和坏卡。**
