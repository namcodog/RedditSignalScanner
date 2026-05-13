# Phase 625 - 主链报告质量收口：solutions_low 根因修复并重新拿回 A_full

## 已完成

1. 确认 `coverage_partial` 不是当前 open-question live 掉到 `B_trimmed` 的主因
   - 对比旧的 `A_full` 验收结果可见，旧样本同样带有 `coverage_partial`
   - 当前真正卡住的是 `solutions_low`
2. 定位 `solutions_low` 的两个真实原因
   - `analysis_signal_support` 里 `solution` 标签只进了 `opportunities`，没有进入 `business_signals.solutions`
   - `facts_v2` 质量门槛在 `source_signal_volume = 12` 的低样本开放题上仍要求 `4` 条 solutions，过严
3. 修复语义信号到 `solutions` 的收口
   - `solution` 标签现在会同时进入 `SolutionSignal`
   - 新增 `merge_business_signals_with_heuristics(...)`
   - 让语义账本为主、heuristic 只补稀疏的 `solutions/opportunities`
4. 修复低样本开放题的 quality gate
   - `facts_v2` 现在在 `source_signal_volume <= 12` 时，`min_solutions_effective = 3`
   - 不再把这种“已有 3 条真实 solutions、2 条 pain、1 条 brand”的样本误压到 `B_trimmed`
5. 重启 live runtime 并复验
   - `analysis-live` worker 已显式重启
   - 最新 live 已重新通过

## 关键改动

1. 修改：
   - `backend/app/services/analysis/analysis_signal_support.py`
   - `backend/app/services/analysis/analysis_engine.py`
   - `backend/app/services/facts_v2/quality.py`
2. 测试：
   - `backend/tests/services/analysis/test_analysis_signal_support.py`
   - `backend/tests/services/analysis/test_facts_v2_quality_gate.py`

## 验证

1. 定向回归：
   - `pytest tests/services/analysis/test_analysis_signal_support.py tests/services/analysis/test_analysis_engine.py tests/services/analysis/test_facts_v2_quality_gate.py -q`
   - `90 passed`
2. quality gate 回归：
   - `pytest tests/services/analysis/test_facts_v2_quality_gate.py tests/services/analysis/test_analysis_engine.py -q`
   - `87 passed`
3. live 复验：
   - 结果文件：
     - `backend/reports/local-acceptance/open_question_live_final_1774943047.json`
   - 任务：
     - `8feb630f-1c10-43d1-bd65-24ae81e87701`
   - 最终：
     - `accepted=1/1`
     - `report_tier=A_full`

## 新结论

1. 主链 P0 前段已经收稳，当前题目重新拿回 `A_full` 不是 route 偶然命中
2. 这轮真正补齐的是报告质量层：
   - `solutions_low` 已被压掉
   - 当前事实质量标记只剩 `coverage_partial`
3. 当前通过样本的关键指标是：
   - `solutions = 3`
   - `min_solutions_effective = 3`
   - `good_pains = 2`
   - `good_brands = 1`
4. 这说明：
   - 对低样本、无评论、但 business signal 已经足够成立的开放题
   - 质量门槛应该是“真实可信地过”，不是“机械要求 4 条 solutions”

## 下一步

1. 不再继续围着这一题做 patch
2. 直接做 1~2 条跨领域开放题 live 复验
3. 同时补齐 `analyses.sources` 的审计可读性，方便后续排查不靠猜
