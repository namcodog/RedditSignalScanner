# Phase 156 - Dev 报告产出修复（默认时间窗）

## 目标
- 在 dev 库跑通“产出报告”链路并定位阻塞点
- 对齐默认时间窗与 PRD（12 个月）

## 现状核查（dev）
- 任务：`28b1b5a0-2e10-494a-88c2-2a48e105b728`
- 结果：`insufficient_samples`，`min_required=1500`，`lookback_days=30`
- 样本来源：`hot_count=0`，`cold_count=11`，补充 search 14 条，剩余短缺 1486
- 关键原因：近 30 天 hot/cold 数据为 0 或极少

## 修复动作
- 将默认时间窗从 30 天调整为 12 个月（`SAMPLE_LOOKBACK_DAYS=365`，支持环境变量覆盖）
- 新增单测：验证无 topic_profile 时使用默认时间窗
- 文档对齐：PRD-03 与 PRD-SYSTEM 写明默认 12 个月时间窗

## 变更清单
- `backend/app/services/analysis_engine.py`：默认 `SAMPLE_LOOKBACK_DAYS=365`
- `backend/tests/services/test_analysis_engine.py`：新增默认时间窗测试
- `docs/PRD/PRD-03-分析引擎.md`：Step 2 时间窗口径
- `docs/PRD/PRD-SYSTEM.md`：报告顶部信息时间窗口径

## 测试
- `pytest tests/services/test_analysis_engine.py -k "default_sample_lookback_days"`（`SKIP_DB_RESET=1`）✅

## 复测（dev / 8011）
- 任务：`27014e57-b45d-433a-ac77-875eff7659bb`
- 状态：completed（不再触发 sample_guard）
- `lookback_days=365` 生效
- `report_tier=X_blocked`，`analysis_blocked=quality_gate_blocked`
- 质量门禁原因：`topic_mismatch` + `pains_low` + `brand_pain_low`
- 结论：时间窗修复后“样本不足”不再阻塞，但 dev 数据与输入主题不匹配，导致质量门禁拦截

## 下一步
1. 选用匹配 topic_profile 或导入相关社区池
2. 对匹配社区执行抓取/回填，确保有足够 on-topic 样本
3. 再跑一次 dev 报告验收，目标为非 X_blocked 的完整报告
