# Phase 489 - 低样本场景门禁平滑（Family 从 C 收口到 B）

## 时间
- 2026-03-26

## 目标
- 在不加领域硬编码的前提下，继续压缩 `C_scouting`。
- 针对两轮矩阵里唯一剩余 `C`（`Family_Parenting`）做系统级收口。

## 执行内容

### 1) 根因定位（真实数据）
- 抽检两条 Family 任务：
  - `36ea6c04-dd66-46cd-9ed4-46d5091e6db3`
  - `ec5ce07f-3123-49d3-b444-6c96d27f03af`
- 共同特征：
  - `source_posts=18`, `source_comments=0`
  - `high_value_pains` 并非空（2 条），但每条 `mentions=2`
  - 旧阈值平滑后仍是 `pain_min_mentions_effective=3`
  - 结果：`good_pains=0`，落到 `C_scouting`

### 2) 系统修复（通用算法）
- 文件：`backend/app/services/facts_v2/quality.py`
- 调整：
  - pain 阈值改为按 `source_signal_volume = posts + comments` 平滑。
  - `pain_min_mentions`：
    - `floor: 2`
    - `ratio: 0.12`
  - `pain_min_unique_authors`：
    - `floor: 2`
    - `ratio: 0.08`
  - 新增指标：`source_signal_volume`。
- 原则：
  - 只改通用门禁算法，不按 warzone/domain 写死。
  - 保持 topic/range/comments 等硬门禁不变。

### 3) 测试
- 文件：`backend/tests/services/analysis/test_facts_v2_quality_gate.py`
- 更新：
  - 调整已有自适应阈值预期（34 帖场景）。
  - 新增低样本场景测试：`test_quality_gate_relaxes_pain_threshold_for_low_signal_volume`
- 结果：
  - `pytest backend/tests/services/analysis/test_facts_v2_quality_gate.py -q`
  - `23 passed`

### 4) live 验证（两轮）
- 第 1 轮：
  - `backend/reports/local-acceptance/warzone_live_matrix_final_1774510225.json`
  - `A_full=3 / B_trimmed=5 / C_scouting=0 / errors=0`
- 第 2 轮：
  - `backend/reports/local-acceptance/warzone_live_matrix_final_1774510692.json`
  - `A_full=3 / B_trimmed=5 / C_scouting=0 / errors=0`
- strict gate：
  - `--min-a-full 3 --max-c-scouting 2`
  - 两轮均 `accepted=true`

## 四问回顾
1. 发现了什么？
- Family 的 `C` 不是“无信号”，而是“低样本下阈值仍偏高”导致的误降级。

2. 是否需要修复？
- 需要，且已完成。

3. 精确修复方法？
- 在 `facts_v2` 质量门禁做总样本量平滑，不做领域特判。

4. 下一步系统计划？
- 继续用 `test-e2e-warzone-live-matrix-2x` 做日常回归，重点盯 A/B 结构和证据链质量。

5. 这次执行价值？
- 把最后一条 `C` 稳定收掉，形成连续两轮 `C=0` 的真实 live 结果。
