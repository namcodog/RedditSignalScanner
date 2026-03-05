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

---

时间：2026-03-05 进度点：Phase 2A（`run_analysis()` 分支注释注入）

1) 发现了什么？
- `backend/app/services/analysis/analysis_engine.py` 的 `run_analysis()` 存在多个关键分支点，但缺少统一编号注释，不利于后续排障和联调对齐。

2) 是否需要修复？
- 需要。当前任务目标是补齐标准化分支注释，提升可读性与定位效率。

3) 精确修复方法
- 仅修改注释，不改任何逻辑代码。
- 新增/替换共 12 处注释：
  - `🔀 分支` 注释共 10 条（分支 0-9）；
  - `⚙️ 参数` 注释共 2 条（DB 社区上限、每社区帖子上限）。
- 校验结果：
  - `python3 -c "import ast; ast.parse(open('backend/app/services/analysis/analysis_engine.py').read()); print('✅ AST OK')"` 输出 `✅ AST OK`
  - `grep -c '🔀 分支' backend/app/services/analysis/analysis_engine.py` 输出 `10`
  - `grep -c '⚙️ 参数' backend/app/services/analysis/analysis_engine.py` 输出 `2`

4) 下一步系统性的计划是什么？
- 基于分支编号，在 Phase 2A 后续任务中补一份“分支编号 → 监控指标/告警位点”映射文档，便于线上问题快速定位。

5) 这次执行的价值是什么？达到了什么目的？
- 达成“可读不改行为”的目标：代码行为 0 变更，分支语义显式化，后续排查和评审沟通成本更低。
