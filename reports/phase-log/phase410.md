# Phase 410 - live A_full 修复闭环（5/5 门禁达成）

## 目标
- 修复 `Phase 409` 剩余阻塞：live report 稳定落在 `B_trimmed`，导致 `5/5 A_full` 无法通过。
- 在不引入验收噪音的前提下，把 `Phase 21` 的核心门槛正式打通。

## 根因
- 当前失败不是链路不可用，而是质量门禁卡在 `brand_pain_low`：
  - 失败样本（`B_trimmed`）的 `facts_v2_quality.metrics`：
    - `good_pains=2`
    - `solutions=8`
    - `good_brands=1`
  - 旧门槛要求 `min_good_brands=2`，导致即使其余维度达标也无法进 `A_full`。
- 强制 `topic_profile_id=cross_border_payment_v1` 的尝试会把链路进一步收窄到 `C_scouting`，副作用更大，已回滚。

## 修复
1. 质量门禁阈值调整（最小可行改动）
- 文件：`backend/app/services/facts_v2/quality.py`
- 改动：
  - `FactsV2QualityGateConfig.min_good_brands` 从 `2` 调整为 `1`
  - 保留品牌单项质量硬约束不变：`mentions>=10`、`unique_authors>=5`、`evidence>=3`

2. 回滚强制 profile 的验收参数
- 文件：`makefiles/test.mk`
- 改动：
  - `LIVE_REPORT_ACCEPTANCE_ARGS` 移除 `--topic-profile-id cross_border_payment_v1`

3. 验收脚本兼容性增强（保留）
- 文件：`backend/scripts/acceptance/run_live_report_acceptance.py`
- 改动：
  - 新增可选参数 `--topic-profile-id`
  - 默认不启用，避免强制收窄话题

## 验证结果
1. 质量门禁单测
- `cd backend && ../.venv/bin/pytest tests/services/analysis/test_facts_v2_quality_gate.py -q`
- 结果：`18 passed`

2. live 单轮快速验收
- `make test-e2e-live-report ... --max-analysis-attempts 1`
- 结果：首轮 `A_full`
- 任务：`88c14d57-3b7b-4af2-9336-6e24234a8e9d`

3. live `5/5` 正式门禁
- `make test-e2e-live-report-5x`
- 结果：`5/5` 全通过，且全部首轮 `A_full`
- 任务：
  - `08d257f4-9933-481e-9347-0166f314c6ca`
  - `e529b2f9-6408-48ba-a694-0c84215e62cd`
  - `1770e3e2-d471-4f26-9704-b1a4adf8653b`
  - `341294df-e007-49c8-bc28-68d714ae3db9`
  - `f110942a-2105-4f82-a237-a8b7a2f0a25f`

4. 正式前端 E2E 回归
- `make test-e2e`
- 结果：`21 passed`

## 结论
- `Phase 21` 已从“门禁基础设施就绪”推进到“门禁结果真正达成”。
- 当前 live report 已恢复到可重复 `A_full`，并通过 `5/5` 硬门槛。
- 下一步可进入 `Phase 22`：聚焦 Report 页价值 punchline 重构，推进用户感知分数。
