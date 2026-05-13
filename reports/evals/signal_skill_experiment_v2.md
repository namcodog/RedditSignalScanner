# Signal Skill Experiment V2

## 目标

在保留 `signal input quality gate` 的前提下，继续做第二轮半自动 `signal skill` 实验。

- 固定评估集：`reports/evals/signal_eval_set_v1.jsonl`
- 当前基线：`human_summary_tight_why_now_v1`
- 固定评委：`reports/evals/signal_judge_prompt_v1.md`
- 只比较离线变体，不直接改线上 prompt

## 变体

1. `human_summary_tight_why_now_v1`
   - 上一轮 keep 版本
   - 作为第二轮基线
2. `judgment_forward_summary_v2`
   - 更强地要求 `summary_line` 先给“这对人意味着什么”
   - 禁止按论坛发言顺序转述
3. `judgment_forward_summary_strict_v2`
   - 在 `judgment_forward_summary_v2` 基础上更进一步
   - `summary_line` 不允许直接引语，证据尽量退回 `preview_quote`

## 结果

| variant | pass | fail | pass_rate | decision |
| --- | ---: | ---: | ---: | --- |
| `human_summary_tight_why_now_v1` | 13 | 18 | 41.94% | baseline |
| `judgment_forward_summary_v2` | 7 | 24 | 22.58% | discard |
| `judgment_forward_summary_strict_v2` | 10 | 21 | 32.26% | discard |

## 关键判断

### 1. 全局“判断前置”改写没有赢

第二轮两个新变体都没有超过当前基线。

- `judgment_forward_summary_v2` 直接退步最明显
- `judgment_forward_summary_strict_v2` 比普通版好一点，但依然输给基线

说明：

- 不是所有 signal 都适合一上来写成“判断句”
- 一刀切把 `summary_line` 强行改成“判断前置”，会让一部分卡变成空话或假判断

### 2. 主问题没有变，只是暴露得更清楚

基线的高频失败仍然是：

- `reddit_restatement`
- `why_now_not_actionable`
- `no_judgment_gain`

第二轮新变体没有把这三件事一起打下来，反而让一部分卡多了：

- `quote_not_used_well`
- `audience_not_who_is_talking`

这说明：

- 当前不是缺一个更猛的“总 prompt”
- 而是缺更细的、按主题包分开的 signal 写法

### 3. 当前最稳的仍然是“人话 summary + 收紧 why_now”

第二轮实验之后，当前最优 baseline 仍然是：

- `human_summary_tight_why_now_v1`

这意味着当前应继续保留：

- summary 不硬塞原话翻译
- `why_now` 用更硬的信号读数句

但不能直接往前再叠一层“全局判断句模板”。

## 决策

- `human_summary_tight_why_now_v1`: 保留为当前最优基线
- `judgment_forward_summary_v2`: discard
- `judgment_forward_summary_strict_v2`: discard

## 下一步

1. 不做一刀切的全局 prompt 强推
2. 继续保留 `signal input quality gate`
3. 下一轮改成更细的定向实验：
   - 只打最差 pack
   - 只解决该 pack 里最常见的坏法
4. 优先顺序：
   - `business-growth-ops / paid-economics`
   - `ai-automation / tools-efficiency`
