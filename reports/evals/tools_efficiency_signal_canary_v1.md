# Tools Efficiency Signal Canary V1

## 结论

`tools-efficiency` 在更窄供给盘子上跑了一个最小 canary，结果是：

- 基线 `human_summary_tight_why_now_v1`：`1/2 pass`
- `tools_efficiency_focus_v1`：`0/2 pass`
- `tools_efficiency_focus_strict_v1`：`0/2 pass`

这轮结论很硬：

**当前不该继续做 `tools-efficiency` 的正式 pack prompt 实验。**

原因不是“没样本”，而是：

- 样本已经比之前干净
- 但一旦强行把 summary 往“工具切换/订阅取舍判断”上推
- 很容易把个别能过的样本写成：
  - 标题更报告腔
  - audience 更像目标人群画像
  - why_now 还是模板句

## 本轮变体

- `human_summary_tight_why_now_v1`
- `tools_efficiency_focus_v1`
- `tools_efficiency_focus_strict_v1`

## 结果

### keep / discard

```json
[
  {"variant_id": "human_summary_tight_why_now_v1", "pass_rate": 0.5, "pass_count": 1, "fail_count": 1, "decision": "baseline"},
  {"variant_id": "tools_efficiency_focus_v1", "pass_rate": 0.0, "pass_count": 0, "fail_count": 2, "decision": "discard"},
  {"variant_id": "tools_efficiency_focus_strict_v1", "pass_rate": 0.0, "pass_count": 0, "fail_count": 2, "decision": "discard"}
]
```

### 失败形态

- `tools_efficiency_focus_v1`
  - `reporty_title`
  - `audience_not_who_is_talking`
  - `why_now_not_actionable`
  - `reddit_restatement`
  - `no_judgment_gain`

- `tools_efficiency_focus_strict_v1`
  - `reporty_title`
  - `why_now_not_actionable`
  - `reddit_restatement`
  - `no_judgment_gain`

## 判断

这轮 canary 说明两件事：

1. `tools-efficiency` 的供给方向已经比之前对得多
   至少不再主要是抽象 AI 观点和 builder brag

2. 但这条线现在还不适合上正式 pack 写法实验
   因为新变体没有比全局基线更稳，反而把一部分样本写坏了

## 下一步

1. 保留当前更窄的供给配置
2. 保留全局基线 `human_summary_tight_why_now_v1`
3. 暂停 `tools-efficiency` 的正式 pack prompt 实验
4. 如果后面还要继续，只能等：
   - 更多可写样本
   - 或更清晰的子问题再做下一轮 canary
