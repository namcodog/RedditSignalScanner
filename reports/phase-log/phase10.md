# Phase 10 — Spec 010 缺口补齐（门禁 + 机会量化参数化 + 诊断脚本）

日期：$DATE

## 1）发现了什么问题/根因？
- 门禁缺失 Spec010 的三条硬约束：pain_clusters ≥ 2、competitor_layers ≥ 2、opportunities[*].potential_users_est > 0。
- 机会量化采用启发式常数，未参数化，难以调参与复现；且仅输出字符串，不利于门禁断言。
- 缺少 clusters-smoke / competitors-smoke 诊断命令与 Make 目标。

## 2）是否已精确定位？
- content_acceptance.py 仅做统计一致性、证据密度、Top 社区、洞察丰富度等检查，未覆盖三条硬门禁。
- signal_extraction.py 在行 605 附近以固定系数计算 potential_users。
- analysis_engine.py 仅下发了字符串 potential_users，未同时输出数值字段。

## 3）精确修复方法（已实现）
- 门禁补齐（Spec010）：
  - backend/scripts/content_acceptance.py 增加 clusters_ok / competitor_layers_ok / opportunity_users_ok，并纳入 passed 计算。
- 机会量化参数化：
  - backend/config/scoring_rules.yaml 新增 opportunity_estimator 参数块（base/freq_weight/avg_score_weight/keyword_weight/theme_relevance/intent_factor/participation_rate）。
  - backend/app/services/analysis/scoring_rules.py 新增 OpportunityEstimatorConfig 并由 Loader 解析；保持向后兼容。
  - backend/app/services/analysis/signal_extraction.py 改为读取上面的参数，并使用 multiplier（主题相关性 + 意愿强度）调整；保证最小/最大边界。
  - backend/app/services/analysis_engine.py 在机会项中附带 potential_users_est 数值，同时保留原字符串字段。
  - backend/app/schemas/analysis.py 为 OpportunitySignal 增加可选的 potential_users_est: int 字段（兼容旧数据）。
- 诊断脚本与 Make 目标：
  - 新增 backend/scripts/cluster_smoke.py 与 competitor_smoke.py：读取任务并输出 clusters / competitor_layers_summary JSON。
  - Makefile 增加 clusters-smoke / competitors-smoke 目标，输出落盘到 backend/reports/local-acceptance/。

## LLM 接入（新增）

- OpenAI 客户端接通（模块化）：
  - 客户端：backend/app/services/llm/clients/openai_client.py（读取 OPENAI_API_KEY / LLM_MODEL_NAME）
  - Summarizer（要点句）：优先 OpenAI，失败回退本地提取式（LocalExtractiveSummarizer）
  - Normalizer（基础本地）：LocalDeterministicNormalizer（为后续 OpenAI Normalizer 预留位）
  - 标题/Slogan：TitleSloganGenerator（OpenAI，失败回退跳过，不阻断）
  - 集成：ReportService 在组装 action_items 时生成要点句与标题/Slogan；metadata 写入 llm_used/model
  - 门禁：content_acceptance 增加 llm_coverage（≥0.6 必须）

## 机会人数校准（新增）

- 在 ReportService 汇总阶段加入“社群规模乘子”（scale_weight 参数化），对 potential_users_est 做二次校准并同步字符串展示。


## 4）下一步做什么？
- 回收现有样本任务，运行 clusters-smoke 与 competitors-smoke，确认典型任务的门禁覆盖达标。
- 视需要在 opportunity_report 中优先使用 potential_users_est 计算 product_fit（当前保持兼容逻辑）。
- 与前端对齐：若前端需要展示数值估计，则按字段名 potential_users_est 读取。

## 5）这次修复的效果是什么？达到了什么结果？
- content_acceptance 增加三条硬门禁后，报告“样本级可用”可被自动化严格卡住，减少人工验收负担。
- 机会量化参数化，后续可在 YAML 中快速调参并复现，且提供稳定的数值断言位 potential_users_est。
- 诊断脚本补齐，降低排障与人工验证的成本；Make 目标一键落盘，便于归档与比对。

## 变更清单
- tests: backend/tests/scripts/test_content_acceptance_spec010.py
- scripts: backend/scripts/content_acceptance.py（新增断言）
- config: backend/config/scoring_rules.yaml（新增 opportunity_estimator）
- core: backend/app/services/analysis/scoring_rules.py（Loader 扩展）
- core: backend/app/services/analysis/signal_extraction.py（参数化估计）
- core: backend/app/services/analysis_engine.py（opportunities 输出 potential_users_est）
- schema: backend/app/schemas/analysis.py（机会数值位）
- tools: backend/scripts/cluster_smoke.py、backend/scripts/competitor_smoke.py
- Make: 新增 clusters-smoke、competitors-smoke 目标；help 菜单增加指引
