# Implementation Plan: 分析报告主线与生成优化（Spec 015）

**Branch**: `015-report-mainline-and-t1-pipeline` | **Date**: 2025-11-22 | **Spec**: [015-分析报告主线与生成优化.md](./015-分析报告主线与生成优化.md)

## Summary

本计划围绕 Spec 015，落地一条清晰的“分析报告主业务线”说明，并在其之上实现 Stats Layer、Clustering Layer 和 Report Agent 三层大脑，用于恢复和固化 T1 价值报告的生成能力。执行顺序遵循“先主线认知 → 再数据就绪 → 再统计 → 再聚类 → 最后接回主线”的原则。

## Phases

### Phase 0: 主线确认与文档落地（认知对齐）

**目标**: 所有人能在一份文档中看清 `/api/analyze → analysis_task → analysis_engine → report_service → /api/report` 的唯一主业务线，以及与之强相关的数据准备白名单。

- 输出物:
  - `docs/archive/2025-11-主业务线说明书.md`（或同等命名）
  - Spec 015 下的 `plan.md` / `tasks.md` 初始化

### Phase 1: 数据就绪与 Stats Layer（数据基础）

**目标**: 确认/恢复 T1 社区 + 12 个月数据，并在其之上实现一个可重复调用的统计层，为后续聚类和报告生成提供“硬指标”输入。

- 输出物:
  - T1 社区和 12 个月窗口的数据检查报告（可记入 `reports/phase-log/`）
  - Stats Layer 模块（服务或脚本）
  - `reports/local-acceptance/t1-stats-snapshot.json`

### Phase 2: Clustering Layer（痛点聚类）

**目标**: 用已有 `content_labels`/`content_entities` 把 PAIN 评论聚成 3–5 个痛点簇，为报告中的“痛点章节 + 驱动力”提供结构。

- 输出物:
  - Clustering 模块（服务或脚本）
  - `reports/local-acceptance/t1-pain-clusters.json`

### Phase 3: Report Agent（T1 报告生成器）

**目标**: 基于 Stats + Clustering 输出，用 LLM/模板生成一份结构对齐 `reports/t1价值的报告.md` 的 Markdown 报告。

- 输出物:
  - Report Agent 模块
  - CLI 命令（如 `make t1-report-demo`）
  - `reports/t1-auto.md`（自动生成的 T1 报告示例）

### Phase 4: 接入主业务线与配置开关（可选升级）

**目标**: 在不破坏现有技术版报告的前提下，将 Report Agent 接入 `/api/report` 主线，通过配置开关控制“市场版/T1 报告模式”。

- 输出物:
  - ReportService 中新的“market/T1 模式”分支
  - 配置项梳理与说明（`ENABLE_MARKET_REPORT` / `REPORT_MODE`）
  - Spec 008/010/013 中对报告生成部分的引用更新

