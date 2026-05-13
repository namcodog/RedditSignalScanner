# Phase 671 - Card Skill Workflow V1 Closed

## 发现了什么

- `paid-economics` 这条线在第二轮供给修复后，已经跑出了一个明确优于全局基线的 pack 定向 signal 写法。
- 最终 canary 结果是：
  - `human_summary_tight_why_now_v1 = 2/3 pass`
  - `paid_econ_signal_readout_v2 = 3/3 pass`
- 这意味着：
  - `paid-economics` 已经可以正式 promote 到生产生成链
  - `card skill optimization workflow v1` 也已经具备收口条件

## 是否需要修复

需要，但不是继续大改全局 prompt。

当前不需要再继续扩 V1。

正确动作已经变成：

- 保留 `paid_econ_signal_readout_v2` 作为 `paid-economics` 默认生产写法
- 不影响其他 pack
- `tools-efficiency` 继续保持暂停正式 prompt 实验
- 把 V1 作为一整套方法闭环正式收口

## 精确修复方法

### 本轮实现

- 将 `paid_econ_signal_readout_v2` 收成 `paid-economics` 的默认生产写法
- 生产生成链不直接依赖 draft schema 新增字段，而是从 `candidate_id -> cards payload` 反查 `topic_pack_id`
- 仅当 `topic_pack_id = paid-economics` 时：
  - 注入更贴投手判断的 prompt instruction
  - 清洗低价值 quote
  - 覆盖 `why_now / detail.why_test_now`

### 验证

```bash
SKIP_DB_RESET=1 pytest \
  backend/tests/services/hotpost/test_card_content_generator.py \
  backend/tests/services/hotpost/test_signal_skill_experiment.py \
  backend/tests/services/hotpost/test_signal_pack_eval_builder.py -q
```

- 结果：`19 passed`

### canary 结果

- `human_summary_tight_why_now_v1`：`2/3 pass`
- `paid_econ_signal_readout_v2`：`3/3 pass`

## 下一步系统性的计划是什么

1. V1 到这里正式结束
2. 进入日常运行态：
   - 保留 `signal judge`
   - 保留 `signal input quality gate`
   - 保留全局基线
   - 保留 `paid_econ_signal_readout_v2`
3. `tools-efficiency`
   - 保留更窄供给配置
   - 暂停正式 prompt 实验
4. 后续如果再开新优化，应该以 V2 立题：
   - 新 pack
   - breakdown skill
   - 或更自动化的 autoresearch loop

## 这次执行的价值是什么

这一步真正达成的不是“又加了一个实验变体”，而是：

- 第一次把某个 pack 的 keep 结果正式推进到了生产生成链
- 证明这套 `eval -> judge -> canary -> promote` 的优化闭环已经跑通
- 也让 V1 从“研究方法”变成了“真实工程能力”
- 同时守住了边界：
  - 只 promote 成熟 pack
  - 不把未成熟的 `tools-efficiency` 一起硬推上线
