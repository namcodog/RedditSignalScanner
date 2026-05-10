# Phase 483 - Home / Family 弱领域系统收口验证

## 本轮目标
- 验证 `Home_Lifestyle` 和 `Family_Parenting` 现在到底是：
  - 系统主链还在漂
  - 还是已经收敛为样本深度不足
- 继续把“不稳定因素”收成“稳定可控结果”

## 本轮执行

### 1. 起干净隔离 runtime
- `backend/scripts/acceptance/manage_live_runtime.py start --json-only`
- 端口：`8016`
- 确认：
  - backend 单实例
  - `analysis-live` 单实例
  - `bulk-live` 单实例

### 2. 重跑 Home_Lifestyle live
- 题面：
  - `我想研究 home cleaning、vacuum、organization、storage 这些家庭清洁和收纳场景里的真实麻烦，尤其是灰尘、pet hair、small space 和 cleaning routine，判断有没有工具机会。`
- 最终任务：
  - `5aebab07-6438-4cd2-b9a7-8ba815f7fb8e`
- 结果：
  - `report_tier = C_scouting`
  - `analysis_blocked = scouting_brief`
  - `target_communities = ["r/homeowners","r/organization","r/CleaningTips","r/declutter"]`
  - `pain_titles`
    - `清洁步骤容易断档，家里总在反复返工`
    - `灰尘和宠物毛反复积累，小空间清洁收纳很费力`
    - `东西一多就容易堆乱，收纳系统很难长期维持`
  - `opportunity_titles`
    - `围绕「清洁步骤容易断档，家里总在反复返工」的产品机会`
    - `围绕「灰尘和宠物毛反复积累，小空间清洁收纳很费力」的产品机会`

### 3. 修 Family_Parenting 第 3 条 pain 缺失
- 文件：
  - `backend/app/services/report/analysis_payload_loader.py`
  - `backend/tests/services/report/test_analysis_payload_loader.py`
- 修复：
  - 为宽题面 `routine + parenting 协作` 增加通用家庭协作 pain 规则
  - 补回归，锁住：
    - `家人轮流照护时信息接不上，重复和漏做会一起发生`
- 回归：
  - `pytest backend/tests/services/report/test_analysis_payload_loader.py backend/tests/services/report/test_structured_report_fallback.py -q`
  - 结果：`44 passed`

### 4. 重跑 Family_Parenting live
- 题面：
  - `我想研究新生儿家庭在夜奶 喂养 睡眠 routine 和 parenting 协作上的真实痛点，判断有没有育儿记录工具机会。`
- 最终任务：
  - `6a1eb64d-5a4c-4d9c-8afa-a0a36dafe17e`
- 结果：
  - `report_tier = C_scouting`
  - `analysis_blocked = scouting_brief`
  - `target_communities = ["r/NewParents","r/Parenting","r/beyondthebump"]`
  - `pain_titles`
    - `半夜照护节奏一乱，大人和孩子都更难睡稳`
    - `睡眠和喂养节奏不清楚，照护安排很难提前预判`
    - `家人轮流照护时信息接不上，重复和漏做会一起发生`
  - `opportunity_titles`
    - `围绕「半夜照护节奏一乱，大人和孩子都更难睡稳」的产品机会`
    - `围绕「睡眠和喂养节奏不清楚，照护安排很难提前预判」的产品机会`

## 关键结论

- `Home_Lifestyle` 和 `Family_Parenting` 这两个最弱领域，现在都已经不是“输出失真”问题。
- 它们的共同形态已经收敛成：
  - `report_tier = C_scouting`
  - `analysis_blocked = scouting_brief`
  - 但 `pain/opportunity/communities` 都是稳定的中文业务表达
- 这意味着系统层现在更接近稳定：
  - 主链不再乱漂
  - 剩余主要矛盾开始转成样本深度不足

## 当前系统判断

- 已经稳定可控的系统层：
  - `warzone routing`
  - `target_communities` canonical 出口
  - 多领域 pain/opportunity 中文化合同
  - AI/Home/Family 的弱领域 fallback 中文脚手架
- 当前剩余主要问题：
  - 不是表达乱跳
  - 而是 `B_trimmed / C_scouting -> A_full` 的样本深度、评论覆盖和 query focus 深度提升

## 下一步
- 回到完整 8 领域整轮 live 复验
- 验证剩余领域是否也都已经从“输出不稳”收敛为“深度不够”
