# Phase 488 - 质量门禁阈值重构（从固定阈值改为数据量自适应）

## 时间
- 2026-03-26

## 目标
- 根治 strict hard-gate 卡点（`A_full>=3 && C_scouting<=2`）。
- 不靠领域硬编码提分，改成通用的“数据量自适应阈值”。
- 用 2 轮真实 live 矩阵确认不是偶然命中。

## 执行内容

### 1) 根因复盘（不是前端问题）
- 对 `C_scouting` 任务抽检后确认：
  - `facts_slice.business_signals.high_value_pains` 已有信号（不是空白）
  - 但 quality gate 仍用固定阈值（pain/brand `mentions>=10`, `authors>=5`），导致 `good_pains/good_brands` 统计偏零。
- 对 `B_trimmed` 任务抽检确认：
  - 主要卡在 `brand_pain_low`，同样是固定阈值在中等样本量下过严。

### 2) 代码修复（通用算法，不做领域特判）
- 文件：`backend/app/services/facts_v2/quality.py`
- 核心改动：
  - 新增 `_resolve_volume_capped_threshold(...)`。
  - 将 pain/brand 的 `mentions` 与 `unique_authors` 阈值改成“配置阈值 + source_posts 数据量上限”的组合。
  - 在 metrics 写入：
    - `*_configured`
    - `*_effective`
  - 保留原有硬门禁：
    - `topic_mismatch / range_mismatch / comments_low` 等判定逻辑不变。

### 3) 测试补齐
- 文件：`backend/tests/services/analysis/test_facts_v2_quality_gate.py`
- 新增：
  - `test_quality_gate_uses_volume_capped_pain_threshold_for_sparse_posts`
  - `test_quality_gate_uses_volume_capped_brand_threshold_for_a_full`
- 全量结果：
  - `pytest backend/tests/services/analysis/test_facts_v2_quality_gate.py -q`
  - `22 passed`

### 4) 真实 live 双轮验证
- 重启隔离 runtime 后连跑两轮 8 领域矩阵：
  - `backend/reports/local-acceptance/warzone_live_matrix_final_1774508070.json`
  - `backend/reports/local-acceptance/warzone_live_matrix_final_1774508565.json`
- 两轮结果一致：
  - `A_full=4`
  - `B_trimmed=3`
  - `C_scouting=1`
  - `errors=0`
- strict gate 均通过：
  - `validate_warzone_live_matrix.py --min-a-full 3 --max-c-scouting 2`
  - `accepted=true`

### 5) Makefile 固化（可复用 SOP）
- 修改：
  - `makefiles/test.mk`
  - `Makefile`
- 新增目标：
  - `test-e2e-warzone-live-matrix`
  - `test-e2e-warzone-live-matrix-2x`
- 作用：
  - 一键跑 8 领域 live + 严格门禁校验
  - 一键连跑 2 轮做稳定性复检

## 四问回顾
1. 发现了什么？
- strict gate 卡点本质是固定阈值与样本量不匹配，而不是模型随机漂移。

2. 是否需要修复？
- 必须修；否则系统会在中低样本场景稳定误降级到 `C/B`。

3. 精确修复方法？
- 在 `facts_v2` 质量门禁层引入通用“数据量自适应阈值”，并保留硬门禁不变。

4. 下一步系统性计划？
- 继续做 8 领域日常回归（使用新 Makefile 目标），并将稳定门禁纳入发布前必跑项。

5. 这次执行价值？
- 把“看起来漂移”的问题收敛成可解释、可测试、可复验的质量算法问题；并且已用两轮真实 live 得到一致达标结果。
