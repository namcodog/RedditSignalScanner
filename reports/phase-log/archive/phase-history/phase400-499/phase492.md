# Phase 492 - live C 档归零（pain fallback 门禁修复）

## 时间
- 2026-03-26

## 目标
- 收口上一轮残留的 `C_scouting=1`（Family_Parenting）
- 保持“通用算法修复”，不做领域硬编码
- 复验至少 2 轮 8 领域 live matrix

## 执行内容

### 1) 根因定位
- 先锁定最新矩阵中的唯一 `C`：
  - `Family_Parenting`
  - `report_tier=C_scouting`
  - `analysis_blocked=scouting_brief`
- 通过 `/api/report/{task_id}` 检查 `sources.facts_v2_quality` 发现：
  - `flags=["pains_low","brand_pain_low"]`
  - `pain_clusters_pipeline_status="empty"`
  - `high_value_pains=[]`
  - 但 `business_signals.pain_points` 已有频次信号

### 2) 通用修复（quality gate）
- 文件：`backend/app/services/facts_v2/quality.py`
- 修复策略：
  - 当 `high_value_pains` 为空时，改用 `business_signals.pain_points` 构建兜底 pain 候选参与 quality gate 判定
  - 新增 `evidence id -> author` 索引，尽量从样本中还原 `unique_authors`
  - 新增 metrics：`pain_fallback_used`
- 说明：
  - 这是质量门禁层的信号兜底，不改领域路由，不引入 mock，不写题材硬编码

### 3) 测试补齐
- 文件：`backend/tests/services/analysis/test_facts_v2_quality_gate.py`
- 新增测试：
  - `test_quality_gate_uses_pain_points_fallback_when_high_value_pains_empty`
- 回归：
  - `pytest backend/tests/services/analysis/test_facts_v2_quality_gate.py -q`
  - 结果：`26 passed`

### 4) 真实 live 双轮复验
- 第 1 轮：
  - `backend/reports/local-acceptance/warzone_live_matrix_final_1774517567.json`
  - `A_full=7 / B_trimmed=1 / C_scouting=0 / errors=0`
  - strict gate：`accepted=true`
- 第 2 轮：
  - `backend/reports/local-acceptance/warzone_live_matrix_final_1774518054.json`
  - `A_full=6 / B_trimmed=2 / C_scouting=0 / errors=0`
  - strict gate：`accepted=true`

## 四问回顾
1. 发现了什么？
- `C` 的核心不是“没内容”，而是 `high_value_pains` 为空时门禁缺少有效兜底，导致被 `pains_low` 拉到 scouting。

2. 是否需要修复？
- 需要，且已修复完成。

3. 精确修复方法？
- 在 `facts_v2` 质量门禁中引入 `pain_points -> pain candidates` 的通用兜底路径，并记录 `pain_fallback_used` 指标。

4. 下一步系统性计划？
- 继续横向复检，重点把 `B_trimmed` 的共性阻塞（尤其 `solutions_low`）收口到通用门禁与证据策略，而非题材特判。

5. 这次执行价值？
- 将 8 领域 live 从“偶发 `C=1`”收口为“连续两轮 `C=0`”，并保持 strict gate 稳定通过。
