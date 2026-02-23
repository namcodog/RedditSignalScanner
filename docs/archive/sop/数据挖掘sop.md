# Reddit Signal Scanner: Data Mining & Opportunity Protocol (v2.0)

> **执行角色**: 数据淘金矿工程师 (Data Gold Miner)
> **最后更新**: 2025-11-28
> **核心目标**: 将海量 Reddit 噪声转化为可执行的商业信号。
> **基本原则**: 以数据库为核武器，以 SQL 为探针，以 Python 服务为加工厂。

---

## 🗺️ 协议总览：从矿石到黄金

本 SOP 将数据挖掘流程标准化为五个核心阶段。每个阶段都有明确的**输入**、**执行动作**（SQL/脚本）和**输出产物**。

| 阶段 | 名称 | 目标 | 核心工具 |
|:---:|---|---|---|
| **1** | **矿床探查 (Health Check)** | 确保数据全、新、准 | SQL Diagnostics |
| **2** | **矿石筛选 (Metrics & Quality)** | 识别高价值社区，剔除噪声 | `metrics_service` / SQL |
| **3** | **冶炼提纯 (Semantic Extraction)** | 提取痛点、场景、实体 | `analysis_engine` / `labeling` |
| **4** | **铸造金币 (Opportunity Signal)** | 发现商机、爆发趋势、语义盲区 | SQL Heatmaps / Insights |
| **5** | **工艺校准 (Calibration)** | 对齐 T1/T2/T3 策略与调度 | `crawler_config` / `scheduler` |

---

## ⛏️ Phase 1: 矿床探查 (数据全库体检)

**目标**: 在开始挖掘前，必须确认“矿床”状况，避免在劣质数据上浪费算力。

### 1.1 基础规模与新鲜度检查
**执行动作**: 运行以下 SQL 确认数据水位。

```sql
-- 1. 总体规模与当前有效数据
SELECT 
    COUNT(*) as total_raw,
    COUNT(*) FILTER (WHERE is_current = true) as current_active,
    COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '24 hours') as new_24h
FROM posts_raw;

-- 2. 社区数据断层检查 (找出有配置但无数据的社区)
SELECT p.name, c.posts_cached, c.last_crawled_at
FROM community_pool p
LEFT JOIN community_cache c ON p.name = c.community_name
WHERE c.posts_cached < 10 OR c.last_crawled_at IS NULL
ORDER BY c.posts_cached ASC;
```

### 1.2 标注覆盖率体检
**执行动作**: 确认语义引擎是否在工作（是否有 content_labels）。

```sql
-- 检查痛点(pain)和实体(brand)的覆盖率
SELECT 
    count(distinct CASE WHEN category = 'pain' THEN content_id END) as pain_labeled_count,
    count(distinct CASE WHEN category = 'brand' THEN content_id END) as brand_labeled_count,
    (SELECT COUNT(*) FROM comments) as total_comments
FROM content_labels;
```

**输出产物**: 
- `reports/phase-log/phase1_health_check.md` (记录异常社区和数据断点)

---

## 🧪 Phase 2: 矿石筛选 (社区质量重算)

**目标**: 重新评估社区价值（C-Score），决定哪些社区值得深挖，哪些应该降权。

### 2.1 社区价值评分 (C-Score)
基于 `backend/app/services/metrics_service.py` 的逻辑，但使用 SQL 进行批量高效计算。

**公式**: `C = 35%(语义浓度) + 25%(活跃度) + 20%(新鲜度) + 10%(非垃圾) + 10%(非重复)`

**执行动作**: 运行 [SQL Toolkit - Community Scoring](#sql-toolkit---community-scoring) 中的查询。

### 2.2 分级调整 (Re-Tiering)
根据 C-Score 动态调整社区的 Tier（T1/T2/T3）。

*   **T1 (High Value)**: C-Score Top 30% & 低重复率。策略：`2h` 抓取，全量语义分析。
*   **T2 (Potential)**: C-Score Mid 40%。策略：`4h` 抓取，仅痛点分析。
*   **T3 (Low/New)**: C-Score Low 或 高重复率 (>50%)。策略：`8h-24h` 探针抓取，仅监控爆发。

**执行脚本**:
```bash
# 假设存在此脚本用于应用新的 Tier 配置（需确认 backend/scripts 下的对应脚本）
# 若无，需手动更新 community_pool 表
python backend/scripts/update_community_tiers.py --apply-rules
```

---

## 🔥 Phase 3: 冶炼提纯 (语义挖掘)

**目标**: 从文本中提取结构化金矿——痛点 (Pain)、场景 (Scene)、实体 (Entity)。

### 3.1 痛点提取 (Pain Mining)
**核心逻辑**: 关注 `content_labels` 中 `category='pain'` 的数据。

**关键查询**: 找出当前最热的痛点类型。
```sql
SELECT aspect, COUNT(*) as frequency
FROM content_labels 
WHERE category = 'pain' 
  AND created_at > NOW() - INTERVAL '7 days'
GROUP BY aspect 
ORDER BY frequency DESC 
LIMIT 20;
```

### 3.2 实体/品牌映射 (Entity Mapping)
**核心任务**: 解决 `content_entities` 与 `posts_raw` 的关联问题，确保能回答“哪个品牌在被吐槽”。

**执行动作**:
1.  检查未映射的实体：`SELECT COUNT(*) FROM content_entities WHERE post_id IS NULL AND comment_id IS NULL;`
2.  执行映射修复脚本 (如有)。

### 3.3 语义回流 (Semantic Feedback)
将高频但未识别的关键词回流到 `semantic_terms` 库。
*   **输入**: T1 社区高分评论 (`score > 5`)。
*   **处理**: 提取 Noun Chunks，过滤停用词。
*   **输出**: `semantic_candidates` 表 (待审核词库)。

---

## 💎 Phase 4: 铸造金币 (商业机会识别)

**目标**: 输出最终的商业洞察信号。这是产品经理最关心的部分。

### 4.1 痛点热力图 (Pain Heatmap)
**场景**: “告诉我 Dropshipping 领域最近大家都在抱怨什么？”

**执行动作**:
```sql
SELECT 
    c.subreddit, 
    l.aspect as pain_point, 
    COUNT(*) as volume,
    AVG(cm.score) as avg_impact
FROM content_labels l
JOIN comments cm ON l.content_id = cm.id
JOIN community_pool c ON cm.subreddit = c.name
WHERE l.category = 'pain' 
  AND c.tier = 'high'
  AND cm.created_utc > NOW() - INTERVAL '30 days'
GROUP BY c.subreddit, l.aspect
HAVING COUNT(*) > 5
ORDER BY volume DESC;
```

### 4.2 爆发趋势识别 (Trend Spotting)
**场景**: “哪个社区或话题突然火了？”

**规则**: 7天提及量增幅 > 10倍。
**执行动作**: 运行 [SQL Toolkit - Trend Detection](#sql-toolkit---trend-detection)。

### 4.3 被低估的“黑马”社区
**场景**: 寻找 Tier 目前低但指标极好的社区。
**逻辑**: `Tier != 'high'` 但 `C-Score > 80`。

---

## ⚙️ Phase 5: 工艺校准 (配置与调度)

**目标**: 将挖掘的发现转化为系统配置的持久化更新。

1.  **更新 Crawler Config**: 
    *   修改 `backend/config/crawler.yml`。
    *   将爆发社区提升至 `T1` 组。
    *   将高重复社区 (`dedup_rate > 50%`) 降级或开启强去重。
2.  **更新 停用词/黑名单**:
    *   将误报高的词加入 `backend/config/community_blacklist.yaml` 或语义过滤服务。

---

## 🧰 Appendix: The Nuclear Console (SQL Toolkit)

> **警告**: 直接在数据库执行，请使用只读事务或小心操作。

### 🛠 Tool 1: Community Scoring (C-Score 计算)
```sql
WITH metrics AS (
    SELECT 
        name,
        semantic_quality_score as topic_score, -- 语义分
        CASE WHEN daily_posts > 50 THEN 1 ELSE daily_posts/50.0 END as activity_score, -- 活跃分
        (1 - COALESCE(dedup_rate, 0)) as uniqueness_score, -- 独特性
        CASE WHEN last_crawled_at > NOW() - INTERVAL '48 hours' THEN 1 ELSE 0 END as freshness_score -- 新鲜度
    FROM community_pool cp
    JOIN community_cache cc ON cp.name = cc.community_name
)
SELECT 
    name,
    (topic_score * 35 + activity_score * 25 + freshness_score * 20 + uniqueness_score * 20) as c_score
FROM metrics
ORDER BY c_score DESC;
```

### 🛠 Tool 2: Trend Detection (爆发检测)
```sql
WITH recent_stats AS (
    SELECT subreddit, COUNT(*) as cnt_7d
    FROM posts_raw
    WHERE created_at > NOW() - INTERVAL '7 days'
    GROUP BY subreddit
),
historical_stats AS (
    SELECT subreddit, COUNT(*) as cnt_prev_30d
    FROM posts_raw
    WHERE created_at BETWEEN NOW() - INTERVAL '37 days' AND NOW() - INTERVAL '7 days'
    GROUP BY subreddit
)
SELECT 
    r.subreddit,
    r.cnt_7d,
    h.cnt_prev_30d,
    ROUND(r.cnt_7d::numeric / NULLIF(h.cnt_prev_30d, 1), 2) as growth_ratio
FROM recent_stats r
JOIN historical_stats h ON r.subreddit = h.subreddit
WHERE r.cnt_7d > 20  -- 忽略极小样本
  AND (r.cnt_7d::numeric / NULLIF(h.cnt_prev_30d, 1)) > 3 -- 3倍增长
ORDER BY growth_ratio DESC;
```

### 🛠 Tool 3: Semantic Gap Analysis (语义盲区)
找出高频出现但未被系统语义库(`semantic_terms`)捕获的词。
*(需结合 `semantic_candidates` 表使用)*
```sql
SELECT term, frequency, status
FROM semantic_candidates
WHERE status = 'pending'
ORDER BY frequency DESC
LIMIT 50;
```