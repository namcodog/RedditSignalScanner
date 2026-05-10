# phase76 - facts_v2 门禁（无 topic_profile 也触发）

## 目标
- 让 facts_v2 门禁在无 topic_profile 的场景也能触发
- 避免“该刹车时没刹车”
- 让拦截提示文案在无 profile 时不误导

## 发现的问题 / 根因
- 只有在有 topic_profile 时才构建 facts_v2 包并触发门禁，导致无 profile 的任务直接跳过门禁。

## 精确定位
- `backend/app/services/analysis_engine.py` 门禁逻辑依赖 topic_profile
- `backend/app/services/facts_v2/quality.py` 主题匹配在无 profile 时需要明确跳过

## 修复方法
- `quality_check_facts_v2` 新增 `skip_topic_check`：无 profile 时跳过主题匹配，但仍走完整度/一致性门禁。
- `run_analysis` 无论是否有 profile 都构建 facts_v2 包并执行门禁。
- `X_blocked` 提示文案：无 profile 时不再提示更换 topic_profile_id。
- 调整快速测试用例：根据 report_tier 允许空洞洞察。

## 影响范围
- facts_v2 门禁在全量任务上生效（含无 topic_profile 的任务）。

## 测试
- `python -m pytest backend/tests/services/test_facts_v2_quality_gate.py`
- `python -m pytest backend/tests/services/test_analysis_engine.py::test_run_analysis_fast_with_mocked_database`
- `python -m pytest backend/tests/services/test_analysis_engine.py::test_run_analysis_applies_facts_v2_quality_gate_without_topic_profile`
- `python -m pytest backend/tests/services/test_analysis_engine.py::test_run_analysis_applies_facts_v2_quality_gate_with_topic_profile`

## 结果
- 门禁在无 topic_profile 时可触发，且跳过主题匹配不误伤；拦截提示更符合真实情境。
