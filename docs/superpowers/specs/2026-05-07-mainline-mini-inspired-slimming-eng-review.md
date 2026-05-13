# Eng Review: 主项目借鉴小程序机制瘦身
Date: 2026-05-07
Branch: feat/hotpost-cluster-aware-recall

## 状态

DONE_WITH_CONCERNS

## 范围挑战

### 1. 现有代码杠杆

已有模块已经覆盖第一刀要收的职责：

- `analysis_readiness_support.py`
  - `run_sample_guard_check`
  - `build_data_readiness_snapshot`
  - `build_insufficient_sample_artifacts`
- `analysis_remediation_support.py`
  - `schedule_auto_backfill_for_insufficient_samples`
  - `schedule_auto_backfill_for_missing_comments`
- `analysis_artifacts.py`
  - `build_sources_payload`
  - `build_facts_v2_package`
- `analysis_finalization_support.py`
  - `finalize_analysis_outputs`

所以不应该新建一套 parallel scanner service。

### 2. 最小变更集

第一刀只改：

- `backend/app/services/analysis/analysis_engine.py`
- `backend/tests/services/analysis/test_analysis_engine_readiness_delegation.py`（新）

可选补充：

- `backend/tests/services/analysis/test_analysis_readiness_support.py`
- `backend/tests/services/analysis/test_analysis_remediation_support.py`

不动：

- frontend
- DB schema
- report service
- Hotpost
- mini app

### 3. 复杂度检查

如果本轮超过 `3` 个生产文件，就是范围失控。目标是让 engine wrapper 委托已有模块，而不是引入新对象模型。

## 架构审查

目标数据流：

```text
run_analysis
  -> _run_sample_guard
       -> analysis_readiness_support.run_sample_guard_check
  -> _build_data_readiness_snapshot
       -> analysis_readiness_support.build_data_readiness_snapshot
  -> _build_insufficient_sample_result
       -> analysis_readiness_support.build_insufficient_sample_artifacts
  -> _schedule_auto_backfill_for_insufficient_samples
       -> analysis_remediation_support.schedule_auto_backfill_for_insufficient_samples
```

关键点：

- 保留 `analysis_engine.py` 旧 wrapper 名称，避免老测试 monkeypatch 断裂。
- support 模块负责真实逻辑。
- engine 只负责把 engine 常量 / `SessionFactory` / `_select_top_communities` 注入 support。

## 测试覆盖图

```text
代码路径覆盖
===========================
[+] analysis_readiness_support.py
├── [已测试] run_sample_guard_check 空输入返回 None
├── [已测试] run_sample_guard_check 转发 hot/cold/supplement 合同
├── [已测试] build_data_readiness_snapshot 汇总命中和缺失社区
└── [已测试] build_insufficient_sample_artifacts 保留 insufficient_samples 合同

[+] analysis_remediation_support.py
└── [已测试] schedule_auto_backfill_for_insufficient_samples 基础动作

[缺口] analysis_engine.py wrapper 是否真的委托 support
├── _run_sample_guard -> run_sample_guard_check
├── _build_data_readiness_snapshot -> build_data_readiness_snapshot
├── _build_insufficient_sample_result -> build_insufficient_sample_artifacts
└── _schedule_auto_backfill_for_insufficient_samples -> schedule_auto_backfill_for_insufficient_samples
```

必须补的测试：

- 新增 `backend/tests/services/analysis/test_analysis_engine_readiness_delegation.py`
- 用 monkeypatch 锁定 engine wrapper 调用 support 函数
- 断言 wrapper 输出仍符合 `AnalysisResult` / dict 合同

## 性能审查

第一刀不改变查询量。它只是把已有 engine 内联 SQL / scheduling 逻辑委托到 support。

注意点：

- `build_data_readiness_snapshot` 的 support 版本查的是 registry / membership / runtime state，不是旧 engine 版本的 `CommunityCache`。这可能是正确方向，但需要测试锁住输出字段一致。
- 如果后续要让 readiness snapshot 成为产品 gate，需要单独审 SQL 成本和索引，不在本轮完成。

## 风险

1. support 版本和 engine 旧版本数据源不同。
   处理：本轮只要求输出合同一致；数据源差异在报告中标记。

2. 老测试 patch 私有函数。
   处理：保留 wrapper 名称，不删除。

3. 自动 backfill 预算行为被误改。
   处理：本轮只委托 support，不调整预算默认值。

## 工程结论

可以进入实现计划，但第一刀必须非常窄：

```text
已存在 support 模块 -> engine wrapper 薄委托 -> 目标测试 -> 主线 smoke
```

不要新建轻扫描产品，不要重写 crawler，不要碰报告服务。
