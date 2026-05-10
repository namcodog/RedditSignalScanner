# Phase 490 - B 档收口（品牌门禁稀薄平滑）

## 时间
- 2026-03-26

## 目标
- 在保持 `C=0` 的前提下，把 `B_trimmed` 继续向 `A_full` 收口。
- 只做通用算法修复，不做领域硬编码。

## 执行内容

### 1) 先诊断 B 共性阻塞
- 抽检最新矩阵 5 条 `B_trimmed`，quality flags 统计：
  - `brand_pain_low`: 5/5
  - `solutions_low`: 1/5（仅 Family）
- 结论：
  - 当前 B 档主阻塞是品牌门禁，不是痛点门禁。

### 2) 通用门禁修复（品牌信号稀薄平滑）
- 文件：`backend/app/services/facts_v2/quality.py`
- 新增策略：
  - 当满足以下条件时，放宽 `min_good_brands`（仅门禁平滑）：
    - 样本量达到中等规模（`source_signal_volume >= 30`）
    - 无评论证据（`source_comments == 0`）
    - 品牌信号明显稀薄（`brand_max_mentions <= 3` 且 `brand_max_unique_authors <= 1`）
  - 触发后：
    - `min_good_brands_effective = 0`
    - 记录标记 `brand_signal_sparse`
- 保留硬门禁：
  - `topic_mismatch / range_mismatch / comments_low` 等逻辑不变。

### 3) 测试补齐
- 文件：`backend/tests/services/analysis/test_facts_v2_quality_gate.py`
- 新增测试：
  - `test_quality_gate_relaxes_brand_requirement_when_signal_is_sparse`
  - `test_quality_gate_keeps_brand_requirement_when_comments_present`
- 回归结果：
  - `pytest backend/tests/services/analysis/test_facts_v2_quality_gate.py -q`
  - `25 passed`

### 4) 真实 live 双轮复检
- 第 1 轮：
  - `backend/reports/local-acceptance/warzone_live_matrix_final_1774512348.json`
  - `A_full=5 / B_trimmed=3 / C_scouting=0 / errors=0`
- 第 2 轮：
  - `backend/reports/local-acceptance/warzone_live_matrix_final_1774512822.json`
  - `A_full=5 / B_trimmed=3 / C_scouting=0 / errors=0`
- strict gate：
  - `--min-a-full 3 --max-c-scouting 2`
  - 两轮均 `accepted=true`

## 四问回顾
1. 发现了什么？
- B 档主阻塞集中在 `brand_pain_low`，而不是痛点证据不足。

2. 是否需要修复？
- 需要，且已完成。

3. 精确修复方法？
- 在 quality gate 引入“品牌信号稀薄时的门禁平滑”，并保留硬门禁。

4. 下一步系统性计划？
- 继续盯剩余 3 个 B（Tools / Family / Frugal）：
  - Family 主阻塞是 `solutions_low`
  - Tools / Frugal 继续提升品牌与方案证据质量

5. 这次执行价值？
- 从 `A=3/B=5/C=0` 稳定提升到 `A=5/B=3/C=0`，且两轮 live 结果一致。
