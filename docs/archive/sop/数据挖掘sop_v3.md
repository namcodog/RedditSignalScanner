# Reddit Signal Scanner: Data Gold Mining SOP (v3.1)

> **角色**: Data Gold Miner (数据淘金工)
> **核心资产**: Postgres Analysis Layer (基于 `mv_analysis_` 视图) + Semantic Engine
> **目标**: 从 Reddit 噪声中提炼出 **"可售卖的商业机会"**。

---

## 🗺️ 核心流程：淘金漏斗 (The Gold Funnel)

我们将挖掘过程重构为从“矿石”到“金币”的五个精炼步骤。

| 阶段 | 代号 | 核心任务 | 依赖工具 | 商业价值 |
|:---:|---|---|---|---|
| **0** | **映射 (Mapping)** | [新增] 中文需求 -> 英文社区/关键词 | LLM Semantic Layer | **打破语言隔阂，确保找对战场** |
| **1** | **洗矿 (Washing)** | 剔除 Bot、水军、低质贴 | `posts_raw` | 减少 60% 算力浪费，提高信号信噪比 |
| **2** | **探脉 (Sensing)** | 识别痛点密集区 & 飙升竞品 | `mv_analysis_labels` | 发现“谁在痛苦”以及“谁在赚钱” |
| **3** | **提纯 (Refining)** | 锁定具体商业机会 (Gap/Arbitrage) | SQL Logic | 明确“卖什么”能解决问题 |
| **4** | **定价 (Valuation)** | 评估机会的市场规模与转化率 | `analytics_community_history` | 决定是否值得投入资源 |

---

## 🧠 Phase 0: 语义映射 (Semantic Mapping) - **[NEW]**

**场景**: 用户输入 "宠物用品"，但 Reddit 上全是 `r/dogs`, `r/cats`, `r/petcare`。
**执行动作**:
使用 `generate_t1_market_report.py` 的语义扩展层：
1.  **Input**: 中文/模糊话题 (e.g. "跨境支付")
2.  **LLM Process**: 扩展为 5-10 个精准英文关键词 + **特定 Subreddit 名称** (e.g. `payment`, `stripe`, `r/dropshipping`, `r/ecommerce`)。
3.  **Output**: 用于 SQL 查询的 Token Set。

---

## ⛏️ Phase 1: 洗矿 (Washing & De-noising)

**场景**: Reddit 上充满了 AutoMod 通告、垃圾广告和无效的水贴。在分析前必须清洗。

**执行动作**: 每次分析前，确保你的 WHERE 子句包含以下“去噪逻辑”。

```sql
-- 标准去噪过滤器 (Standard Noise Filter)
WHERE author_name != 'AutoModerator'
  AND title NOT ILIKE '%Megathread%'
  AND title NOT ILIKE '%Daily Discussion%'
  AND len(body) > 50 -- 剔除太短的无效吐槽
  AND is_stickied = false -- 忽略置顶公告
```

---

## 🧭 Phase 2: 探脉 (Sensing - 寻找痛点与竞品)

**前提**: 已执行 `make refresh-mining` (Calling `refresh_mining_views.py`)

### 2.1 痛点热力图 (Pain Point Heatmap)
**商业问题**: “在这个细分市场，用户最抱怨什么？”
**分析逻辑**: 统计 `category='pain'` 的高频 `aspect`。

```sql
SELECT 
    subreddit,
    aspect as pain_point,
    COUNT(*) as complaint_count,
    ROUND(AVG(sentiment::numeric), 2) as avg_sentiment -- 越低越愤怒
FROM mv_analysis_labels
WHERE category = 'pain'
  AND created_at > NOW() - INTERVAL '7 days'
GROUP BY subreddit, aspect
HAVING COUNT(*) > 10
ORDER BY complaint_count DESC;
```
**👉 洞察**: 如果 `shipping` 在 `r/dropshipping` 中高频出现，说明物流是核心痛点，这就是卖“海外仓服务”的机会。

### 2.2 竞品负面信号 (Competitor Vulnerability)
**商业问题**: “大家都在骂哪个竞品？它的弱点就是我们的卖点。”

```sql
SELECT 
    e.entity_name as brand,
    l.aspect as weakness,
    COUNT(*) as mention_count
FROM mv_analysis_entities e
JOIN mv_analysis_labels l ON e.post_id = l.post_id
WHERE l.category = 'pain'
  AND e.entity_type = 'brand'
GROUP BY e.entity_name, l.aspect
ORDER BY mention_count DESC
LIMIT 20;
```

---

## 💎 Phase 3: 提纯 (Refining - 捕捉具体商机)

这是“数据淘金”的核心。我们寻找三种特定的 **Money Patterns**。

### 3.1 模式 A: "求推荐" (The 'W2C' Signal)
**特征**: 用户明确询问“在哪里买”或“有没有更好的替代品”。这是**购买意图最强**的信号。

```sql
SELECT 
    p.subreddit,
    p.title,
    p.url
FROM posts_hot p
WHERE (
    p.title ILIKE '%recommend%' OR 
    p.title ILIKE '%suggestion%' OR 
    p.title ILIKE '%alternative to%' OR 
    p.title ~* '\bw2c\b' -- 'Where to Cop' 潮牌圈黑话
)
AND p.created_at > NOW() - INTERVAL '24 hours'
AND p.num_comments > 5 -- 只有互动的才值得看
ORDER BY p.score DESC;
```

### 3.2 模式 B: "功能缺失" (The 'Feature Gap')
**特征**: 用户抱怨“我希望产品 X 能做 Y，但它不能”。

```sql
SELECT 
    subreddit,
    aspect as missing_feature,
    COUNT(DISTINCT post_id) as demand_volume
FROM mv_analysis_labels
WHERE category = 'pain' 
  AND aspect NOT IN ('price', 'shipping') -- 排除通用痛点，只看产品痛点
GROUP BY subreddit, aspect
ORDER BY demand_volume DESC;
```

---

## ⚖️ Phase 4: 定价 (Valuation - 社区价值评分)

**商业问题**: “我应该把营销预算花在哪个社区？”
**公式**: **C-Score (v3.0)** = `商业密度(40%)` + `活跃度(30%)` + `增长率(30%)`

**执行计算**:

```sql
WITH commercial_density AS (
    -- 计算每个社区的“痛点”和“求购”贴比例
    SELECT 
        subreddit,
        COUNT(*) FILTER (WHERE category = 'pain') * 100.0 / COUNT(*) as pain_density
    FROM mv_analysis_labels
    GROUP BY subreddit
),
activity AS (
    SELECT subreddit, AVG(num_comments) as avg_engagement
    FROM posts_hot
    GROUP BY subreddit
)
SELECT 
    c.subreddit,
    c.pain_density,
    a.avg_engagement,
    (c.pain_density * 0.6 + a.avg_engagement * 0.4) as opportunity_score
FROM commercial_density c
JOIN activity a ON c.subreddit = a.subreddit
ORDER BY opportunity_score DESC;
```

---

## 🗓️ 每日淘金例会 (Daily Routine)

1.  运行 `make refresh-mining`。
2.  运行 `make report-t1 TOPIC="[今日话题]"`。
3.  检查生成的 Report，重点看 **P/S Ratio** 和 **机会卡片**。

---

**SOP 执行人**: Data Gold Miner Agent