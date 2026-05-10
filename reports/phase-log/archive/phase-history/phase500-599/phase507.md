# Phase 507 - Hotpost 双模型分层落地（快层 Gemini Flash-Lite + 重层 GPT-5.4-mini）

## 时间
- 2026-03-27

## 目标
- 把 Hotpost 从“单一 `llm_model_name` 贯穿全链路”改成“双模型角色 + 条件触发”的最小可用版本：
  - 快层：`google/gemini-2.5-flash-lite`
  - 重层：`openai/gpt-5.4-mini`
- 保持低耦合、高内聚：
  - 只改 Hotpost 域内配置、service、workflow、测试
  - 不动全局 report/analysis 链
  - 不引入 skills / Responses API / strict schema

## 执行内容

### 1) Hotpost 专属模型配置接线
- 更新：
  - `backend/config/hotpost_quality.yaml`
  - `backend/app/services/hotpost/hotpost_config.py`
- 新增配置：
  - `fast_model`
  - `reasoning_model`
  - `reasoning_enabled`
  - `reasoning_trigger_modes`
  - `reasoning_min_evidence`
  - `reasoning_trigger_on_gaps`
- 环境变量覆盖已接通：
  - `HOTPOST_FAST_MODEL`
  - `HOTPOST_REASONING_MODEL`
  - `HOTPOST_REASONING_ENABLED`
  - `HOTPOST_REASONING_TRIGGER_MODES`
  - `HOTPOST_REASONING_MIN_EVIDENCE`
  - `HOTPOST_REASONING_TRIGGER_ON_GAPS`

### 2) Service 层改成“快层默认”
- 更新：
  - `backend/app/services/hotpost/service.py`
- 现在：
  - query translation 固定走快层
  - `_maybe_llm_summary` 固定走快层
  - search workflow 输入不再只传一个模型名，而是传完整 Hotpost 路由策略

### 3) Report workflow 改成显式吃模型
- 更新：
  - `backend/app/services/hotpost/report_workflow.py`
- 调整：
  - `HotpostReportWorkflowInput.llm_model_name` 改为 `report_model_name`
  - 报告生成器不再自己猜模型，只吃本次调用显式传入的模型

### 4) Search workflow 接入双模型路由决策
- 更新：
  - `backend/app/services/hotpost/search_workflow.py`
  - `backend/app/schemas/hotpost.py`
- 新行为：
  - fast response 始终先跑
  - 满足以下任一条件时，补跑一次 reasoning report：
    - `mode == opportunity` 且 `evidence_count >= reasoning_min_evidence`
    - fast report 出现 `fallback / invalid_json / llm_generate_failed`
    - 自动补证后仍存在 `quality_contract_gaps`
  - 结果择优规则：
    - 先比 report 失败态
    - 再比 `quality_contract_gaps` 数量
    - 再比状态 / evidence_count
    - 平手时 `opportunity` 偏向 reasoning，其它模式保留 fast
- 新增 debug 字段：
  - `fast_model_name`
  - `reasoning_model_name`
  - `report_model_name`
  - `reasoning_triggered`
  - `final_report_layer`

## 测试与验证

### 定向回归
- 命令：
  - `cd backend && SKIP_DB_RESET=1 pytest tests/services/hotpost/test_hotpost_runtime_config.py tests/services/hotpost/test_hotpost_report_workflow.py tests/services/hotpost/test_hotpost_search_workflow.py tests/services/hotpost/test_hotpost_summary.py tests/services/hotpost/test_hotpost_search_service.py -q`
- 结果：
  - `18 passed`

### Hotpost 全回归
- 命令：
  - `cd backend && SKIP_DB_RESET=1 pytest tests/services/hotpost tests/scripts/acceptance/test_run_live_hotpost_acceptance.py -q`
- 结果：
  - `95 passed`

## 五问回顾
1. 发现了什么？
- Hotpost 之前虽然已经有“缺口驱动补证”，但 LLM 仍是单模型通吃，导致快活和重活没有拆开，质量和成本一起绑死。

2. 是否需要修复？
- 需要，而且这一步必须做在 Hotpost 域内，不能把全局 LLM 主链一起拖进来。

3. 精确修复方法？
- 新增 Hotpost 专属模型配置；
- service 把 translation/summary 固定到快层；
- report workflow 改成显式接模型；
- search workflow 负责“是否升级重层 + 谁的结果留下来”。

4. 下一步系统性计划是什么？
- 跑真实 `make acceptance-hotpost-quality-smoke`，看三模式 live 数据下：
  - reasoning 触发率
  - 输出提升幅度
  - 额外 API 成本
- 如果 `opportunity` 收益稳定，再考虑把 `rant` 纳入 reasoning 触发名单。

5. 这次执行的价值是什么？达到了什么目的？
- Hotpost 现在已经具备“快层先跑、重层按条件补跑、结果自动择优”的正式能力。
- 这一步把模型分层从纸面方案变成了可执行链路，同时没有破坏原来的补证闭环和质量合同。
