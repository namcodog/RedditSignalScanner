# Phase 3 — Spec 011 桥接修复记录（语义门禁 / 受控摘要 / 回灌）

日期：{DATE}

## 本次变更概览
- 语义质量门禁落地（Make 目标 + 脚本 + 阈值配置）
- 受控摘要 v2 接入 Report API（后端生成 Markdown，前端展示）
- 语义→社区池手动串联（Hybrid 评分导入 DB Pool）

## 统一反馈四问
1) 发现了什么问题/根因？
- 语义指标仅供查看，未进入流水线门禁；
- 语义评分未回灌到社区池/Tier；
- 报告端未直接食用“语义指标/层级覆盖”的受控摘要。

2) 是否已精确定位？
- 是。已在如下代码位对接：
  - 门禁：`backend/scripts/semantic_acceptance_gate.py` + `backend/config/quality_gates/semantic_thresholds.yml`
  - 摘要：`backend/app/services/report_service.py` 内构建 `report_html`（受控摘要 v2 模板）
  - 回灌：`backend/scripts/score_with_hybrid_reddit.py` → `backend/scripts/import_hybrid_scores_to_pool.py`

3) 精确修复方法？
- 新增 Make 目标：
  - `semantic-metrics`：生成 JSON/CSV 指标
  - `semantic-acceptance`：按阈值断言（不达标退出 1）
  - `semantic-refresh-pool`：Hybrid 评分→导入 pool（手动串联）
- ReportService：若模板/指标存在则生成受控摘要 Markdown 写入 `report_html`，否则回退旧内容。
- 阈值可在 `backend/config/quality_gates/semantic_thresholds.yml` 或环境变量覆盖。

4) 下一步做什么？
- 和产品/算法确认门禁阈值（当前为建议默认）；
- 决定受控摘要在前端的呈现方式（当前直接显示 Markdown 文本，后续可上 Markdown 渲染）；
- 是否将 `semantic-refresh-pool` 纳入定时任务；
- 观察门禁后续对抓取/报告稳定性的影响，必要时微调阈值。

5) 修复效果与结果
- 任何不达标的语义集会被门禁阻断，避免低质词库进入抓取/报告；
- 受控摘要随报告输出，前端直接可读；
- 语义评分可一键导入社区池，TieredScheduler 可用其结果调度抓取。

## 变更明细
- 新增
  - `backend/scripts/semantic_acceptance_gate.py`
  - `backend/config/quality_gates/semantic_thresholds.yml`
  - `backend/scripts/import_hybrid_scores_to_pool.py`
  - `backend/tests/quality/test_semantic_acceptance_gate.py`
- 修改
  - `backend/app/services/report_service.py`：生成 `report_html`（受控摘要）
  - `frontend/src/pages/ReportPage.tsx`：在摘要卡片显示 `report_html`
  - `Makefile`：`semantic-metrics` / `semantic-acceptance` / `semantic-refresh-pool`

## 验收命令（本地）
- 语义门禁
  - `make semantic-acceptance`
  - 覆盖阈值（示例）：`SEMANTIC_THRESHOLDS_YML=path/to/override.yml make semantic-acceptance`
- 报告受控摘要（需已有分析产物）
  - 后端启动并生成报告后，调用报告 API，响应体字段 `report_html` 应包含“执行摘要（基于四层语义分析）”标题。
- 回灌串联
  - `make semantic-refresh-pool`
  - 观察输出 `✅ Imported hybrid scores → pool`，并在 DB `community_pool` 表看到相应 upsert。

## 本次自动发布结果（零人工校准）
- 使用 brands 基线 + 锁定痛点槽位（min_pains=55, max_brands=30）构建实体词典：
  - 脚本：`backend/scripts/filter_and_refill_entity_dict.py --brands-base backend/config/entity_dictionary/brands_base.csv --min-pains 55 --max-brands 30`
  - 产物：`backend/config/entity_dictionary/crossborder_v2_diverse.csv`
- 指标（entity-metrics_brandsbase2.csv）：
  - overall_coverage: 0.8626（≥0.70 ✓）
  - brands: 0.6273（≥0.60 ✓）
  - pain_points: 0.5073（≥0.50 ✓）
  - top10_unique_share: 0.7916（∈[0.60,0.90] ✓）
- 质量门禁：`backend/scripts/semantic_acceptance_gate.py` → "ok"（已通过）

## 风险与回退
- 若门禁阈值过严导致频繁阻断，可临时放宽 `semantic_thresholds.yml` 或通过环境变量覆盖；
- 受控摘要生成失败时自动回退到旧的 `analysis.report.html_content`；
- 回灌脚本仅追加/更新 `community_pool`，不涉及破坏性删除。

---

> 注：本页为阶段产出记录的一部分，配合 `docs/2025-10-10-实施检查清单.md` 更新进度。
