# Phase 628 - EDC 证据链接合同收口 + analyses.sources 审计摘要首版

## 1. 发现了什么？

- `EDC` 失败的真根因不在 retrieval，也不在 facts quality。
- 真实 Reddit 证据已经进了 `analysis.sources.facts_slice.evidence_ledger.opportunities`，但落到 `report_structured.opportunities[*].evidence_chain` 时被过滤空了。
- 直接原因是 `structured_report_fallback` 对 opportunity evidence 先做了过严的 `product_warzone` 过滤，像 `r/ManyBaggers` 这种明明在目标社区盘里的真实证据也会被裁掉。
- 同时，当前 `analyses.sources` 虽然有 `analysis_diagnostics` 和 `facts_v2_quality`，但还要人工翻很多字段，排障成本高。

## 2. 是否需要修复？

需要。

- `EDC` 要补的不是“假证据展示”，而是 canonical report 层对真实 Reddit 证据的保留规则。
- 审计层也需要补一个固定摘要，不然下一轮 live 还是要靠人手动拼结论。

## 3. 精确修复方法

### 3.1 EDC 证据链接合同

修改文件：

- `backend/app/services/report/structured_report_fallback.py`
- `backend/tests/services/report/test_structured_report_fallback.py`

修复内容：

- 新增 `_select_opportunity_evidence_chain(...)`
- 规则改成：
  - 先按原逻辑做 `product_warzone + allowed_names` 双过滤
  - 如果这一步把 opportunity evidence 全裁空，但原始证据仍来自 `allowed_names` 里的真实社区，并且 URL 是可点击 Reddit 链接
  - 就回退保留这些真实 allowed-community 证据
- 这次没有回退到 synthetic，也没有伪造链接

新增回归：

- `test_build_structured_report_fallback_keeps_allowed_opportunity_reddit_link_when_warzone_filter_is_too_strict`

### 3.2 analyses.sources 审计摘要

修改文件：

- `backend/app/services/analysis/analysis_finalization_support.py`
- `backend/tests/services/analysis/test_analysis_finalization_support.py`

修复内容：

- 在最终 render 后新增 `sources["analysis_audit"]`
- 固定输出 5 个区块：
  - `query_plan_summary`
  - `route_decision_summary`
  - `drift_guard_summary`
  - `facts_quality_summary`
  - `final_verdict`
- `final_verdict.reason_code` 当前支持：
  - `passed`
  - `route_fail`
  - `drift_intervened`
  - `facts_quality_fail`
  - `evidence_link_density_fail`
  - `runtime_fail`

## 4. 验证

### 定向测试

```bash
cd backend && ../.venv/bin/python -m pytest \
  tests/services/report/test_structured_report_fallback.py \
  tests/scripts/acceptance/test_run_open_question_live_acceptance.py -q
```

结果：

- `46 passed`

```bash
cd backend && ../.venv/bin/python -m pytest \
  tests/services/analysis/test_analysis_finalization_support.py \
  tests/services/report/test_structured_report_fallback.py \
  tests/scripts/acceptance/test_run_open_question_live_acceptance.py -q
```

结果：

- `50 passed`

### live 验收

重启 live runtime 后复验：

- `EDC`
  - 输出文件：`backend/reports/local-acceptance/open_question_live_final_1775141296.json`
  - 结果：`accepted = 1/1`, `report_tier = A_full`

额外核实：

- 这轮 `Family` 和电商 live 并不稳定，不应继续沿用之前“已稳定 A_full”的口径。
- `Family` 旧结论需要收正：之前那条通过记录本质是 `auto_rerun -> C_scouting`，不是稳定 `A_full`。

## 5. 下一步系统性的计划是什么？

1. 用新的 `analysis_audit` 直接复盘 `Family` 和电商为何掉到 `C_scouting`
2. 再决定是继续收 `AI_Workflow` 第三领域复验，还是先把当前 live 稳定性收平
3. 后面再继续做 `hotpost` 上线边界和 runtime / frontend 封版

## 6. 这次执行的价值是什么？达到了什么目的？

- `EDC` 这条已经从“分析成立但展示合同不过”变成真正通过。
- `analyses.sources` 终于开始有固定审计摘要，后面排障不需要再手工翻一堆散字段。
- 同时也把一个错误口径纠正了：当前跨领域并没有稳定到“Family / 电商都 A_full”，还需要继续用真实 live 结果说话。
