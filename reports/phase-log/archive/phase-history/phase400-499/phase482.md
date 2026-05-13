# Phase 482 - AI workflow 通用中文 pain/opportunity 收口验证

## 本轮目标
- 把 AI workflow 宽题面里的低信号英文 pain 彻底收成中文业务痛点
- 把 `产品机会：英文句子` 这类半中半英机会标题纳入 fallback 合同
- 用真实 live 验证 report payload 是否已经稳定可控

## 关键修复

### 1. payload 层把低信号英文 pain 当成占位词
- 文件：
  - `backend/app/services/report/analysis_payload_loader.py`
- 修复：
  - 新增 `_is_low_signal_scaffold_pain_title(...)`
  - `_is_placeholder_pain_item(...)` 现在把 `高频抱怨：<纯英文半句>` 视为占位 pain

### 2. AI workflow 宽题面补通用中文脚手架
- 文件：
  - `backend/app/services/report/analysis_payload_loader.py`
- 修复：
  - 为宽题面 `ChatGPT / Notion / AI agent / workflow / 自动化` 增加通用 pain 规则
  - `_derive_pains_from_product_description(...)` 改为大小写无关匹配，英文题眼能真正命中

### 3. 机会标题拒绝半中半英低信号 copy
- 文件：
  - `backend/app/services/report/structured_report_fallback.py`
- 修复：
  - `_is_generic_opportunity_title(...)` 现在把 `产品机会：<纯英文>` 视为低信号标题
  - contract 会自动退回到围绕中文痛点的业务机会标题

## 回归测试
- `pytest backend/tests/services/report/test_analysis_payload_loader.py backend/tests/services/report/test_structured_report_fallback.py backend/tests/services/analysis/test_insight_synthesis.py -q`
- 结果：`50 passed`

## 真实 live 验证

### AI workflow
- base url: `http://127.0.0.1:8016`
- 最终任务：
  - `20d3e60f-8a41-45ac-83a3-04b4cc0d0ac1`
- 结果：
  - `report_tier = B_trimmed`
  - `target_communities = ["r/ClaudeAI","r/LocalLLaMA","r/ChatGPT","r/Notion"]`
  - `pain_titles`：
    - `多人一起协作时，交接和责任边界很容易断档`
    - `流程一旦跨工具切换，信息和动作就容易断开`
    - `任务很多，但真正推进情况并不清楚`
  - `opportunity_titles`：
    - `围绕「多人一起协作时，交接和责任边界很容易断档」的产品机会`
    - `围绕「流程一旦跨工具切换，信息和动作就容易断开」的产品机会`

## 阶段结论
- 这轮已经把 AI workflow 的两个主要不稳定因素收掉了：
  - `高频抱怨：英文半句`
  - `产品机会：英文句子`
- 现在 AI workflow 这条线虽然仍是 `B_trimmed`，但 payload 已经回到稳定、可解释、可控的中文业务表达
- 当前剩余重点不再是 AI 的 report copy 断裂，而是：
  - `B_trimmed -> A_full` 的深度提升
  - `Home_Lifestyle / Family_Parenting` 的样本深度与 query focus

## 下一步
- 继续横向打 `Home_Lifestyle / Family_Parenting`
- 确认 8 领域里剩余 `B_trimmed / C_scouting` 是否已经从“表达失真”收敛为“样本深度不足”
