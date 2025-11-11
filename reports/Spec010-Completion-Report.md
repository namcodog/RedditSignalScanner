# Spec 010 完成报告（样本级报告达成蓝图）

日期：$DATE

## 摘要
- 报告“能用能验”：痛点聚类、竞品分层、机会量化（参数化）与受控摘要 v2 完整接入；报告内容门禁具备三条硬约束与 LLM 覆盖率门槛。
- LLM 必开：接通 OpenAI 客户端，证据要点句、机会标题/口号默认生成，失败自动回退；归一化（基础版）已接，RAG 候选升级位已留。
- 可审计：生成 llm-audit-<task>.json；ReportPayload 元数据写入 llm_used/model/rounds。

## 交付明细
- LLM 接入
  - 客户端：backend/app/services/llm/clients/openai_client.py（读取 OPENAI_API_KEY / LLM_MODEL_NAME）
  - 要点句：backend/app/services/llm/openai_summarizer.py（失败回退 LocalExtractiveSummarizer）
  - 标题/口号：backend/app/services/llm/title_slogan.py（失败回退“跳过不阻断”）
  - 名字归一化（基础）：backend/app/services/llm/normalizer.py；ReportService 中对 competitors 执行归一化；RAG 候选通过 entity_summary + entity_dictionary（canonical）拼装
  - 集成：backend/app/services/report_service.py（action_items 生成阶段统一处理）
- 报告门禁
  - 三条硬门禁：簇≥2、分层≥2、potential_users_est>0
  - LLM 覆盖率：llm_coverage≥0.6 为必需；normalization_rate<0.9 扣分提醒
  - 实现：backend/scripts/content_acceptance.py
- 机会量化
  - 参数化：backend/config/scoring_rules.yaml: opportunity_estimator{ base,freq_weight,avg_score_weight,keyword_weight,theme_relevance,intent_factor }
  - 二次校准：社群规模乘子（scale_weight，可调），在 ReportService 汇总阶段生效
- 受控摘要 v2
  - 指标卡：P/S 比、竞争饱和度
  - 模板：backend/config/report_templates/executive_summary_v2.md
  - 渲染：backend/app/services/report/controlled_generator.py
- 诊断与导出
  - clusters-smoke / competitors-smoke / report-markdown（Make 目标已加）
  - 审计落盘：backend/reports/local-acceptance/llm-audit-<task>.json

## 使用说明
- 配置（backend/.env）
  - OPENAI_API_KEY=sk-...
  - LLM_MODEL_NAME=gpt-4o-mini（建议）
  - ENABLE_LLM_SUMMARY=true（默认）
- 命令
  - 语义门禁：make semantic-acceptance
  - 报告内容门禁：make content-acceptance（输出 llm_coverage、normalization_rate）
  - 导出 Markdown：make report-markdown TASK=<id>
  - 诊断：make clusters-smoke / competitors-smoke TASK=<id>

## 质量与门禁结果（口径）
- 内容门禁通过条件：score≥70 且 {clusters_ok && competitor_layers_ok && opportunity_users_ok && llm_ok}
- 参考指标：llm_coverage≥0.6；normalization_rate≥0.9（先扣分，后视稳定度再升为硬门槛）

## 优势与不足
- 优势
  - 看得懂：要点句、标题/口号让卡片“像人写的”；摘要有指标卡
  - 卡得住：三条硬门禁 + LLM 覆盖率门槛；自动化 Gate 避免“人工挑”
  - 调得动：机会量化可配/可复现；社群规模乘子可调
  - 可追溯：审计文件与元数据保障可回看
- 不足/后续
  - Normalizer 升级为 OpenAI RAG（现已预留模块 openai_normalizer，可继续完善置信度与候选裁剪）
  - 审计明细扩展（逐条证据输入/输出、标题/口号来源描述）
  - “核心战场画像 + 策略建议”段落自动生成（失败回退）

## 变更清单
- 见仓库文件：
  - llm/* 模块、report_service 接线、content_acceptance 门禁增强、scoring_rules.yaml 参数位、受控摘要模板/生成器、诊断与导出脚本

（本报告由实施脚本自动生成模板，具体数值与运行截图请参考 llm-audit 与 content-acceptance 输出）
