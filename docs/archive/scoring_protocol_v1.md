# DEPRECATED

> 本文档已归档，不再作为当前口径。请以 docs/2025-10-10-文档阅读指南.md 指定的文档为准。

# Scoring Protocol v1（事实与评分分层）

> 目的：把 LLM 语义结果、规则计算和落库字段说明白，确保 post_scores / comment_scores、content_labels / content_entities 的字段含义一致、可回溯。

## 字段定义

- sentiment：情绪分，范围 -1.0~1.0，来源 LLM 或规则回填。
- content_type：post 或 comment，用于 content_labels / content_entities 区分目标类型。
- actor_type：发声人角色（如 buyer/seller/neutral），由 LLM 提取或规则推断。
- main_intent：主意图标签（如 ask_help/share_experience/review），LLM 提取。
- pain_tags：痛点标签列表，写入 content_labels（category=pain，aspect=标签名）。
- aspect_tags：维度标签列表（如 quality/logistics/pricing），写入 content_labels.aspect。
- entities：实体列表（brand/product/channel 等），写入 content_entities（entity_type 指示类型）。
- crossborder_signals：跨境相关标记（如 region/payment/logistics），来源 LLM 或规则。
- purchase_intent_score：购买/行动意向分，0-10，可选字段。
- value_score：价值分，0-10，规则引擎计算的主分数。
- opportunity_score：机会分，0-10，规则引擎结合模板/权重计算。
- business_pool：core/lab/noise，用于冷热池归类，规则引擎给出。

## 入库约定

- 评分结果落 *_scores：post_scores / comment_scores。
- 语义标签落 content_labels（pain/aspect/sentiment 等）、content_entities（实体）。
- is_latest=true 代表当前有效版本；rule_version 标明使用的规则集（例如 rulebook_v1）。
- llm_version 记录调用的模型名（如 gemini-1.5-flash）。

## YAML 版本标记

- scoring_rules.yaml：rule_version=rulebook_v1（机会评分权重、估计参数）。
- scoring_templates.yaml：rule_version=rulebook_v1（正负模板、pattern 权重）。
- crossborder_scoring.yml：rule_version=rulebook_v1（跨境场景权重/门禁）。
- thresholds.yaml：rule_version=rulebook_v1（全局阈值）。
- 词典类：community_roles.yaml、vertical_overrides.yaml、pain_dictionary.yaml、entity_dictionary.yaml、aspect_keywords.yml 保持与 rulebook_v1 对齐，如有变更需 bump 版本。

## 校验清单（只读 SQL）

- 重复最新检查：
  - `SELECT post_id, COUNT(*) FROM post_scores WHERE is_latest GROUP BY post_id HAVING COUNT(*)>1;`
  - `SELECT comment_id, COUNT(*) FROM comment_scores WHERE is_latest GROUP BY comment_id HAVING COUNT(*)>1;`
- 覆盖率：
  - 评论标签覆盖率：`SELECT COUNT(*) AS total, COUNT(DISTINCT content_id) FILTER (WHERE content_type='comment') AS labeled FROM content_labels;`
  - 帖子标签覆盖率同理，实体表也做一次。
- 空标签检查：
  - `SELECT COUNT(*) FROM post_scores WHERE is_latest AND (tags_analysis='{}'::jsonb OR tags_analysis IS NULL);`（评论同理）。
- 版本分布：
  - `SELECT rule_version, COUNT(*) FROM post_scores GROUP BY rule_version;`（评论同理）。

## 变更策略（迁移口径）

- 旧分数仍在 posts_raw/comments：保持只读，迁移后停写，最终下线。
- 新分数：只写 *_scores，严格过滤 is_latest=true + 指定 rule_version 供报表使用。
- 若需要版本对比，查同一 post_id/comment_id 的多条记录，不回填到事实表。
