# Phase 661 - Signal Input Quality Gate V1

## 结果

在第一轮 `signal skill` keep 变体之后，又做了两件关键事：

1. 对 keep 变体跑了 hardest-cases canary
2. 基于 canary 结论，补了 `signal input quality gate` 的离线验证

新增产物：

- `reports/evals/signal_skill_canary_v1.md`
- `reports/evals/signal_input_quality_gate_v1.md`
- `reports/evals/signal_input_quality_audit_v1.json`
- `backend/app/services/hotpost/signal_input_quality.py`
- `backend/scripts/evals/run_signal_input_quality_audit_v1.py`
- `backend/tests/services/hotpost/test_signal_input_quality.py`

## canary 结论

### 第一轮 canary

- variant: `human_summary_tight_why_now_v1`
- sample_count: `6`
- improved: `1`

### 第二轮 canary

- variant: `human_summary_tight_why_now_clean_quotes_v2`
- sample_count: `6`
- improved: `0`

这说明：

- keep 变体能拉高整体平均分
- 但 hardest cases 靠 prompt 继续打磨，收益已经很低

## 当前判断

这轮最大的判断转折是：

**最差的那批 signal case，不是“写得不够好”，而是“输入证据本身就不该生成卡”。**

主问题已经从：

- `signal skill optimization`

转成：

- `signal input quality gate`

## 质量闸门审计结果

离线审计结果：

- `sample_count = 36`
- `blocked_count = 9`
- `blocked_fail_count = 9`
- `blocked_pass_count = 0`

说明这道最小闸门：

- 能提前挡掉 `9` 条 judge 已判死的垃圾样本
- 当前没有误伤 pass 样本

## 当前决策

下一步不该继续盲调 prompt。

应直接做：

1. 把 `signal input quality gate` 接入 signal 生产生成链
2. 只挡：
   - 单帖弱证据
   - bot / 公版 / 寒暄废话 quote
3. 接入后再重跑：
   - `signal eval set`
   - `signal judge`
4. 再判断 prompt 优化剩余空间
