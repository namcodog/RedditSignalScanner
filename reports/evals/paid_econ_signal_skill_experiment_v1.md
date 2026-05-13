# Paid Economics Signal Skill Experiment V1

## 目标

验证 `business-growth-ops / paid-economics` 在完成供给修复后，是否已经适合进入 pack 定向 `signal skill` 优化。

## 实验盘子

- 来源：当前真实 collect 后的 `paid-economics` candidates
- 通过 `signal input quality gate` 的样本：`3`

## 变体

1. `human_summary_tight_why_now_v1`
   - 当前全局最优基线
2. `paid_econ_decision_v1`
   - 强调“这件事让投手重新判断什么”
   - 不要写成事故复盘或论坛转述
3. `paid_econ_decision_strict_v1`
   - 在上面基础上进一步禁止引语和工单标题感

## 结果

| variant | pass | fail | pass_rate | decision |
| --- | ---: | ---: | ---: | --- |
| `human_summary_tight_why_now_v1` | 2 | 1 | 66.67% | baseline |
| `paid_econ_decision_v1` | 1 | 2 | 33.33% | discard |
| `paid_econ_decision_strict_v1` | 2 | 1 | 66.67% | discard |

## 关键判断

### 1. `paid-economics` 已经真正重回实验盘子

供给修复已经起效：

- 这条线现在有 `3` 条能过 gate 的可写样本
- judge 里也第一次出现了 `pass`

这说明它已经不再停留在“只能修供给”的阶段。

### 2. 但 pack prompt 还没有赢过当前基线

- `paid_econ_decision_v1` 明显更差
- `paid_econ_decision_strict_v1` 只追平了基线，没有赢

当前还剩的主问题集中在：

- `quote_not_used_well`
- `why_now_not_actionable`
- 少量 `reddit_restatement`

### 3. 样本盘子已经比上轮健康，但还不够厚

这次样本已经不再都是 `r/PPC` 单社区 incident：

- 社区已经分散到：
  - `PPC`
  - `FacebookAds`
  - `googleads`
- query 也开始命中真正的投放判断词

但盘子还是小，当前不适合继续盲目加变体。

## 结论

当前阶段：

- `paid-economics` 已经从“供给全灭”
  推进到
- “可以重开 pack 定向 skill 实验”

但当前 keep/discard 结果也很明确：

- 继续保留 `human_summary_tight_why_now_v1` 作为基线
- 不保留 `paid_econ_decision_v1`
- `paid_econ_decision_strict_v1` 只打平，不升级成 keep

## 下一步

1. 继续保留当前全局基线：
   - `human_summary_tight_why_now_v1`
2. 如果要开第二轮 `paid-economics` 变体，只能继续打：
   - `quote_not_used_well`
   - `why_now_not_actionable`
3. 不再回头把它当成“纯供给问题”
4. 供给侧继续保守维护，但主线已经可以从“修输入”切到“定向打写法”
