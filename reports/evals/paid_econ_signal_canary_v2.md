# Paid Economics Signal Canary V2

## 目标

验证 `business-growth-ops / paid-economics` 在完成第二轮供给修复后，是否已经出现一个值得正式收进生产生成链的 pack 定向 signal 写法。

## canary 盘子

- pack：`business-growth-ops / paid-economics`
- 样本数：`3`
- 当前比较对象：
  - `human_summary_tight_why_now_v1`
  - `paid_econ_signal_readout_v2`

## 结果

| variant | pass | fail | pass_rate | decision |
| --- | ---: | ---: | ---: | --- |
| `human_summary_tight_why_now_v1` | 2 | 1 | 66.67% | baseline |
| `paid_econ_signal_readout_v2` | 3 | 0 | 100.00% | keep |

## 关键判断

### 1. 这条线已经不再停留在“只能修供给”

`paid-economics` 当前不只是能过 gate，而且已经出现了一个比全局基线更好的 pack 定向写法。

这和前一轮“全部变体都没赢”的状态不同，说明第二轮供给修复后，样本盘子终于开始支撑更贴脸的 signal 写法。

### 2. 有效改动不是“写得更重”，而是“把信号读数写成投手会重新判断什么”

`paid_econ_signal_readout_v2` 真正有效的地方有两点：

- `summary_line` 不再把帖子写成事故回放，而是直接落到：
  - 这件事会让投手重新判断什么
- `why_now` 不再写模板趋势句，而是写成：
  - 这已经开始影响目标设置、回传路径、预算判断

### 3. 这条线在 V1 范围内已经收口

这轮 rerun 后：

- `paid_econ_signal_readout_v2 = 3/3 pass`
- 当前 canary 上已经没有残余失败标签

这不代表以后所有 `paid-economics` 样本都永远不会再出问题，
但对 V1 来说，已经足够把这条线从“继续实验”推进到“收口”。

## 决策

1. 保留 `paid_econ_signal_readout_v2`
2. 将它收成 `paid-economics` 的默认生产生成写法
3. 只影响 `topic_pack_id = paid-economics`
4. 不改全局 signal 基线
5. `tools-efficiency` 仍然维持暂停正式 prompt 实验的判断
6. `card skill optimization workflow v1` 可以按收尾状态结束

## 验证

```bash
SKIP_DB_RESET=1 pytest \
  backend/tests/services/hotpost/test_card_content_generator.py \
  backend/tests/services/hotpost/test_signal_skill_experiment.py \
  backend/tests/services/hotpost/test_signal_pack_eval_builder.py -q
```

- 结果：`19 passed`

## 结论

当前阶段已经可以把 `paid-economics` 从“继续试验候选”推进到“pack 定向默认写法上线”，并把 `workflow v1` 正式收口。

这一步的意义不是再多一个 prompt 变体，而是第一次证明：

**在更干净的输入盘子上，某个 pack 可以有自己比全局基线更好的默认 signal 写法。**
