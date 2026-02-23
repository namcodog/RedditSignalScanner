# 第三阶段执行记录：人类需求图谱 (Phase 3 Execution Log)

**日期**: 2025-12-05
**执行人**: Eleven (Architect) & Product Manager
**状态**: ✅ 已完成 (Completed)

---

## 1. 阶段目标
将系统从"问题发现器"升级为"**需求洞察引擎**"。基于马斯洛需求层次理论，将 24 万帖子标记为 5 大核心需求：**Survival / Efficiency / Belonging / Aesthetic / Growth**。

---

## 2. 核心里程碑 (Milestones)

### ✅ 2.1 语义库重构 (Phase 3.1)
*   **规则挖掘**: 从 24 万帖子中提取 **18,975 条** 语义规则。
*   **噪音修复**: 加入 80+ 停用词过滤，剔除 "the job" 等无意义短语。
*   **资产**: `semantic_rules` 表 + `pain_keywords` (136条)。

### ✅ 2.2 Smart Tagger 上线 (Phase 3.2)
*   **新表**: `post_semantic_labels` (l1_category, l1_secondary, raw_scores...)
*   **算法**: FlashText 内存匹配 + TextBlob/VADER 情感分析
*   **全量覆盖**: 243,890 条帖子 100% 打标

### ✅ 2.3 痛点敏感度调优 (Phase 3.3)
*   **VADER 替代 TextBlob**: 专为社交媒体优化
*   **最大负面原则**: 切句取最负分，避免长文稀释
*   **规则分级**: hard_pain / soft_pain / neutral

### ✅ 2.4 人类需求图谱 (Phase 3.4)
*   **马斯洛 5 层**: Survival / Efficiency / Belonging / Aesthetic / Growth
*   **双标签**: l1_primary + l1_secondary 揭示交叉需求
*   **乘法情感修正**: 负面强化 Survival，正面强化 Growth

### ✅ 2.5 再平衡 (Phase 3.5)
*   **问题**: Survival 虚高 (76%)，Efficiency 虚低 (4%)
*   **解法**: 剔除 help/question 等中性词，增加意图短语 (how to, best tool)
*   **结果**: Survival 降至 66%，Growth 升至 15%

### ✅ 2.6 效率注入 (Phase 3.6)
*   **问题**: Efficiency 仅 4.77%，工具类帖子未被识别
*   **解法**: 注入 50+ 电商工具实体 (shopify, klaviyo, zapier...)
*   **结果**: Efficiency 升至 **10.01%**

### ✅ 2.7 向量回填 (Task A)
*   **目标**: 构建深层语义搜索与 RAG 基础
*   **模型**: `BAAI/bge-m3` (多语言/多粒度)
*   **进度**: 全量回填 24万+ 帖子 (100% 覆盖)
*   **价值**: 支持意图搜索 (Search by Intent) 与相似推荐

### ✅ 2.8 自动化闭环 (Task C)
*   **链路**: Crawler (Insert) -> Celery Task (`tag_posts_batch`) -> DB
*   **机制**: 爬虫双写成功后，自动触发批量打标任务 (Near Real-time)
*   **成果**: 实现了"抓取即打标"，无需人工干预

### ✅ 2.9 报告认知对齐 (Phase 5.3)
*   **目标**: 将技术标签转化为"人话"，对齐卖家认知。
*   **动作**:
    *   **术语翻译**: Survival -> "吐槽/避坑党"；Efficiency -> "找货/工具党"；Growth -> "进阶/学习党"。
    *   **Prompt Humanization**: 废弃 `aspect_breakdown` 等变量名，强制 LLM 用自然语言输出。
    *   **去重逻辑**: "痛点" -> "驱动力" -> "机会" 三级递进，不再重复背景。

### ✅ 2.10 深度推理集成 (Phase 7)
*   **目标**: 填补分析引擎的空白，实现"有理有据"的洞察。
*   **组件**:
    *   **Competitor Layering**: 引入 `competitor_layers.yml`，精准区分 Platform (Amazon), Brand (Breville), Channel (YouTube)。
    *   **Quote Extractor**: 引入智能引言抽取器，基于情感和相关度筛选"用户金句"，附带 🔗 链接。
    *   **Pain Cluster**: 修复 SQL 逻辑，兼容 `Survival` 标签，实现基于 TF-IDF 的痛点归因。
*   **资产**: 注入 **1600+** 个垂类品牌到 `semantic_terms`，覆盖 Ecommerce, Food, Home, Outdoor 等 7 大赛道。

### ✅ 2.11 模型升级 (Phase 8)
*   **动作**: 全面切换至 **x-ai/grok-4.1-fast** (OpenRouter)。
*   **价值**: 逻辑推理能力显著提升，文笔更接地气，擅长处理复杂 JSON 结构。

---

## 3. 最终分布 (Final Distribution)

| 需求层次 | 占比 | 商业机会 |
| :--- | :--- | :--- |
| **Survival** | 62.72% | 质量改良、合规服务 |
| **Growth** | 14.18% | 内容营销、卖课 |
| **Efficiency** | 10.01% | SaaS、自动化工具 |
| **Belonging** | 6.97% | 礼品选品、节日营销 |
| **Aesthetic** | 6.12% | 高颜值产品、Etsy选品 |

---

## 4. 工具链与脚本 (Toolchain)

| 脚本/文件 | 用途 | 运行方式 |
| :--- | :--- | :--- |
| `backend/app/services/semantic/smart_tagger.py` | **核心打标器**。标准化 Service 类 (马斯洛 5 层)。 | Service 调用 |
| `backend/scripts/run_semantic_pipeline.py` | **语义流水线**。支持增量/全量打标。 | `make semantic-tag` |
| `backend/scripts/backfill_embeddings.py` | **向量回填**。生成 BGE-M3 向量。 | `make semantic-embed` |
| `backend/scripts/generate_t1_market_report.py` | **全能分析师**。生成 V8 深度洞察报告。 | `make report-t1` |
| `backend/scripts/migrate_brands.py` | **品牌注入**。将 YAML 品牌库注入数据库。 | 手动运行 |
| `backend/app/services/analysis/competitor_layering.py` | **竞品分层**。区分平台/品牌/渠道。 | 库调用 |

---

## 5. 数据结构 (Schema)

```sql
-- post_semantic_labels 表字段
post_id         BIGINT PRIMARY KEY
l1_category     VARCHAR(50)  -- Survival/Efficiency/Belonging/Aesthetic/Growth
l1_secondary    VARCHAR(50)  -- 次需求 (Phase 3.4 新增)
l2_business     VARCHAR      -- subreddit
raw_scores      JSONB        -- {"Survival": 2.5, "Growth": 1.0, ...}
sentiment_score FLOAT        -- VADER 最大负面分
confidence      FLOAT

-- semantic_terms 表字段 (Phase 7 新增)
canonical       VARCHAR(128) -- 品牌名 (e.g. 'olight')
category        VARCHAR(32)  -- 赛道 (e.g. 'Tools_EDC')
layer           VARCHAR(8)   -- 'entity'
precision_tag   VARCHAR(16)  -- 'brand'
weight          NUMERIC
```

---

## 6. 应急与维护 (Maintenance)

*   **生成报告**:
    ```bash
    make report-t1 TOPIC="咖啡机" DESC="..." MODEL="x-ai/grok-4.1-fast"
    ```
*   **品牌库维护**:
    1. 编辑 `backend/config/semantic_sets/brands_*.yml`。
    2. 运行 `python backend/scripts/migrate_brands.py` (增量注入)。
*   **分层规则维护**:
    1. 编辑 `backend/config/entity_dictionary/competitor_layers.yml`。
    2. 无需重启，下次报告自动生效。

---

## 7. 演进历史

| 日期 | 阶段 | 关键变更 |
| :--- | :--- | :--- |
| 2025-12-04 | 3.1 | 语义规则挖掘 (18,975 条) |
| 2025-12-05 | 3.2 | Smart Tagger 上线 |
| 2025-12-05 | 3.3 | VADER + 最大负面原则 |
| 2025-12-05 | 3.4 | 马斯洛 5 层需求图谱 |
| 2025-12-05 | 3.5 | 再平衡 (Growth +9%) |
| 2025-12-05 | 3.6 | 效率注入 (Efficiency +6%) |
| 2025-12-05 | 3.7 | 向量回填 & 自动化闭环 |
| 2025-12-07 | 5.3 | 报告人话化 (Prompt V2) |
| 2025-12-07 | 7.0 | 深度推理集成 (Competitor Layering) |
| 2025-12-07 | 8.0 | Grok 模型切换 & 品牌库注入 |

---

**文档维护**: Reddit Signal Scanner Team