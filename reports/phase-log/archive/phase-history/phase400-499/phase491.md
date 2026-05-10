# Phase 491 - 结构噪音回归修复（nested opportunity）+ live 复验

## 时间
- 2026-03-26

## 目标
- 修复本轮 live matrix 严格门禁失败项：`nested opportunity title`
- 保持通用修复，不引入领域硬编码
- 重新跑 live 验证，确认 strict gate 恢复通过

## 执行内容

### 1) 先恢复门禁单测一致性
- 文件：`backend/tests/services/analysis/test_facts_v2_quality_gate.py`
- 动作：
  - 更新品牌阈值自适应后的断言口径：
    - `brand_min_mentions_effective: 5 -> 3`
    - `brand_min_unique_authors_effective: 3 -> 1`
  - 调整“品牌信号稀薄放宽”测试触发条件：`min_good_brands=2`
- 验证：
  - `pytest backend/tests/services/analysis/test_facts_v2_quality_gate.py -q`
  - 结果：`25 passed`

### 2) live matrix 首轮触发真实阻塞
- 命令：`make test-e2e-warzone-live-matrix-2x`
- 首轮输出：`backend/reports/local-acceptance/warzone_live_matrix_final_1774514944.json`
- 结果：
  - `A_full=5 / B_trimmed=2 / C_scouting=1 / errors=0`
  - strict gate 失败，唯一问题：
    - `Tools_EDC[2]: nested opportunity title=围绕「围绕「...」的产品机会`

### 3) 根因与修复
- 根因：
  - 机会标题去壳逻辑只覆盖了标准模板，未覆盖痛点标题后缀 `（场景N）`。
  - 导致 `围绕「围绕「...（场景2）」的产品机会` 漏网。
- 修复文件：
  - `backend/app/services/report/structured_report_fallback.py`
- 修复动作：
  - 扩展 `_SCAFFOLD_PAIN_TITLE_RE`，支持 `（场景N）` / `（场景N-M）` 后缀：
    - `^围绕「(?P<pain>.+?)」反复出现的关键麻烦(?:（(?:第\d+类|场景\d+(?:-\d+)?)）)?$`
- 回归测试：
  - `backend/tests/services/report/test_structured_report_fallback.py`
  - 在 `test_enforce_structured_report_contract_avoids_nested_opportunity_scaffold_title` 增加 `（场景2）` 嵌套案例断言
  - 验证：`pytest backend/tests/services/report/test_structured_report_fallback.py -q` -> `32 passed`

### 4) 修复后 live 双轮复验
- 第 1 轮：
  - `backend/reports/local-acceptance/warzone_live_matrix_final_1774515707.json`
  - `A_full=6 / B_trimmed=1 / C_scouting=1 / errors=0`
  - strict gate：`accepted=true`
- 第 2 轮：
  - `backend/reports/local-acceptance/warzone_live_matrix_final_1774516144.json`
  - `A_full=7 / B_trimmed=0 / C_scouting=1 / errors=0`
  - strict gate：`accepted=true`

## 四问回顾
1. 发现了什么？
- 当前阻塞不是随机漂移，而是结构化标题规范化遗漏（`nested scaffold`）。

2. 是否需要修复？
- 需要，且已完成。

3. 精确修复方法？
- 在 `structured_report_fallback` 扩展 pain scaffold 正则，覆盖 `（场景N）` 后缀并补测试。

4. 下一步系统性计划？
- 继续用 8 领域 live 矩阵横向复检，优先盯剩余 `C_scouting` 的统一根因（样本深度/评论利用率）。

5. 这次执行的价值？
- 从“首轮 strict gate 卡死”恢复为“修复后连续两轮 strict gate 通过”，且 A 档上移到 `6~7`。
