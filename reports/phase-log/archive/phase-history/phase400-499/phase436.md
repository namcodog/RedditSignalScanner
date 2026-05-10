# Phase 436 - Narrative 实链路验收与覆盖修复

## 本轮目标

完成 `Phase 38` 的最后缺口：在真实 live 链路中确认完整报告走 narrative 主链，而不是被短模板覆盖。

## 发现了什么

1. `make test-e2e-live-report` 能稳定出 `A_full`，但 `/api/report/{task_id}` 返回的 `report_markdown` 仍是短模板（约 300 字）。
2. 真实根因有两个：
   - 进程环境存在占位 key：`OPENAI_API_KEY=your_open...`，导致 LLM 请求 401；
   - `render_bundle` 的优先级错误：`controlled_result.markdown` 覆盖了 narrative `base_report_markdown`。
3. narrative workflow 本身是通的：同机直调 `run_narrative_report_workflow` 可生成 3000+ 字长版报告。

## 是否需要修复

需要，且是 P0。

不修会造成“元数据显示 llm_used=true，但完整报告仍是短模板”的交付错觉，直接违背同源合同。

## 精确修复方法

### 1) 配置层修复占位 key 覆盖

- 更新 `backend/app/core/config.py`
  - 新增 `_is_placeholder_secret` / `_resolve_llm_api_key`
  - `get_settings().openai_api_key` 改为优先选择非占位的真实 key（`OPENAI_API_KEY` 或 `OPENROUTER_API_KEY`）
- 新增测试 `backend/tests/core/test_llm_api_key_resolution.py`

### 2) 渲染层修复 markdown 覆盖优先级

- 更新 `backend/app/services/report/render_bundle.py`
  - `report_markdown` 优先使用 `base_report_markdown`（narrative/structured）
  - 只有 `base` 缺失时才用 `controlled_result.markdown` 兜底
- 更新测试 `backend/tests/services/report/test_render_bundle.py`

## 验证结果

### 配置与渲染回归

- `pytest tests/core/test_llm_api_key_resolution.py tests/core/test_dotenv_precedence.py tests/services/llm/test_openai_client.py -q` -> `5 passed`
- `pytest tests/services/report/test_render_bundle.py -q` -> `4 passed`
- `pytest tests/services/report/test_narrative_report_workflow.py tests/services/report/test_report_assembly_workflow.py tests/services/report/test_report_assembly_deps_factory.py tests/services/report/test_report_payload_builder.py tests/services/report/test_report_export_service.py tests/api/test_report_export_markdown_and_fallback.py tests/core/test_llm_api_key_resolution.py -q` -> `18 passed`

### 前端合同与构建

- `npm test -- src/tests/contract/report-api.contract.test.ts src/tests/contract/report-schema.contract.test.ts src/pages/__tests__/ReportPage.test.tsx src/pages/__tests__/ReportFlow.integration.test.tsx` -> `12 passed`
- `npm run build` -> passed
- `make test-e2e` -> `21 passed`

### Live 真链路验收

- `make test-e2e-live-report` 最新任务：
  - `task_id = 9073cbd3-67a4-40dd-9963-4e6c39c84a51`
  - `report_tier = A_full`
  - `metadata.llm_used = true`
  - `report_markdown_len = 3067`（已是 narrative 长版，不再是短模板）
  - `canonical_report_json` 同时存在，保持同源合同

## 当前结果

`Phase 38` 已完成：完整报告的 live 主链现在是
`canonical_report_json -> narrative markdown -> 前端完整报告/导出`，并通过正式 E2E 与 live 验收。

## 下一步系统计划

1. 用 `topic_profile` 6 卡各跑一次长版 narrative 抽检，确认展示轨与开放轨都稳定输出长版。
2. 对照 `reports/t1价值的报告.md` 做结构强度对齐（只调 prompt，不再改主链架构）。

## 这次执行的价值

把“看起来有 LLM”变成“真正交付长版报告”的可验收状态，消除了报告短模板覆盖长报告的核心漂移点。
