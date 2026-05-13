# Phase 668 - Pack Supply Fix V2 And Paid Economics Reopen

## 发现了什么

- 之前 `paid-economics` 和 `tools-efficiency` 的 query 虽然收紧了，但实际产出仍被 `listing` 和同社区前两帖抢掉 quota。
- 根因不是 prompt，而是采集顺序：
  - `build_reddit_search_specs()` 先 listing 后 search
  - `collect_scope_candidates()` 顺序消费 spec
  - 同时每个 spec 默认可吞 `2` 条帖子
- 对 quota 只有 `3` 的 pack，这会导致 query 改了也没有真正主导产出。

## 是否需要修复

需要，而且是结构性修复，不是继续叠 prompt。

## 精确修复方法

### 本轮实现

- `paid-economics / tools-efficiency` 改成：
  - `search-first`
  - 不再产 `listing` spec
  - search spec 按 `keyword -> subreddit` 交错生成
- 这两个 pack 的每个 spec 最多只取 `1` 条帖子，不再默认吞 `2` 条
- 同时继续收紧：
  - subreddit 池
  - query 语义

### 验证

```bash
SKIP_DB_RESET=1 pytest \
  backend/tests/services/hotpost/test_reddit_search_spec_builder.py \
  backend/tests/services/hotpost/test_source_scope_catalog.py \
  backend/tests/services/hotpost/test_source_scope_candidate_collector.py \
  backend/tests/services/hotpost/test_signal_pack_eval_builder.py -q
```

- 结果：`13 passed`

### 真实结果

- `paid-economics`
  - `3` 条候选
  - `3` 条 eval case
  - `0` generation failure
  - judge：`1/3 pass`
- `tools-efficiency`
  - `3` 条候选
  - `3` 条 eval case
  - `0` generation failure
  - judge：`0/3 pass`

### `paid-economics` 重开 pack skill 实验

- `human_summary_tight_why_now_v1`：`2/3 pass`
- `paid_econ_decision_v1`：`1/3 pass`
- `paid_econ_decision_strict_v1`：`2/3 pass`

结论：

- `paid-economics` 已重新进入可实验状态
- 但新 pack 变体没有赢过当前基线

## 下一步系统性的计划是什么

1. `paid-economics`
   - 继续保留当前基线
   - 下一轮只打：
     - `quote_not_used_well`
     - `why_now_not_actionable`
2. `tools-efficiency`
   - 暂不做 pack prompt 实验
   - 继续修供给或改 pack 定义
3. 不放松 `signal input quality gate`

## 这次执行的价值是什么

这轮把两条 pack 线真正分开了：

- `paid-economics`：从“供给问题”推进到“可以重开定向 skill 实验”
- `tools-efficiency`：仍然停在“先把输入修到像样”

这一步避免后面继续把两条不同成熟度的线绑在一起乱优化。
