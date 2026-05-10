# Selection-Signals Canary V1

## 结论

`selection-signals` 已经跑出 keep 结果，可以作为第二个成熟 pack 进入生产链。

## 结果

- baseline：`human_summary_tight_why_now_v1`
  - `0 / 5 pass`
- canary：`selection_signal_readout_v1`
  - `4 / 5 pass`

keep/discard：

- `human_summary_tight_why_now_v1`：baseline
- `selection_signal_readout_v1`：keep

## 说明

这轮 canary 用的是冻结的 `signal_eval_set_v1` 里的 `selection-signals` 样本，不吃当前生产链结果，基线是干净的。

这次真正打掉的主问题是：

- `reddit_restatement`
- `why_now_not_actionable`

## 剩余尾巴

还剩 `1` 条 harder case 没完全过：

- `signal-eval-generated-card-cand-ecommerce-sellers-1se2c91-validate`
- failure tags：
  - `reddit_restatement`
  - `no_judgment_gain`

这条现在不影响 pack promote，但说明后面如果再开 `selection-signals` 的下一轮小 canary，优先该打“可更换电池/维修权”这一类更抽象的耐用品判断。
