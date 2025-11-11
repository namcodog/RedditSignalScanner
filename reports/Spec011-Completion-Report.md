# Spec 011 完成报告（语义集：建-测-用闭环）

日期：2025-11-10

## 目标与范围
- 建：历史语料 → 四层语义（L1–L4）→ 实体词典（brands/features/pain_points）
- 测：Hybrid 匹配 + 质量度量（覆盖、分层覆盖、Top10 占比、实体数）+ 质量门禁（含CI）
- 用：语义评分→社区池回灌（带轻权重排序）；报告薄接线（受控摘要供 010 消费）
- 不包含：用户端报告呈现/UI（归属 Spec 010）

## 实施与产出（代码与命令）
- 指标与门禁
  - calculate_metrics：`backend/scripts/calculate_metrics.py`（补充计数项与 layer-map 参数）
  - 质量门禁：`backend/scripts/semantic_acceptance_gate.py`（支持 features 可选校验、CI 判定）
  - Make 目标：`semantic-metrics`、`semantic-acceptance`
- 自动发布与治理
  - 自动发布：`make semantic-release-auto`（别名自适应高置信→品牌基线+锁痛点→多样化字典→门禁→可选报告/回灌）
  - Contrib 发布：`make semantic-release-contrib`（合并外部种子）
  - 周更治理：`make semantic-weekly-govern`（候选→别名高置信→黑名单候选→合并→门禁）
  - 回灌入口：`make semantic-refresh-cron`（评分→导入 pool，容错）
- 社区选择（轻权重排序，接口不变）
  - `backend/app/services/analysis_engine.py`：优先 crossborder:hybrid + score，高分先行，按 L1–L4 轮转均衡抽取
- 报告薄接线（供 010 消费）
  - 受控摘要模板：`backend/config/report_templates/executive_summary_v2.md`
  - 生成器：`backend/app/services/report/controlled_generator.py`
  - ReportService：将 Markdown 渲染为 HTML 注入 `report_html`；可选 `metrics_summary`
  - 路径可配：`SEMANTIC_LEXICON_PATH`、`SEMANTIC_METRICS_PATH`

## 关键指标（代表性一次，Contrib 发布）
- 文件：`backend/reports/local-acceptance/metrics/metrics_contrib.json`
- 结果：
  - overall_coverage: 0.8626（≥0.70 ✓）
  - brands: 0.6273（≥0.60 ✓）
  - pain_points: 0.5073（≥0.50 ✓）
  - top10_unique_share: 0.7916（∈[0.60,0.90] ✓）
  - 实体：100（✓）
- 门禁：`semantic_acceptance_gate.py` 返回 ok（CI 启用）

## 验收与复现步骤
1) 生成候选 + 指标
   - `make stage2-candidates`；`make semantic-metrics`
2) 自动发布（任选其一）
   - `make semantic-release-auto`
   - `make semantic-release-contrib`
3) 质量门禁（默认 CI 开启）
   - `make semantic-acceptance`
4) 报告（可选，供 010 消费）
   - `make stage3-report-generate` 或通过 Report API 读取 `report_html`
5) 回灌（可选）
   - `make semantic-refresh-cron`

## 配置与参数（可覆盖）
- 门禁：`SEMANTIC_GATE_ARGS=--use-ci`（默认）
- 别名自适应：`ALIAS_QUANTILE=0.95`、`ALIAS_MIN_FLOOR=0.90`
- 词典构建：`MIN_PAINS=55`、`MAX_BRANDS=30`、`ENABLE_ST_AUGMENT=0`
- 摘要资源路径：`SEMANTIC_LEXICON_PATH`、`SEMANTIC_METRICS_PATH`
- Layer 覆盖映射：`SEMANTIC_LAYER_MAP`（JSON/YAML）

## 风险与缓解
- 指标波动：启用 CI（Wilson 区间）判定 + 硬门禁，失败自动回退
- 头部挤占：品牌基线 + 锁痛点 + 多样化补齐 + 黑名单候选周更
- 回灌偏移：仅导入高分社区，engine 侧轻权重排序与层级均衡

## 后续建议（可选）
- TieredScheduler 引入“最近评分时间/分数”作为调度权重字段
- 将 ST 长尾增广默认化（资源允许时），由门禁兜底
- Admin/QA 侧仅保留下载与 API 调试，不做用户端指标呈现

---

> 本报告对应实现已写入代码与 Make 目标；所有产物与参数变更均记录于 `reports/phase-log/phase3.md`。
