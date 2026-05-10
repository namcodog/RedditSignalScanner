# Phase 631 - 主链报告层切换到推理模型（第一刀）

时间：2026-04-03

## 这次做了什么

- 新增主链报告模型策略层：
  - `backend/app/services/report/report_llm_policy.py`
- 主链报告装配改成双模型分层：
  - structured / inline structured 继续走 fast model
  - narrative report 改走 reasoning model
- report enrichment 里两块最终表达能力也切到 reasoning model：
  - action item evidence summary
  - action item title / slogan decoration

## 这次为什么做

之前主链报告链和 hotpost 一样，默认共用 `settings.llm_model_name`。
当前默认模型是 `x-ai/grok-4.1-fast`，适合快整理，但放在最终判断和最终写作层偏弱。

这次的目标不是重写主链，而是先把：

- 结构层 = 快模型
- 最终判断层 = 推理模型

这个边界立起来。

## 具体落点

### 新增

- `backend/app/services/report/report_llm_policy.py`

职责：
- 统一决定 report 链的 fast / reasoning 模型分工
- `REPORT_REASONING_MODEL_NAME` 优先
- 否则复用 `HOTPOST_REASONING_MODEL`
- 再否则使用当前 report 默认推理模型 `xiaomi/mimo-v2-pro`

### 改动

- `backend/app/services/report/report_runtime_factory.py`
  - narrative builder 不再继续直接吃 `llm_model_name`
  - 通过 `report_llm_policy` 决定 narrative model

- `backend/app/services/report/report_runtime_inputs.py`
  - runtime 装配输入增加 `reasoning_model_name`

- `backend/app/services/report/report_enrichment_workflow.py`
  - `_summarize_action_item_evidence()` 改走 reasoning model
  - `_decorate_action_item_titles()` 改走 reasoning model
  - `_normalize_competitors()` 保持不动，继续视为中间清洗层

## 这次没做什么

- 没动 `analysis_engine`
- 没动 route / retrieval / facts / truth-source
- 没把主链整条链改成推理模型
- 没新长 orchestrator / 大文件

## 验证结果

执行：

```bash
cd backend && ../.venv/bin/python -m pytest \
  tests/services/report/test_report_llm_policy.py \
  tests/services/report/test_report_runtime_inputs.py \
  tests/services/report/test_report_assembly_deps_factory.py \
  tests/services/report/test_narrative_report_workflow.py \
  tests/services/report/test_report_enrichment_workflow.py -q
```

结果：

- `16 passed`

补充：

```bash
python -m compileall \
  backend/app/services/report/report_llm_policy.py \
  backend/app/services/report/report_runtime_factory.py \
  backend/app/services/report/report_runtime_inputs.py \
  backend/app/services/report/report_enrichment_workflow.py
```

结果：

- compile 通过

## 当前结论

主链第一刀已经落地：

- fast model 负责结构化层
- reasoning model 负责最终 narrative / final judgment 边缘层

这一步已经从代码层成立，不再只是口头方案。

## 下一步

下一步不扩散，继续按最小实现走：

1. 用 fresh live 任务验证 narrative 是否真实切到 reasoning model
2. 再决定要不要把 `report_brief` 也切成显式 fast-LLM 结构包
3. hotpost 与主链共用中间结构层，放到下一阶段做，不在这一刀里硬并
