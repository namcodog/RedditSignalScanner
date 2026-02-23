# Phase 98 - SOP 同步校准（抓取链路/清洗打分）

日期：2025-12-23

## 背景
对齐“数据抓取系统SOP v3.2”和“数据清洗打分规范 v1.2”与当前生产库/代码现状，避免文档超前或口径不一致。

## 变更摘要
- 更新 `docs/sop/数据清洗打分规则v1.2规范.md`
  - 修正 DB Atlas 路径为 `docs/sop/2025-12-14-database-architecture-atlas.md`
  - 补充抓取侧默认输入边界：spam 默认 tag、评论回填默认 smart_shallow 参数
  - 明确 facts_v2 门禁文档入口
- 更新 `docs/sop/数据抓取系统SOP_v3_修正版_v3.2.md`
  - 语义回流改为“现状只有 semantic_rules + evidence_posts（探针审计）”，证据/统计表标记为规划
  - 任务链改为当前已落地任务（extract_candidates/tag_post_semantics）
  - 增量评论回填默认参数补充
  - 垃圾/重复默认策略明确为 tag

## 影响范围
仅文档更新，不改代码与数据库。

## 验证
- 对照 `current_schema.sql` 与 backend 代码检索确认字段/任务现状一致。


## 2025-12-25 追加
- 修正两份文档的日期为 2025-12-25。
