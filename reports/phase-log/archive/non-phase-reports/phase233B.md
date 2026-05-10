# Phase 233B — hotpost 爆帖子系统深度诊断（2026-03-05）

## 背景
hotpost 是一个独立的实时"爆帖检测+分析"子系统，12 个 service 文件 + 2 个 model + 1 个 schema + 1 个 API endpoint + 2 个运维脚本。本次用 Serena 做完整的业务逻辑梳理。

---

## 1. 系统定位

> hotpost = **实时热点帖检测 + 信号分类 + LLM 深度分析 + 结构化输出**

与主分析引擎 (`analysis_engine.py`) 的区别：
- **主引擎**: 批量、异步、Celery 调度、以 topic/品类为中心
- **hotpost**: 实时、API 驱动、以查询词为中心、面向前端即时响应

---

## 2. 完整管线 (8 阶段)

```
用户查询 → ① 查询解析 → ② 缓存检查 → ③ Reddit 搜索
         → ④ 信号检测 → ⑤ 评论抓取 → ⑥ LLM 深度报告
         → ⑦ 模式富化 → ⑧ 缓存 + 持久化
```

### ① 查询解析 (`query_resolver.py`)
- CJK 检测 (`_contains_cjk`) → 中文查询自动走 LLM 翻译
- 输出: `HotpostQueryResolution(search_query, keywords, subreddits, source)`
- 长查询自动拆分 (max 50 chars/part, max 3 splits)

### ② 缓存检查 (`cache.py`)
- Key: `hotpost:search:{hash(query+mode+subreddits)}`
- TTL: 按 mode 动态计算 (`get_hotpost_cache_ttl_seconds`)
- 命中 → 直接返回 `HotpostSearchResponse(from_cache=True)`

### ③ Reddit 搜索 (`service.py → _search_subreddit_posts`)
- 无指定社区时: 先搜社区建议 (limit=5), 再按社区搜帖
- 有指定社区时: 直接按社区搜帖
- 去重: `seen_post_ids` set
- 限制: `max_posts_per_sub = min(100, max(30, request.limit))`

### ④ 信号检测与过滤 (`rules.py`)
- **三检测器**, 全部由 YAML 词典驱动 (`keywords.py → HotpostLexicon`):

| 模式 | 检测器 | 信号分组 | 过滤逻辑 |
|------|--------|---------|----------|
| `rant` | `detect_rant_signals` | strong / medium / weak | 必须命中至少一个信号 |
| `opportunity` | `detect_opportunity_signals` | seeking / unmet_need / resonance | 必须命中 + 关键词相关性过滤 |
| `trending` | `detect_discovery_signals` | positive / hidden_gem | 不强制过滤 (全过) |

- **评分公式**: `signal_score = total_signals × 10 + (score + num_comments × 2) × 0.01`
- **分类**: `classify_pain_category(text, lexicon)` → 痛点类别标签
- **情绪**: `_sentiment_label(mode, text, signals)` → positive/neutral/negative

### ⑤ 评论抓取 (`service.py → _fetch_comments`)
- 对 top 30 帖子逐个抓评论
- 评论写入 Redis: `hotpost:comments:{query_id}`, TTL = `COMMENTS_TTL_SECONDS`
- 同时持久化到 DB: `evidence_post` + `query_evidence_map` (含 rank + signal_score + top_comment_refs)

### ⑥ LLM 深度报告 (`report_llm.py`)
- **入口**: `generate_hotpost_llm_report()`
- **流程**: `render_hotpost_prompt()` → LLM generate (JSON mode) → `sanitize_llm_report()`
- **提示模板**: `prompts.py` 中按 mode 存 3 套 (TRENDING_PROMPT / RANT_PROMPT / OPPORTUNITY_PROMPT)
- **模型**: `settings.llm_model_name` (Grok-4.1)
- **守卫**: `enable_llm_report` env var + API key 检查 + evidence_count > 0
- **合并**: `merge_hotpost_llm_report()` 将 LLM 字段合入主响应 + `apply_hotpost_llm_annotations()` 补充标注

### ⑦ 模式富化 (`enrichment.py` + `detail_builder.py`)
- **rant 模式**:
  - `enrich_rant_payload` → 补充 category_counts, user_quotes
  - `extract_competitor_mentions` → 竞品提及
  - `classify_intent_label` → 迁移意图 (already_left / considering / staying_reluctantly)
  - `build_top_rants` → top rant 帖子
  - `migration_intent.destinations` → 竞品流向
- **opportunity 模式**:
  - `enrich_opportunity_payload` → 补充 me_too_count
  - `opportunity_strength`: weak (<10 帖) / medium (10-19 帖) / strong (≥20 帖 + ≥5 me_too)
  - `build_top_discovery_posts` → top 发现帖

### ⑧ 缓存 + 持久化
- **Redis 多键缓存**:
  - `hotpost:search:{hash}` → 完整响应 (去重主键)
  - `hotpost:result:{query_id}` → 按 query_id 检索
  - `hotpost:llm_report:{query_id}` → LLM报告单独缓存
  - `hotpost:comments:{query_id}` → 评论缓存
- **DB 持久化**:
  - `hotpost_queries` 表 → `create_hotpost_query` / `update_hotpost_query`
  - `evidence_posts` 表 → `upsert_evidence_post`
  - `hotpost_query_evidence_map` 表 → `insert_query_evidence_map`
  - `maybe_discover_community` → 自动发现新社区

---

## 3. API 端点 (4 个)

| 端点 | 方法 | 功能 |
|------|------|------|
| `hotpost_search` | POST | 主搜索入口 → `HotpostService.search()` |
| `hotpost_result` | GET | 按 `query_id` 获取结果 |
| `hotpost_stream` | GET(SSE) | 队列位置实时推送 |
| `hotpost_deepdive` | POST | 深度分析 (复用已有数据) |

---

## 4. 队列管理 (`queue.py`)

`HotpostQueueTracker` 基于 Redis:
- `mark_processing()` → `mark_waiting()` → `mark_completed()` / `mark_failed()`
- 前端通过 SSE (`hotpost_stream`) 实时轮询队列状态
- 用途: 当多用户并发查询时，给用户"排队中"的反馈

---

## 5. 运维脚本 (2 个)

| 脚本 | 功能 |
|------|------|
| `warmup_hotpost_cache.py` | 预热高频查询缓存 |
| `export_hotpost_report.py` | 导出 Markdown 报告 |

---

## 6. 文件清单 (12 service + 6 infra)

| 文件 | 行数(约) | 职责 |
|------|---------|------|
| `service.py` | ~924 | 核心编排: search() 主方法 |
| `rules.py` | ~100 | 信号检测: rant/opportunity/discovery |
| `report_llm.py` | ~420 | LLM 报告: prompt → generate → sanitize |
| `cache.py` | ~40 | 缓存键计算 + TTL |
| `queue.py` | ~80 | Redis 队列位置跟踪 |
| `detail_builder.py` | ~100 | 详情构建: rant intensity, competitor |
| `enrichment.py` | ~60 | 模式富化: rant/opportunity payload |
| `keywords.py` | ~80 | YAML 词典加载器 |
| `prompts.py` | ~100 | 3 套 LLM 提示模板 |
| `query_resolver.py` | ~120 | CJK 查询解析 + LLM 翻译 |
| `repository.py` | ~130 | DB CRUD + 社区发现 |
| `report_export.py` | ~200 | Markdown 导出 (3 种格式) |

---

## 7. 与主引擎的集成点

| 共享组件 | 说明 |
|---------|------|
| `OpenAIChatClient` | LLM 客户端 (同一个 Grok-4.1 模型) |
| `evidence_posts` 表 | 证据生态 — hotpost 发现的帖子可被主引擎复用 |
| `maybe_discover_community` | hotpost 搜索过程中自动发现新社区，写入主社区池 |
| `Settings.llm_model_name` | 共享模型配置 |

---

## 8. 关键阈值速查

| 参数 | 默认值 | 来源 |
|------|--------|------|
| `HOTPOST_QUERY_MAX_CHARS` | 50 | env var |
| `HOTPOST_MAX_QUERY_SPLITS` | 3 | env var |
| `HOTPOST_LLM_MAX_TOKENS` | 4096 | env var |
| `HOTPOST_LLM_TEMPERATURE` | 0.3 | env var |
| `ENABLE_HOTPOST_LLM_REPORT` | true | env var |
| `ENABLE_HOTPOST_RELEVANCE_FILTER` | true | env var |
| `ENABLE_HOTPOST_QUERY_TRANSLATION` | true | env var |
| `ENABLE_HOTPOST_MARKDOWN_EXPORT` | true | env var |
| `COMMENTS_TTL_SECONDS` | (code const) | service.py |
| opportunity_strength=strong | ≥20帖 + ≥5 me_too | 硬编码 |
| opportunity_strength=medium | ≥10帖 | 硬编码 |
| reliability_note 阈值 | 10 帖 | 硬编码 |
