# Signal Input Quality Gate V1

## 结论

第一轮 canary 已经证明：

- `human_summary_tight_why_now_v1` 在全量评估上有提升
- 但在 hardest cases 上不够用
- 第二轮 `clean_quotes_v2` 在 hardest cases 上依然 `0/6` 救回

这说明主问题已经不是“summary 还不够人话”，而是：

**有一批输入证据本身就不配生成 signal 卡。**

## canary 结果

### v1 canary

- variant: `human_summary_tight_why_now_v1`
- sample_count: `6`
- improved: `1`

### v2 canary

- variant: `human_summary_tight_why_now_clean_quotes_v2`
- sample_count: `6`
- improved: `0`

## 判断

这两个结果合起来说明：

1. `why_now` 收紧能拉高整体平均值
2. 但 hardest cases 的根因不是文案，而是输入证据质量太差
3. 对这类样本继续调 prompt，只会产出更顺的垃圾，不会产出更值钱的卡

## V1 质量闸门

当前先只挡最脏的一类：

- 单帖
- 单社区
- 没有可用原话
- 原话主要是：
  - bot / automod
  - 公版提醒
  - 寒暄废话

## 离线审计

运行 `signal_input_quality_audit_v1` 后：

- `sample_count = 36`
- `blocked_count = 9`
- `blocked_fail_count = 9`
- `blocked_pass_count = 0`

也就是：

**这道最小闸门能提前挡掉 9 条 judge 已经判死的坏样本，而且当前没有误伤 pass 样本。**

## 当前决策

- 继续做 prompt 微调，不是当前第一优先
- 下一步最值的是：
  - 把 `signal input quality gate` 接进生产生成链的 signal 路径
  - 先减少“明知救不回来的垃圾卡”

## 下一步

1. 在 `signal` 生成前加输入质量闸门
2. 只拦最脏样本，不做模糊打分
3. 接入后再重跑：
   - `signal eval set`
   - `signal judge`
4. 再看剩下的失败项里，prompt 优化还有多大空间
