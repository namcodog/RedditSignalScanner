# Phase 462 - Report 侧 Evidence Ledger 接线

## 背景

在完成：

- `Worker / State Orchestration`
- `Evidence Selection`
- `Evidence Ledger` 第一段落地

之后，下一步不能停在 fallback 认账本。

如果：

- `report_enrichment_workflow`
- `opportunity_report`
- `report_payload_builder`
- `controlled_generator`

这些正式 report 入口还各自拼证据，那么“统一证据读取面”就还没有真正落到交付层。

## 本轮改动

### 1. 让 report enrichment 显式透传账本

- 文件：`backend/app/services/report/report_enrichment_workflow.py`

当前 action items 的生成流程已经开始显式读取 `facts_slice.evidence_ledger`，再传给机会报告构建层。

### 2. 让机会报告优先读账本

- 文件：`backend/app/services/report/opportunity_report.py`

当前机会证据链会优先从 `evidence_ledger` 命中；只有账本没有命中时，才继续回退到旧来源。

### 3. 让 payload builder 回填 action item 证据

- 文件：`backend/app/services/report/report_payload_builder.py`

现在 action items 如果原始 `evidence_chain` 为空，会从 `facts_slice.evidence_ledger` 回填对应证据链。

### 4. 让 controlled report 正文也优先认账本

- 文件：`backend/app/services/report/controlled_generator.py`

当前正文上下文里的：

- L4 pain evidence
- action evidence

都开始优先从 `evidence_ledger` 读取，而不是再去各自拼一份旧来源。

### 5. 补齐定向测试

- `backend/tests/services/report/test_report_enrichment_workflow.py`
- `backend/tests/services/report/test_report_payload_builder.py`
- `backend/tests/services/report/test_controlled_generator.py`

另外这轮也顺手修正了一条测试合同问题：

- `insights.opportunities` 这条链本来就应保持对象协议
- 新测试误塞了 `dict`
- 这会把测试失败伪装成主链失败

现在测试已经收回正确对象合同。

## 验证

通过：

- `cd backend && pytest tests/services/report/test_report_enrichment_workflow.py -q`
- `cd backend && pytest tests/services/report/test_report_payload_builder.py -q`
- `cd backend && pytest tests/services/report/test_controlled_generator.py -q`
- `cd backend && python -m py_compile app/services/report/opportunity_report.py app/services/report/report_enrichment_workflow.py app/services/report/report_payload_builder.py app/services/report/controlled_generator.py`

## 结论

这轮之后，`Evidence Ledger` 已经不再只是 fallback 在认：

- report enrichment 认账本
- 机会卡认账本
- payload builder 认账本
- controlled report 正文认账本

这说明统一证据读取面已经开始真正进入 report 交付层。

## 下一步

- 继续审视剩余 report 入口，把“多处各自拼证据”的旧逻辑继续降级成兼容回退层。
- 后续重心会转向：
  - `Insight Synthesis`
  - `Canonical Report Assembly`
  让统一证据面继续往上游和最终交付同时收口。
