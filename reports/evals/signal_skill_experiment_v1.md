# Signal Skill Experiment V1

## 目标

在不动生产链的前提下，对 `signal skill` 做第一轮半自动优化实验。

- 固定评估集：`reports/evals/signal_eval_set_v1.jsonl`
- 固定评委：`reports/evals/signal_judge_prompt_v1.md`
- 只比较离线变体，不直接改线上 prompt

## 变体

1. `baseline_v1`
   - 当前 signal prompt / 当前 why_now 重写
2. `human_summary_v1`
   - summary 改成人话，不强制嵌原话翻译
   - why_now 不变
3. `human_summary_tight_why_now_v1`
   - summary 改成人话，不强制嵌原话翻译
   - why_now 改成更硬的信号读数句

## 结果

| variant | pass | fail | pass_rate | decision |
| --- | ---: | ---: | ---: | --- |
| `baseline_v1` | 5 | 31 | 13.89% | discard |
| `human_summary_v1` | 4 | 32 | 11.11% | discard |
| `human_summary_tight_why_now_v1` | 10 | 26 | 27.78% | keep |

## 关键判断

### 1. 单改 summary 没用，甚至更差

`human_summary_v1` 的 `reddit_restatement` 从 `28` 降到 `24`，但 `why_now_not_actionable` 从 `13` 升到 `18`，整体 pass rate 反而下降。

说明：

- 只把 summary 写得更像人话，不足以把卡从“论坛转述”推进成“判断卡”
- 如果 `why_now` 还是轻飘模板句，整卡依然站不住

### 2. 真正有效的是“summary 人话化 + why_now 收紧”组合

`human_summary_tight_why_now_v1` 的结果明显更好：

- pass rate：`13.89% -> 27.78%`
- `why_now_not_actionable`：`13 -> 6`
- `reddit_restatement`：`28 -> 21`

说明：

- 当前最值钱的改动不是“少一点英文原话”
- 而是要让 `why_now` 真正回答“这件事现在是不是已经从随口一提变成需要继续盯的信号”

### 3. 主问题仍然没被完全打掉

即使保留变体，前两大失败标签仍然是：

- `reddit_restatement`
- `no_judgment_gain`

这说明 V1 只是把 signal skill 从“很差”拉到“可继续优化”，还没有到可直接 promote 的程度。

## 决策

- `baseline_v1`: discard
- `human_summary_v1`: discard
- `human_summary_tight_why_now_v1`: keep，进入 canary 前准备

## 下一步

1. 只把 `human_summary_tight_why_now_v1` 做成 canary
2. 不直接全量替换生产 prompt
3. 第二轮实验继续专打：
   - `reddit_restatement`
   - `no_judgment_gain`
4. 优先看最差 pack：
   - `business-growth-ops / paid-economics`
   - `ai-automation / tools-efficiency`
