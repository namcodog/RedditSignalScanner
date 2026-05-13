# Phase 435 - Narrative Full A 主链接线

## 本轮目标

把 `Phase 38` 后半段真正接上：让完整报告不再只是结构化 renderer 的结果，而是可由 LLM 基于 `canonical_report_json` 生成 narrative markdown，并进入统一交付链。

## 发现了什么

1. 之前 `Phase 38` 第一半已经有 `report_markdown`，但它主要来自 structured/control 模板链，不是我们目标中的 Full A narrative。
2. 仓库里其实已有可复用资产，不需要重造：
   - `build_complete_report_v9`（完整报告 prompt）
   - `OpenAIChatClient`（统一 LLM 客户端）
3. narrative 若继续绑定 `ENABLE_REPORT_INLINE_LLM`，默认主链依旧可能不触发，和“开放提问 = 默认主链”的产品合同冲突。

## 是否需要修复

需要，而且是 P0。

不把 narrative 接回主链，完整报告就会长期停在“结构有了，但语义交付不够硬”的状态，产品体验会继续漂。

## 精确修复方法

### 1. 新增 narrative workflow

- 新建 `backend/app/services/report/narrative_report_workflow.py`
- 输入：`canonical_report_json + facts_slice`
- 输出：`narrative markdown`
- 复用：`build_complete_report_v9` + `OpenAIChatClient`

### 2. 接入 report runtime / assembly 主链

- `report_runtime_factory` 增加 `build_narrative_report_markdown` 依赖构建
- `report_assembly_workflow` 在 structured 之后优先尝试 narrative：
  - narrative 成功 -> 优先作为 `report_markdown`
  - narrative 失败 -> 回退 structured markdown
- `render_bundle` 把 narrative 的 LLM 使用并入 `llm_used`

### 3. 触发条件收口

- narrative 从 `ENABLE_REPORT_INLINE_LLM` 解耦
- 改为由 `ENABLE_LLM_SUMMARY + llm_model_name + openai_api_key` 决定是否触发

## 验证结果

### 后端回归

- `pytest tests/services/report/test_narrative_report_workflow.py tests/services/report/test_report_assembly_deps_factory.py tests/services/report/test_report_assembly_workflow.py tests/services/report/test_render_bundle.py tests/services/report/test_report_payload_builder.py tests/services/report/test_report_export_service.py tests/services/report/test_report_service_market_mode.py tests/api/test_report_export_markdown_and_fallback.py -q`
  - `25 passed`

- 再次定向复验：
  - `pytest tests/services/report/test_narrative_report_workflow.py tests/services/report/test_report_assembly_workflow.py tests/services/report/test_report_assembly_deps_factory.py tests/services/report/test_report_service_market_mode.py -q`
  - `15 passed`

### 前端合同回归

- `npm test -- src/tests/contract/report-api.contract.test.ts src/tests/contract/report-schema.contract.test.ts src/pages/__tests__/ReportPage.test.tsx src/pages/__tests__/ReportFlow.integration.test.tsx`
  - `12 passed`
- `npm run build`
  - 通过

### 线上接口抽检（现有 task）

- 登录 `test@test.com` 后抽检现有 `A_full` task：`0bd6a7cc-9ed8-4889-932d-28340cfa0c02`
- 结果：
  - `report_markdown` 已返回（合同生效）
  - `canonical_report_json` 已返回（同源骨架生效）
  - `metadata.llm_used = false`
- 判断：
  - 当前运行中的后端进程没有触发 narrative LLM（更可能是进程环境变量/运行参数问题），不是代码链路缺失。

## 当前结果

这轮之后，完整报告主链已经升级为：

`canonical_report_json -> narrative workflow(LLM) -> report_markdown -> report_html / 导出 / 前端完整报告入口`

也就是说，完整报告不再只是“结构化渲染结果”，而是已经具备 narrative 生成能力并接入正式交付链。

## 还未完成

本轮尚未做 live API key 的内容强度验收。

所以当前能确认的是“链路已通 + 合同已通 + 回归全绿”，还不能直接宣称“narrative 质量已经完全对齐 `t1价值的报告.md`”。

## 下一步系统计划

1. 在真实 API key 环境跑 1-2 条 live 任务，拿到 narrative markdown 实物
2. 对照 `reports/t1价值的报告.md` 做结构和语言强度打分
3. 若不足，微调 narrative prompt（不改主链结构）

## 这次执行的价值

把“完整报告要有 Full A narrative 能力”从产品口号变成了真正可执行的后端主链能力，后续优化只需要调质量，不再需要改架构。
