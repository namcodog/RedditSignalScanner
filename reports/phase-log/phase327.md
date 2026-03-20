# Phase 327 - 第三轮：报告模块继续拆内联结构化 LLM 生成链

## 1. 发现了什么？

这次第三轮继续打的是 `ReportService` 里还残留的一块重逻辑：

- 内联结构化 LLM 报告生成

之前这条链虽然已经不像前面那么大，但主服务里还同时背着：

- 读 `facts_slice`
- 看 `inline_llm_enabled`
- 看 `enable_llm_summary`
- 看 `llm_model_name`
- 看 `openai_api_key`
- 拼 prompt
- 起 `OpenAIChatClient`
- 调 LLM
- 解析 JSON

大白话说：

- `ReportService` 还在一边编排，一边亲手跑一条完整的 LLM 子 workflow。

## 2. 是否需要修复？

需要，而且这一步已经修完。

这次没有改数据库表结构，没有新 migration。  
改的是报告模块里“内联结构化 LLM 生成”这条子链的 workflow 边界、主服务职责和测试门禁。

## 3. 精确修复方法？

这次做了三件事：

- 新增独立 workflow：
  - `backend/app/services/report/inline_structured_report_workflow.py`
  - 正式收了：
    - `InlineStructuredReportWorkflowInput`
    - `InlineStructuredReportWorkflowDeps`
    - `run_inline_structured_report_workflow(...)`

- 把 `backend/app/services/report/report_service.py` 的 `_build_inline_structured_report(...)` 收成薄委托：
  - 主服务不再自己手工做 prompt / client / JSON 解析
  - 改成统一组装 deps 后调用 workflow

- 先补 workflow 测试，再用原有服务测试锁兼容：
  - `backend/tests/services/report/test_inline_structured_report_workflow.py`
  - 覆盖：
    - 已有 `report_structured` 时短路
    - 条件满足时能生成结构化结果
    - model/key 不合法时稳定跳过
    - client 失败时稳定回 `None`

## 4. 验证结果

- 定向回归：
  - `cd backend && SKIP_DB_RESET=1 python -m pytest tests/services/report/test_inline_structured_report_workflow.py tests/services/report/test_report_service_market_mode.py tests/services/report/test_report_assembly_workflow.py -q`
  - `12 passed`

- 语法自检：
  - `python -m py_compile backend/app/services/report/inline_structured_report_workflow.py backend/app/services/report/report_service.py backend/tests/services/report/test_inline_structured_report_workflow.py`
  - 通过

- 主门禁：
  - `SKIP_DB_RESET=1 make test-quality-gate`
  - `27 passed`

## 5. 这次执行的价值是什么？达到了什么目的？

这次最值钱的地方很直接：

- `ReportService` 里“要不要内联生成结构化报告”这件事，现在开始有自己的独立齿轮了
- 主服务继续变薄
- prompt / client / 解析链的真相源继续变硬

一句大白话收口：

- 这刀把报告链里还残留在主服务里的那条 LLM 重逻辑拆开了，第三轮推进没有口径漂移。
