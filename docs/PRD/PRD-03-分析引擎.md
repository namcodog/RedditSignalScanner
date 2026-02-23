# PRD-03: 分析引擎设计（后端现状对齐版）

## 1. 问题陈述

### 1.1 背景
系统承诺“5 分钟内输出可用报告”，前提是**缓存优先**，并且所有质量判断可追溯。分析引擎必须在“可控样本量”和“可解释输出”之间做平衡。

### 1.2 目标
- **缓存优先**：目标 90% 数据来自缓存。
- **社区池驱动**：基于 `community_pool` 与 topic_profile 选社区。
- **信号可解释**：痛点/竞品/机会三类信号输出结构化。
- **质量门禁**：facts_v2 做分级输出（B_trimmed / C_scouting / X_blocked）。
- **LLM 必经**：最终报告必须由 LLM 生成（输入=insights 主线 + facts_v2 证据切片）。
- **可追溯**：分析过程写入 `analyses` / `reports` / `facts_snapshot`。
- **可复用中间产物**：DecisionUnit 作为平台级可复用输出。

### 1.3 非目标
- 不做实时流式 NLP；以批处理为主。
- 不承诺“全社区覆盖”；优先可控质量。
- 不在引擎内做 Admin 人工流程。

---

## 2. 解决方案（实际流水线）

### Step 1：选社区（社区池 + 主题画像）
- 主要来源：`community_pool`（按 priority/tier 选取）。
- 约束：若命中 topic_profile，则按 profile 过滤/扩展社区。
- 补充：不足时从搜索/发现结果补齐，并写回 `discovered_communities` 便于复盘。

### Step 2：数据采集（缓存优先 + 受控补抓）
- 主要来源：Redis/热表缓存 + `community_cache`。
- 补抓来源：Reddit API（受 `reddit_rate_limit` 限制）。
- **混合检索增强**：关键词检索 + 向量检索（pgvector）合并召回池，补足“关键词命中但语义不准”的盲区。
- **向量写入自动化**：`embeddings-backfill-posts/comments` 周期补齐（Celery beat，默认开启；可用 `EMBEDDING_BEAT_ENABLED=0` 关闭）。
- 降级策略：API 失败则进入 cache-only；必要时可降级到 mock（仅在允许开关下）。
- 时间窗默认 **12 个月**（`SAMPLE_LOOKBACK_DAYS=365`），topic_profile 的 `preferred_days` 可覆盖。

### Step 3：清洗与信号提取
- 去重：后置去重（`deduplicate_posts`）+ **向量相似度去重**，防一稿多投污染报告。
- 评分：使用 `post_scores` + 业务池权重，识别 noise/core/lab。
- 信号：痛点/竞品/机会 + 实体抽取（`EntityPipeline`）。
- **insights 定义**：算法结论（痛点/竞品/机会/行动项/实体榜单），是 LLM 报告的主线输入。
- **insights 必须完整**：趋势/战场画像/驱动力/饱和度必须由算法产出，不允许 LLM 自行补脑。
- 语义口径：统一读取 `semantic_main_view`，避免多口径分裂。
- **口径对齐**：清洗/评分规则以 `docs/sop/数据清洗打分规则v1.2规范.md` 为唯一真相。

### Step 4：facts_v2 质量门禁
- 生成 `facts_v2_package`，执行 `quality_check_facts_v2`。
- facts_v2 作为“证据包 + 门禁 + 审计包”，会被裁剪为 `facts_slice` 供 LLM 使用。
- 输出分级：
  - `B_trimmed`：保守输出（裁剪）
  - `C_scouting`：侦察态（短报告）
  - `X_blocked`：拦截（只给建议，不给结论）
- 门禁结果写入 `sources.facts_v2_quality` + `facts_snapshot`。

### Step 5：报告生成与落库
- **LLM 必经**：报告由 LLM 生成（insights 主线 + facts_slice 证据）。
- 若 `C_scouting/X_blocked`：只输出解释/下一步动作，不生成完整报告正文。
- 结构化结果写入 `analyses`，HTML 报告写入 `reports`。
- `report` 返回 `report_html + report + metadata + overview + stats`。
- **report 关键字段（前端直用）**：
  - `report.pain_points[].title/text`、`report.opportunities[].title/text`（后端补齐）
  - `report.action_items[].title/category`（category 默认 `strategy`）
  - `report.purchase_drivers`（来源 `insights.top_drivers`）
  - `report.market_health`（饱和度 + P/S；`ps_ratio` 口径：facts_slice 优先，sources.ps_ratio 兜底）

### Step 5.1：insights 全量结构（必须输出）
> 说明：这是“算法结论层”，必须完整输出，LLM 只负责表达。

- `trend_summary`：需求趋势结论 + 依据（热度/场景/时间窗）
- `market_saturation`：竞争饱和度结论 + 依据（品牌密度/讨论集中度）
- `battlefield_profiles[]`：战场画像（社区组/画像/痛点/策略/证据）
- `top_drivers[]`：购买驱动力（标题/解释/行动建议）
- 既有字段继续保留：
  - `pain_points` / `competitors` / `opportunities`
  - `action_items` / `entity_summary` / `pain_clusters`
  - `competitor_layers_summary` / `channel_breakdown`

### Step 5.2：facts_slice（供 LLM 证据输入）
- 来源：`facts_v2_package` 裁剪版（聚合 + 证据样本 + 门禁结论）
- 必含：`aggregates` / `data_lineage` / `sample_posts_db` / `sample_comments_db` / `facts_v2_quality`

### Step 5.3：知识骨架 JSON（UI 只读）
- 固定结构：**社区 → 痛点 → 证据 → 场景/驱动力**
- 入口字段：`sources.knowledge_graph`（同时写入 `facts_slice.knowledge_graph`）
- 用途：前端按结构化 JSON 渲染，不再二次“脑补”。

### Step 6：DecisionUnit 产出（平台级中间产物）
- 由 `insight_cards` 承载（`kind=decision_unit`），对外读口径为 `decision_units_v`。
- 反馈走 `decision_unit_feedback_events`（append-only）。
- ops 侧可由 tier_suggestions 生成 DecisionUnit（见 Phase107）。

---

## 3. 关键口径（避免误解）
- **缓存命中率**：以 `sources.cache_hit_rate` 为准。
- **社区来源**：`sources.seed_source` 标注 pool 或 pool+discovery。
- **门禁是否触发**：看 `sources.facts_v2_quality` 与 `sources.report_tier`。
- **insights 是结论**：算法产出的结论结构，供 LLM 组织报告。
- **facts_v2 是证据**：门禁/审计/证据包，LLM 只读切片，不直接吃全量包。
- **样本不足**：会进入 C/X 降级，不是“成功报告”。
- **sources 账本**：`GET /api/tasks/{task_id}/sources` 为用户侧解释来源。

---

**文档状态**：已按统一口径更新（LLM 报告必经）。
