# PRD-01: 数据模型设计（后端现状对齐版）

## 1. 问题陈述

### 1.1 背景
当前系统已从“极简四表”演进为**完整的数据采集→清洗→评分→事实→报告**流水线。文档需要以本地实现为准，避免“说明书与现货不一致”。

### 1.2 目标
- **以实现为真相**：字段/表/约束以 `current_schema.sql` 与 DB Atlas（SOP 版本）为准。
- **支撑全链路**：抓取、缓存、清洗、打分、事实门禁、报告出数。
- **可追溯**：有 run_id / audit 记录，能还原每次数据来源。
- **可演进**：保留候选/统计/语义资产扩展空间。

### 1.3 非目标
- 不做复杂社交关系图谱（仅围绕内容与社区）。
- 不承诺“纯实时”，以缓存优先 + 受控补抓为主。
- 不在 PRD 里枚举所有 SQL 细节（细节以 DB Atlas 为准）。

---

## 2. 解决方案

### 2.1 核心设计：多域数据模型（实际已落地）

为保证读者“看完能对上库”，按领域拆成 8 组：

1) **用户与任务**
- `users`, `tasks`, `analyses`, `reports`, `insights`, `beta_feedback`
- 说明：任务与分析/报告 1:1；`analyses.insights` 为算法结论，供 LLM 报告主线使用。
  - 必含字段：`trend_summary` / `market_saturation` / `battlefield_profiles` / `top_drivers`
  - 既有字段：`pain_points` / `competitors` / `opportunities` / `action_items` / `entity_summary`

2) **抓取与缓存**
- `crawler_runs`, `crawler_run_targets`, `community_cache`, `posts_hot`, `posts_latest_v`
- 说明：run 级可追溯，缓存由 `community_cache` + 热表承载。

3) **原始内容（冷库）**
- `posts_raw`（SCD2：`version/is_current/valid_from/valid_to`）
- `comments`, `authors`, `posts_quarantine`, `posts_archive`
- 说明：入库触发器清洗；去重以“后置标记”为主。

4) **评分与标签**
- `post_scores`, `comment_scores`, `post_semantic_labels`, `post_embeddings`
- `content_labels`, `content_entities`, `noise_labels`, `mv_*` 视图
- `semantic_main_view`（语义单一真相视图，统一 tags/labels/entities）
- 说明：入库粗分 + 规则评分 + 语义标签分层并存。

5) **社区池与发现**
- `community_pool`, `discovered_communities`, `tier_suggestions`, `tier_audit_log`, `community_import`
- 说明：发现 → 验毒 → 评估 → 入池，带黑名单与健康状态。

6) **事实与审计**
- `facts_snapshot`, `facts_run_log`, `data_audit_events`, `system_health`
- 说明：facts_v2 门禁与审计记录只认落库事实。

7) **语义资产**
- `semantic_rules`, `semantic_candidates`, `semantic_terms`, `semantic_audit_log`
- 说明：候选词、规则库、人工审核记录已落库。

8) **决策单元与反馈（平台级中间产物）**
- `decision_units_v`（对外稳定门面）
- `decision_unit_feedback_events`（append-only 反馈事件）
- `insight_cards`（kind=decision_unit 的承载表）
- `evidences`（已扩展 `content_type/content_id` 用于可追溯证据链）

> **完整字段清单**：见 `docs/sop/2025-12-14-database-architecture-atlas.md`，哈希见 `docs/PRD/PRD-SYSTEM.md` 附录。

---

## 3. 数据流（现实版本）

### 3.1 用户分析链路
```
用户输入 → tasks → analyses → reports
           ↓
     analysis_engine 读取 posts_raw / post_scores / community_pool
```

### 3.2 抓取链路（后台）
```
community_pool → crawler_runs/targets → posts_raw/comments
           ↓
    清洗/去重 → post_scores/comment_scores
           ↓
      facts_v2 门禁 + 证据切片 → LLM 报告 → reports/insights
```

---

## 4. 关键口径（避免误读）
- **唯一真相**：`current_schema.sql` + DB Atlas（SOP 版本）。
- **SCD2 已启用**：`posts_raw` 不是“只保当前”，历史版本已落库。
- **清洗/打分口径**：以 `docs/sop/数据清洗打分规则v1.2规范.md` 为准。
- **facts_v2 门禁**：以 `docs/sop/2025-12-13-facts-v2-落地SOP.md` 为准。

---

**文档状态**：已按统一口径更新（LLM 报告必经）。
