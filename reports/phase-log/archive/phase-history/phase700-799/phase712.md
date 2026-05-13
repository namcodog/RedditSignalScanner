# phase712 - hot lane eval calibration v1

## 这次完成了什么

- 回写了 `hot_lane_eval_labels_v1.jsonl` 的 9 条人工标注
- 新增热点边界校准结论：
  - [reports/evals/hot_lane_eval_calibration_v1.md](../evals/hot_lane_eval_calibration_v1.md)
- 收紧 `hot lane` 判定规则：
  - 低信息围观不进 `hot`
  - 意识形态对线不进 `hot`
  - 纯实操分享不进 `hot`
- 更新回归测试并通过

## 当前校准结果

- `hot = 4`
- `signal = 1`
- `reject = 4`

核心边界：

> 热点不等于热帖。要进 `爆贴热点`，评论区必须有清晰聚焦议题，并且出现实质性的两面论据或群体报数/群体应对。

## 直接影响

- 现有 `hot lane` 不再只看 listing 热度
- 已发布的那张 AI 牛图热点卡，按新标准应视为 `reject`
- 后续 `signal-ops` 在 review `lane=hot` 时，优先看：
  - 有没有争议焦点
  - 有没有实质性对立或群体报数
  - 还是只是围观、感叹、站队

## 验证

- `SKIP_DB_RESET=1 pytest backend/tests/services/hotpost/test_card_lane_policy.py backend/tests/api/test_hotpost_clues.py -q`
- 结果：`13 passed`

## 下一步

- 用新规则继续跑一轮真实运营
- 重点观察：
  - `爆贴热点` 会不会继续被低信息热帖污染
  - 是否能稳定产出第 2、3 张真正像样的热点卡
