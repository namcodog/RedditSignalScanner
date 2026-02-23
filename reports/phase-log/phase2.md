# Phase 2 集成记录（GTM行动计划器）

时间：2025-11-13 进度点：2.4-2.7（GTMPlanner 核心）

- 发现/根因：
  - 现有 GTMActionPlanner 仅包含 3 条基础动作，未覆盖两周节奏与审核强度降级，难以直接用于 Phase 2 验收。
- 定位：
  - 目标文件：`backend/app/services/reporting/gtm_planner.py`，保持模板回退、可扩展、无外部依赖。
- 精确修复：
  - 两周极简节奏：新增 W1（潜伏/价值/讨论）、W2（复盘/软植入/反馈）共 ≥6 条动作；
  - 合规降级：`moderation_score>=0.9` 自动替换“发布帖子”为“总结/留言”等更保守方式，并给出 `compliance_warning`；
  - 不改变对外数据结构（`GTMPlan`/`GTMAction`），保持回退友好；
- 测试：
  - `backend/tests/services/report/test_gtm_planner.py`：
    - `test_gtm_planner_fallback_generates_actions`（基础生成）
    - `test_gtm_planner_generates_two_weeks_min_actions_count`（两周≥6条）
    - `test_gtm_planner_compliance_warning_and_copy_tone`（合规降级，禁用“发布帖子”用语）
  - `backend/tests/services/test_report_service_phase2_integration.py`：
    - `test_phase2_integration_generates_gtm_plans`（集成校验：返回结构包含 gtm_plans 且动作数≥6）
- 结果：
  - 单测通过（4 passed）；实现最小可用 GTM 计划输出，集成落点为 `ReportMetadata.market_enhancements.gtm_plans`，满足 Phase 2 的节奏与合规约束；未修改其他模块以避免过度开发。
- 下一步（Phase 2 范畴内可选）：
  - 细化社区差异化模版（按 persona.traits 做轻微措辞替换）；
  - 提供可插拔的频次/天数参数，便于 A/B；
