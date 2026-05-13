# Phase 494 - 开放题验收主链落地（离线门禁 + live smoke/final 入口）

## 时间
- 2026-03-26

## 目标
- 停止“产品描述硬编码推导 pain”路径，避免无证据结论。
- 加强低信号噪音拦截（版务/删帖/权限类文本）。
- 把验收入口从“只盯 8 领域矩阵”升级为“开放题三层漏斗”。

## 执行内容

### 1) 去掉产品描述直推痛点（主链收口）
- 文件：`backend/app/services/report/analysis_payload_loader.py`
- 变更：
  - 删除 `_PRODUCT_DESCRIPTION_PAIN_RULES` 的硬编码映射。
  - `_build_fallback_pain_points(...)` 不再从 `sources.product_description` 生成 pain。
  - `_enforce_domain_coherence_on_pain_points(...)` 改为“只过滤，不补写”。
  - 保留兼容函数 `_derive_pains_from_product_description(...)`，但固定返回空列表（避免旧依赖断裂）。
- 结果：
  - pain 只能来自 `pain_clusters / opportunities.source_examples` 的证据文本，不再由题面文案直接合成。

### 2) Guardrails 增强：拦截版务/权限噪音
- 文件：`backend/app/services/report/content_guardrails.py`
- 新增低信号片段（示例）：
  - `can't post poll / removed by moderators / automoderator / account too new / not enough karma / use the weekly thread`
- 目的：
  - 避免把社区规则/删帖提示误当业务痛点或机会文案。

### 3) 开放题验收脚本 + Makefile 门禁入口
- 新增脚本：
  - `backend/scripts/acceptance/run_open_question_live_acceptance.py`
- 核心能力：
  - `smoke`（3 条代表开放题）与 `final`（1 条最终题）双模式。
  - 同时检查：
    - `required tier`（默认 `A_full`）
    - `canonical_report_json` 结构完整性（pain/opportunity/communities）
    - 低信号标题拦截（placeholder / low-signal）
    - 证据链可点击 Reddit 链接（http(s)+reddit.com）
    - narrative 与 canonical 的基础对齐（markdown 首条标题可见）
  - 输出：`backend/reports/local-acceptance/open_question_live_{suite}_<ts>.json`
- Makefile 新增目标（`makefiles/test.mk`）：
  - `acceptance-offline-gate`
  - `acceptance-live-smoke`
  - `acceptance-live-final`

### 4) 测试与回归
- 新增测试：
  - `backend/tests/scripts/acceptance/test_run_open_question_live_acceptance.py`
- 重写/更新测试：
  - `backend/tests/services/report/test_analysis_payload_loader.py`
  - `backend/tests/services/report/test_content_guardrails.py`
  - `backend/tests/services/report/test_structured_report_fallback.py`
- 验证命令：
  - `pytest backend/tests/services/report/test_analysis_payload_loader.py -q` -> `11 passed`
  - `pytest backend/tests/services/report/test_content_guardrails.py -q` -> `10 passed`
  - `pytest backend/tests/services/report/test_structured_report_fallback.py -q` -> `32 passed`
  - `pytest backend/tests/services/report/test_analysis_payload_loader.py backend/tests/services/report/test_content_guardrails.py backend/tests/services/report/test_structured_report_fallback.py backend/tests/scripts/acceptance/test_run_open_question_live_acceptance.py -q` -> `58 passed`
  - `make acceptance-offline-gate` -> `64 passed`

## 四问回顾
1. 发现了什么？
- 报告噪音的主源之一是“题面文案直推痛点”，这会在低样本时制造伪结论；同时版务噪音会污染机会卡。

2. 是否需要修复？
- 需要，且必须在主链修而不是前端掩盖。

3. 精确修复方法？
- 切断 `product_description -> pain` 生成路径；
- 强化 `content_guardrails` 拦截规则；
- 建立开放题验收脚本，强制检查“证据可点击 + 结构完整 + 文案无低信号”。

4. 下一步系统性计划？
- 直接跑：
  - `make acceptance-live-smoke`
  - `make acceptance-live-final`
- 若失败：
  - 先看 `open_question_live_*.json` 的 `issues` 字段定位根因，再做离线修复，不直接盲目重跑 live。

5. 这次执行的价值是什么？
- 验收机制从“凭运气刷矩阵”升级为“开放题可复验门禁”：
  - 先离线门禁挡回归；
  - 再 live smoke 验证主链；
  - 最后 final 一题封板。
