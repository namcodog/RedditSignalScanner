# Reddit Signal Scanner: Data Gold Mining SOP (v4.5) - "The Deep Refinery"

> **角色**: Data Gold Miner (数据淘金工)
> **核心资产**: Postgres Analysis Layer + Omni-Analyst Prompt Engine + **Tier Intelligence & Deduplication System**
> **目标**: 产出 **"99%纯度"** 的深度市场洞察报告，消除噪音，量化机会，提供决策级情报。

---

## 🗺️ 核心流程：全能分析漏斗 (The Omni-Funnel v4.5)

我们将挖掘过程重构为从“用户模糊意图”到“深度商业洞察”的五个精炼步骤。v4.5 重点强化了**降噪**与**提纯**。

| 阶段 | 代号 | 核心任务 | 依赖工具 | 关键动作 & 价值 (Value Add) |
|:---:|---|---|---|---|
| **0** | **语义映射 (Mapping)** | 中文需求 -> 英文社区 + **排它词** | LLM Semantic Layer | **双向锁定**：不仅生成关键词，还生成 `exclude` 列表（如“宠物”排除“游戏/灵媒”）。<br>💎 **价值**：从源头杜绝同名不同义的无关社区干扰。 |
| **1** | **广域扫描 (Scanning)** | 锁定 Top 12 **高价值**社区 | `t1_stats` + `TierIntelligence` | **多维体检**：不再只看名字！<br>1. **内容硬过滤**：全文检索必须命中关键词。<br>2. **密度加权**：`pain_density` (痛点密度) 低于 0.1 直接剔除。<br>💎 **价值**：确保选出来的社区都是真正有“怨气”和“讨论”的垂直战场。 |
| **2** | **深度萃取 (Extraction)** | 抓取并**清洗**热帖评论 | `Deduplicator` + `JIT Labeling` | **即时标注与去重**：<br>1. **JIT Labeling**：现场对数据打标签，确保指标实时准确。<br>2. **MinHash 去重**：剔除重复车轱辘话和短废话。<br>💎 **价值**：喂给 AI 的每一条评论都是独一无二的干货，拒绝水分。 |
| **3** | **数据炼油 (Refining)** | 计算趋势、情感与**格局** | `CompetitorLayering` + `TrendRadar` | **上帝视角**：<br>1. **竞品分层**：自动识别 Dominant (老大) vs Challenger (挑战者)。<br>2. **机会评分**：综合计算 Opportunity Score (0-100)。<br>💎 **价值**：把数据变成“情报”，直接告诉卖家谁是对手，现在是不是入场时机。 |
| **4** | **全能分析 (Analysis)** | 双阶段生成深度报告 | Omni-Prompt v4 | **深度推理**：Stage 1 (概览) + Stage 2 (深度) 拼接。<br>💎 **价值**：基于清洗后的高纯度数据，产出具有逻辑归因（机制-损失-连锁反应）的深度洞察。 |
| **5** | **语义联想 (Vectorization)** | 捕捉隐性需求与跨界信号 | `EmbeddingService` + `pgvector` | **双模搜索**：<br>1. **关键词**：精准锚定显性讨论。<br>2. **向量**：模糊匹配隐喻（如“焦虑”->“解压”）。<br>💎 **价值**：发现用户“嘴上没说但心里在想”的潜在机会。 |

---

## 🧠 Phase 0: 语义映射 (Semantic Mapping)

**场景**: 用户输入 "宠物智能硬件痛点"。
**执行**:
1.  系统调用 LLM (`_expand_topic_semantically`)。
2.  **Positive**: `['feeder', 'litter box', 'smart pet', 'tracker']`
3.  **Negative (新)**: `['spell', 'magic', 'game', 'nintendo', 'welfare']`
4.  **价值**: 彻底打破中英文隔阂，并构建第一道防线，防止“灵媒社区”乱入。

---

## ⛏️ Phase 1: 智能扫描与体检 (Intelligent Scanning)

**执行**:
1.  **内容初筛**: 使用 Postgres `to_tsvector` 全文检索，统计每个社区内**真正包含关键词**的帖子数。
2.  **多维体检 (Tier Check)**:
    *   调用 `TierIntelligenceService` 计算 **Pain Density** (痛点密度) 和 **Spam Ratio** (垃圾率)。
    *   **硬门槛**: `Pain Density < 0.1` 或 `Spam Ratio > 0.4` -> **DROP (直接丢弃)**。
3.  **价值**: 只有“真材实料”且“怨气冲天”的社区才能进入下一轮，彻底告别水贴社区。

---

## 🧪 Phase 2: 即时标注与去重 (JIT Labeling & Deduplication)

**这是 v4.5 的提纯核心**：

1.  **JIT Labeling (即时标注)**:
    *   **问题**: 历史数据可能没标签，导致分析为 0。
    *   **解法**: 在分析前，现场对 Top 5000 条相关评论进行分类标注 (Pain/Solution)。
    *   **修正**: 统一时间窗口（如 30天），确保指标计算与标注数据对齐。
2.  **MinHash 去重**:
    *   **问题**: 热点话题下可能有大量重复的 "Me too" 评论。
    *   **解法**: 使用 MinHash 算法计算相似度，剔除重复内容，并过滤掉长度 < 20 的无效短评。
3.  **价值**: 极大提升数据密度，让 LLM 用同样的 Token 读到 10 倍的信息量。

---

## 🧬 Phase 3: 数据炼油厂 (The Data Refinery)

引入高级商业分析模块：

1.  **趋势雷达 (Trend Radar)**: 识别 `🔥 EXPLODING` (爆发) 信号。
2.  **特征情感矩阵 (Aspect-Sentiment Matrix)**: 量化用户对“价格”、“功能”的爱恨情仇。
3.  **竞品分层 (Competitor Layering)**:
    *   **Dominant**: 提及占比 > 20% (如 Amazon)。
    *   **Challenger**: 提及占比 5-20% (如 PetKit)。
    *   **Niche**: 提及占比 < 5%。
4.  **机会评分 (Opportunity Scorer)**:
    *   基于 `Pain Density` + `Growth Rate` + `Saturation` 计算出的综合得分 (0-100)。

---

## 🧭 Phase 4: 全能分析与交付 (Omni-Analysis & Delivery)

**模型**: Google Gemini 2.5 Flash (via OpenRouter)
**策略**: **双阶段生成 (Two-Stage Generation)**

1.  **Stage 1 (宏观)**: 结合 **竞品分层** 和 **机会评分**，生成决策卡片和市场概览。
2.  **Stage 2 (微观)**: 基于 **去重后的高质量评论**，生成深度痛点归因（根因->机制->后果）。
3.  **Merge**: 无缝拼接。

**产出标准**:
*   **准确**: 没有幻觉，没有无关社区。
*   **深刻**: 痛点分析直击商业模式弊端（如订阅制）。
*   **实战**: 机会卡直接给出可落地的产品/营销建议。

---

## 🛠 运维指令 (Makefile Operations)

### 生成深度报告
```bash
make report-t1 TOPIC="你的话题" DESC="你的背景描述"
```
*Example*: `make report-t1 TOPIC="宠物智能硬件" DESC="挖掘痛点"`

### 调试模式
如需查看详细的过滤日志（Dropping ...）：
```bash
# 直接运行脚本查看标准输出
python backend/scripts/generate_t1_market_report.py --topic "..."
```

---

**SOP 更新人**: Data Gold Miner Agent
**版本**: v4.5 (Deep Refinery Edition)
**时间**: 2025-11-30

---

## 🕸️ Phase 5: 语义向量化 (Semantic Vectorization)

**核心逻辑**:
系统不再仅仅依赖“文字完全匹配”。通过 `BAAI/bge-m3` 模型，我们将帖子转化为 1024 维向量。
在扫描社区时（Phase 1），系统会同时执行：
1.  `SQL LIKE %keyword%` (传统匹配)
2.  `Vector Distance < 0.4` (语义近似)

**场景**:
*   **传统**: 搜 "Dog Toy" -> 只能找到包含 "Dog Toy" 的帖子。
*   **语义**: 搜 "Dog Toy" -> 能找到 "My puppy is bored" (语义相关，虽无关键词)。

**运维指令**:

### 1. 检查回填进度
```bash
# 查看 post_embeddings 表行数
make check-health
# 或者直接 SQL
# SELECT count(*) FROM post_embeddings;
```

### 2. 启动/继续数据回填 (Backfill)
后台运行回填脚本（支持断点续传）：
```bash
nohup python backend/scripts/backfill_embeddings.py > logs/embedding_backfill.log 2>&1 &
```
*注意：此过程消耗 CPU/GPU 资源，建议在空闲时段挂机运行。*