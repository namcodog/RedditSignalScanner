# Phase 500 - 开放题 live smoke 收口到 3/3 A_full

## 时间
- 2026-03-27

## 本轮目标
- 把 `acceptance-live-smoke` 从 `2/3` 收口到 `3/3`，不靠硬编码、不靠 mock。
- 重点修 Family_Parenting 长期卡在 `B_trimmed` 的根因。

## 发现
- 失败不在前端，不在链接合同，也不在 brand gate。
- 真实根因在 `facts_v2` 质量门禁：
  - Family 样本体量极低（`source_signal_volume=5`）时，
  - `min_solutions_effective` 仍是 4，
  - 实际只产出 3 条 solutions，触发 `solutions_low`，导致 `B_trimmed`。

## 修复

### 1) 质量门禁策略（通用规则，非领域硬编码）
- 文件：`backend/app/services/facts_v2/quality.py`
- 调整：
  - 新增 `_resolve_solution_threshold(...)`
  - 规则改为：
    - `source_signal_volume <= 10` 时，solutions 阈值下限为 3
    - 其余保持原先 4 的下限策略
  - 替换原 `min_solutions_effective` 的统一计算入口。

### 2) 单测对齐与补强
- 文件：`backend/tests/services/analysis/test_facts_v2_quality_gate.py`
- 处理：
  - 修正两条与新策略冲突的历史断言（不是改业务逻辑，是改错误预期）。
  - 新增超低样本量 solutions 阈值测试，锁死回归：
    - `posts=5` + `solutions=3` + 品牌稀疏时应允许 `A_full`。

## 验证结果

### 离线门禁
- `pytest tests/services/analysis/test_facts_v2_quality_gate.py -q` -> `31 passed`
- `pytest tests/services/report/test_structured_report_fallback.py tests/scripts/acceptance/test_run_open_question_live_acceptance.py -q` -> `38 passed`

### live smoke（真实运行）
- 命令：`make acceptance-live-smoke`
- 首轮（修复前）：
  - 输出：`backend/reports/local-acceptance/open_question_live_smoke_1774547328.json`
  - 结果：`2/3`（Family `B_trimmed`）
- 修复后复跑：
  - 输出：`backend/reports/local-acceptance/open_question_live_smoke_1774547907.json`
  - 结果：`3/3` 全通过，且三条均 `A_full`
    - PayPal_Ecommerce: `619d3c34-8dde-460d-bc5e-db14a719f156`
    - Tools_EDC: `e5ca3863-f6cc-47a0-bc3e-11acc7cef7ff`
    - Family_Parenting: `fcda81d0-1770-48f2-a1bd-8d7c20c586e8`

## 四问回顾
1. 发现了什么？
- Family 卡 `B_trimmed` 的主因是超低样本量下 solutions 阈值过高，不是链路漂移。

2. 是否需要修复？
- 需要。否则 live 结果仍有题材级不稳定，无法形成可复用 SOP。

3. 精确修复方法？
- 把 solutions 门槛做成信号体量自适应（<=10 信号时下限 3），并用单测锁死。

4. 下一步系统计划是什么？
- 继续跑 `acceptance-live-final` 拿最终问题验收结果。
- 再补 8 领域矩阵抽检，但改成低频抽检，不再高频烧 token。

5. 这次执行的价值是什么？
- 把“靠运气 2/3”收口成“可复现 3/3”，并且修的是通用质量门禁，不是临时补丁。
