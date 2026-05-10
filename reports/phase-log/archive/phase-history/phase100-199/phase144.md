# Phase 144 - LLM 报告口径统一同步（PRD/API/SOP）

日期：2026-01-22

## 目标
将“LLM 必经、insights 为主线、facts_v2 为证据与门禁”的口径统一同步到 PRD/SOP/API 文档，作为唯一标准。

## 范围
- PRD：`docs/PRD/PRD-01-数据模型.md`、`docs/PRD/PRD-02-API设计.md`、`docs/PRD/PRD-03-分析引擎.md`、`docs/PRD/PRD-05-前端交互.md`、`docs/PRD/PRD-08-端到端测试规范.md`、`docs/PRD/PRD-SYSTEM.md`、`docs/PRD/PRD-INDEX.md`
- API：`docs/API-REFERENCE.md`
- 架构与流程：`docs/系统架构完整讲解.md`、`docs/系统架构快速参考.md`、`docs/ALGORITHM-FLOW.md`
- SOP：`docs/sop/2025-12-13-facts-v2-落地SOP.md`

## 统一口径（新的唯一标准）
- **LLM 必经**：报告正文必须由 LLM 输出。
- **insights = 算法结论**：痛点/竞品/机会/行动项/实体榜单为 LLM 的主线输入。
- **facts_v2 = 证据 + 门禁 + 审计**：生成 `facts_slice` 作为 LLM 证据输入；门禁为 C/X 时仅输出解释与下一步动作。

## 文档变更摘要
- PRD-03/PRD-SYSTEM 明确 LLM 报告生成口径与输入来源。
- PRD-01/PRD-02/PRD-05/PRD-08 与 API-REFERENCE 同步“LLM 必经”与 C/X 输出规则。
- 架构与流程文档更新为“LLM 报告生成（insights + facts_slice）”。
- facts_v2 SOP 增加“报告生成口径（LLM 必经）”说明。

## 测试
- 未执行（仅文档更新）。

## 备注/待办
- 代码实现与测试用例需按新口径复核并补齐（如 LLM 强制输出与 C/X 解释页规则）。
