# Phase 493 - live 二轮复验与波动根因定位

## 时间
- 2026-03-26

## 目标
- 收敛当前分支阻塞（`quality gate` 测试失败）
- 跑真实 8 领域 live matrix 二轮复验
- 定位“第一轮全 A、第二轮回退”的系统根因（非拍脑袋）

## 执行内容

### 1) 修复当前测试阻塞
- 文件：`backend/tests/services/analysis/test_facts_v2_quality_gate.py`
- 问题：
  - `test_quality_gate_does_not_relax_brand_requirement_when_signal_volume_too_low` 的样例本身满足新阈值，断言已过时。
- 修复：
  - 将样例 `brand_pain.mentions` 从 `2` 调整为 `1`，确保确实触发“品牌门禁不足”。
  - 新增断言 `brand_min_mentions_effective == 2`，固定这条测试的语义边界。
- 验证：
  - `pytest backend/tests/services/analysis/test_facts_v2_quality_gate.py -q`
  - 结果：`29 passed`

### 2) 真实 live 第 1 轮（8 领域）
- 命令：`make test-e2e-warzone-live-matrix`
- 结果文件：
  - `backend/reports/local-acceptance/warzone_live_matrix_final_1774520857.json`
- 结果：
  - `A_full=8 / B_trimmed=0 / C_scouting=0 / errors=0`
- strict gate：
  - `accepted=true`

### 3) 真实 live 第 2 轮（8 领域）
- 命令：`make test-e2e-warzone-live-matrix`
- 结果文件：
  - `backend/reports/local-acceptance/warzone_live_matrix_final_1774521340.json`
- 结果：
  - `A_full=6 / B_trimmed=1 / C_scouting=1 / errors=0`
- strict gate：
  - `accepted=true`

### 4) 回退点根因定位（DB 取证）
- `Tools_EDC`（`B_trimmed`）：
  - `flags=["brand_pain_low"]`
  - `good_pains=2 / solutions=9 / good_brands=0`
  - `source_signal_volume=89 / source_comments=11`
  - 结论：不是没内容，是“品牌证据门禁”导致掉 B。
- `Family_Parenting`（`C_scouting`）：
  - `flags=["pains_low","brand_pain_low","solutions_low"]`
  - `source_signal_volume=8 / source_comments=0`
  - `good_pains=0 / good_brands=0 / solutions=2`
  - 结论：是低样本量触发的 `scouting_brief`，属于 live 噪音下的采样深度波动。

## 四问回顾
1. 发现了什么？
- 当前系统已能跑出全 A，但二轮复验仍存在 live 波动；核心波动点不是“随机报错”，而是“品牌门禁稳定性 + 低样本采样深度”。

2. 是否需要修复？
- 需要。当前已达 strict gate，但离“稳定全 A”还有门槛，不应误判为封板。

3. 精确修复方法？
- 第一层（已完成）：修复门禁测试断言漂移，保证质量门禁改动可持续回归。
- 第二层（下一步）：针对 `Tools` 的低价值机会噪音（如 `Can't post poll`）补充内容守卫规则；针对 `Family` 的低样本短路补充采样深度兜底策略。

4. 下一步系统性计划是什么？
- 先做两件事再复验：
  - `content_guardrails` 增加通用“社区发帖权限/版务噪音”过滤，避免污染 pain/opportunity。
  - 为 `source_signal_volume` 极低场景增加通用二次扩采策略，减少 `scouting_brief` 的偶发回退。
- 然后再跑 `8 领域 x2` 复验，目标是“连续两轮全 A 或接近全 A 且无结构噪音”。

5. 这次执行的价值是什么？
- 这轮不是修补视觉层，而是把“是否稳定”用真实二轮 live 数据打实：
  - 拿到一次全 A
  - 同时抓到了回退根因
  - 为下一轮根治留下了可执行、可复验的收口路径。
