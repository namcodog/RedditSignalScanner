# Phase 670 - Tools Efficiency Canary Closed

## 发现了什么

- `tools-efficiency` 第三轮供给修复后，已经能产出更像“工具切换/上下文摩擦”的样本。
- 但这不代表它已经适合进入正式 pack prompt 实验。
- 为了验证这一点，这轮只做了一个很小的 canary：
  - 基线：`human_summary_tight_why_now_v1`
  - 定向变体：
    - `tools_efficiency_focus_v1`
    - `tools_efficiency_focus_strict_v1`

## 是否需要修复

不需要再继续堆 `tools-efficiency` 的 prompt 变体了。

这轮已经足够说明：

- 新变体没有赢过基线
- 继续推只是在小样本上制造更强的写法噪音

## 精确修复方法

### 本轮实现

- 新增两个 `tools-efficiency` 定向变体
- 新增 `pack_tools_efficiency` 的 `why_now` 模式
- 新增 canary runner

### 测试

```bash
SKIP_DB_RESET=1 pytest \
  backend/tests/services/hotpost/test_signal_skill_experiment.py \
  backend/tests/services/hotpost/test_reddit_search_spec_builder.py \
  backend/tests/services/hotpost/test_source_scope_catalog.py -q
```

- 结果：`15 passed`

### canary 结果

- `human_summary_tight_why_now_v1`：`1/2 pass`
- `tools_efficiency_focus_v1`：`0/2 pass`
- `tools_efficiency_focus_strict_v1`：`0/2 pass`

失败主要集中在：

- `reporty_title`
- `reddit_restatement`
- `no_judgment_gain`
- `why_now_not_actionable`

## 下一步系统性的计划是什么

1. `tools-efficiency`
   - 保留当前更窄的供给配置
   - 保留全局基线
   - 暂停正式 pack prompt 实验
2. 主线回到更成熟的地方：
   - `paid-economics` 继续只打：
     - `quote_not_used_well`
     - `why_now_not_actionable`
3. `tools-efficiency` 以后如果再继续，只能在：
   - 样本更多
   - 或问题再切得更细
   的前提下做下一轮 canary

## 这次执行的价值是什么

这轮把 `tools-efficiency` 的边界说真话了：

- 供给方向已经修对
- 但写法还没成熟到值得继续正式实验

这比硬把它推进实验更有价值，因为它避免我们在一条还没成熟的线里继续烧时间。
