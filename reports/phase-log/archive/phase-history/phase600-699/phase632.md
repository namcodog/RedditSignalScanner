# Phase 632 - 主链双模型分层 fresh live 验证

## 时间
- 2026-04-03

## 背景
- Phase 631 已把主链报告链拆成：
  - 结构层继续使用 fast model
  - 最终 narrative / final judgment 边缘层切到 reasoning model
- 本轮目标不是继续改代码，而是做一次 fresh live 验证，确认新分层已真正吃到运行时。

## 执行
- 按运维手册重启 isolated live runtime：
  - `python scripts/acceptance/manage_live_runtime.py restart`
- 跑 fresh `AI_Workflow` open-question live：
  - `python scripts/acceptance/run_open_question_live_acceptance.py --suite final --base-url http://127.0.0.1:8016 --frontend-base-url http://127.0.0.1:3006 --product-description '我想研究团队在 ChatGPT Claude Notion AI agent 和自动化 workflow 里的真实卡点，判断有没有 AI workflow 工具机会。' --required-tier A_full --min-reddit-links 2 --max-analysis-attempts 1 --warmup-wait-timeout-seconds 420`

## 结果
- fresh live 结果文件：
  - `backend/reports/local-acceptance/open_question_live_final_1775147171.json`
- 关键结论：
  - `task_id = 27c1dbd2-e562-4840-9522-9e98946db8d0`
  - `accepted = 1/1`
  - `report_tier = A_full`
  - `issues = []`
  - `target_communities = [r/Notion, r/ClaudeAI, r/ChatGPT]`
  - `reddit_links = 2`

## 新发现
- 这次 fresh live 已证明：
  - 主链在 fast-LLM + reasoning-model 分层下，fresh 运行时仍能稳定过线
- 但也暴露出一个剩余小尾巴：
  - `analyses.sources.analysis_audit` 在这次 fresh task 上仍为 `null`
  - `facts_v2_quality` 已正常写入且 `tier = A_full`
- 说明：
  - 结果链已经吃到新逻辑
  - 但审计摘要链还没有在 fresh live 上稳定落地

## 判断
- 当前可以确认：
  - 主链“fast 做结构，reasoning 做最终判断”这条模式是成立的
  - 这不是单元测试内成立，而是 fresh live 成立
- 当前不能确认：
  - 审计层是否已经和 fresh live 完整对齐

## 下一步
- 不回头改前段，不碰 retrieval / route / facts
- 下一刀应直接查：
  - 为什么 `analysis_audit` 在 fresh task 中没落库
  - 它到底是没有生成，还是生成后被覆盖/漏持久化
