# Phase 629 - AI_Workflow 第三领域复验通过 + 前端 build 绿灯

## 1. 发现了什么？

- `EDC` 补完 Reddit 证据链接合同后，主链并没有再暴露新的 route / retrieval 问题。
- `AI_Workflow` 新鲜 live 复验通过，说明当前 open-question 主链不再是“单题偶然过”。
- `analysis_audit` 不只是测试里存在，已经在新鲜 live 任务里真实落库。
- 前端旧 build 阻塞 `frontend/src/lib/report-contract.ts:35` 已不再阻塞构建。

## 2. 是否需要修复？

- 需要。
- 这轮真正要修的是：
  - 把 `structured_report_fallback` 的 Reddit 证据补链从 EDC 特例收成通用规则
  - 用新鲜 live 再证明 `analysis_audit` 的审计摘要在真实任务中可用
  - 确认前端 build 绿灯，不再把旧阻塞当成本轮开放问题

## 3. 精确修复方法

### 3.1 通用 Reddit 证据补链

修改文件：

- `backend/app/services/report/structured_report_fallback.py`
- `backend/tests/services/report/test_structured_report_fallback.py`

修复内容：

- 新增从 `facts_slice.evidence_ledger` 回补 clickable Reddit links 的通用逻辑
- 规则改成：
  - canonical report 自身先保留已有证据链
  - 如果 canonical report 最终唯一 clickable Reddit links `< 2`
  - 且 `facts_slice.evidence_ledger` 里存在来自允许社区的真实 Reddit 证据
  - 就从 ledger 里补齐到 `>= 2`
- 这次没有回退到 synthetic，也没有引入 AI_Workflow 特判

新增回归：

- `test_enforce_structured_report_contract_backfills_two_unique_clickable_reddit_links_from_allowed_ledger`

### 3.2 AI_Workflow 第三领域复验

重启 live runtime：

```bash
cd backend && ../.venv/bin/python scripts/acceptance/manage_live_runtime.py restart
```

运行 fresh live：

```bash
cd backend && ../.venv/bin/python scripts/acceptance/run_open_question_live_acceptance.py \
  --suite final \
  --product-description '我想研究团队在 ChatGPT Claude Notion AI agent 和自动化 workflow 里的真实卡点，判断有没有 AI workflow 工具机会。' \
  --required-tier A_full \
  --min-reddit-links 2 \
  --max-analysis-attempts 1 \
  --warmup-wait-timeout-seconds 420
```

### 3.3 analysis_audit live 确认

- 新鲜任务：`2e7e242a-ddfa-47d6-a494-34591a9efbf8`
- 关键确认：
  - `analysis_audit.final_verdict.reason_code = passed`
  - `route_decision_summary.warzone = AI_Workflow`
  - `drift_guard_summary.action = relax_route_pre_retrieval`
  - `facts_quality_summary.passed = true`

### 3.4 前端 build 复核

```bash
cd frontend && npm run build
```

- 结果：通过
- 当前仅剩 chunk-size warning，不再是构建阻塞

## 4. 验证

### 定向测试

```bash
cd backend && ../.venv/bin/python -m pytest \
  tests/services/report/test_structured_report_fallback.py \
  tests/services/analysis/test_analysis_finalization_support.py \
  tests/scripts/acceptance/test_run_open_question_live_acceptance.py -q
```

结果：

- `51 passed`

### fresh live

- `AI_Workflow`
  - 输出文件：`backend/reports/local-acceptance/open_question_live_final_1775143332.json`
  - 结果：`accepted = 1/1`, `report_tier = A_full`

### 前端 build

- `cd frontend && npm run build`
  - 结果：通过

## 5. 下一步系统性的计划是什么？

1. 不再回头修 open-question 前段
2. 补 `hotpost` 上线边界矩阵
3. 固化 live 验收预检和 runtime 运维口径
4. 更新根目录收尾文档，把剩余问题压缩成长期优化项

## 6. 这次执行的价值是什么？达到了什么目的？

- `EDC` 的证据合同修法已经证明不是题材特判，而是通用 canonical report 补链规则。
- `AI_Workflow` 第三领域复验通过，当前主链已经初步具备跨领域成立性。
- `analysis_audit` 已经从“测试里可用”推进到“真实 live 可用”。
- 前端 build 绿灯，旧构建阻塞不再占着收尾主清单。
