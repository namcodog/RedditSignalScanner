# Reddit Signal Scanner (Gemini 项目记忆)

**项目角色**: AI 驱动的市场情报引擎
**核心使命**: 将 Reddit 上原始的讨论数据转化为可落地、高价值的市场洞察，服务于跨境电商卖家。
**当前版本**: v6.0 (Context-Aware & Dual-Mode Architecture)
**最后更新**: 2025-12-10

---
## 0. 用户规则

- **初始化**:使用serena mcp工具检索代码库，严格遵循产品经理的指令，不允许做多余的操作，不擅自修改代码文件。
- **对话规范**: 与产品经理沟通一律使用简洁、通俗、健谈的中文，必须说大白话；把工程术语翻译成小白也能明白的表达，直接明了。
- **执行规则**: 不做多余的操作，一切听从用户的指令，不擅自修改代码，先分析找出问题的根本原因，给用户反馈。
- **核心禁忌**: 严禁在报告中使用“市场份额”、“营收”等投行术语，必须使用“讨论热度”、“声量”等舆情术语。

---

## 1. 系统架构 ("大脑")

本系统构建于 **Python (FastAPI/SQLAlchemy)** 后端与 **PostgreSQL (pgvector)** 数据仓库之上，利用 **x-ai/Grok-4.1** 进行深度推理。

### 1.1 核心组件 (已激活)
*   **数据采集 (Data Ingestion)**:
    *   **System A (在线)**: Celery 实时增量抓取。
    *   **System B (离线)**: `crawl_comprehensive.py` 批量深挖。
*   **语义理解 ("识人")**:
    *   **Persona Engine (Phase H)**: `PersonaGenerator` 结合 LLM 与规则引擎，为核心社区生成结构化用户画像 (如 "Tech-Savvy", "Budget-Conscious")。
    *   **Context Router (Phase F/Step 3)**: 基于语义识别垂直赛道 (Vertical)，动态调整社区白名单 (如母婴赛道自动放行 `r/AskWomen`)。
*   **分析推理 ("炼油")**:
    *   **Dual-Mode Router (Phase F/Step 1)**: 支持 **Market Insight** (屏蔽卖家噪音) 与 **Operations** (聚焦卖家玩法) 双模式。
    *   **Signal Density (Phase G)**: 引入 BM25 思想的 "话题浓度" 指标，奖励垂直社区，惩罚泛化社区。
    *   **Solution Miner (Phase G)**: 基于正则与语义挖掘 "解决方案" 信号 (如 "Fixed it by...")。
*   **报告引擎 ("嘴巴")**:
    *   **Facts V6**: 现在的 `facts.json` 包含 **Price Sensitivity** (价格锚点)、**Usage Context** (场景标签) 和 **Community Personas**。

### 1.2 关键文件
*   `backend/scripts/generate_t1_market_report.py`: 报告生成主程序 (支持 `--mode` 和智能过滤)。
*   `backend/config/community_roles.yaml`: 定义卖家/运营社区 (B2B) 的角色清单。
*   `backend/config/community_blacklist.yaml`: 定义上下文相关的动态黑名单规则。
*   `backend/app/services/analysis/persona_generator.py`: 用户画像生成服务。

---

## 2. 操作 SOP (如何运行)

### 2.1 生成市场洞察报告 (消费者视角)
使用 `market_insight` 模式 (默认)，系统会自动屏蔽卖家/B2B 社区，并应用垂直赛道过滤器。

```bash
# 生成家用咖啡机报告 (自动屏蔽 r/AmazonFBA, r/Marketing 等)
python backend/scripts/generate_t1_market_report.py \
  --topic "家用咖啡机" \
  --product-desc "高性价比智能咖啡机" \
  --days 365 \
  --mode market_insight
```

### 2.2 生成运营策略报告 (卖家视角)
使用 `operations` 模式，系统会聚焦卖家社区，挖掘同行玩法。

```bash
# 生成亚马逊广告策略报告 (聚焦 r/PPC, r/AmazonSeller 等)
python backend/scripts/generate_t1_market_report.py \
  --topic "Amazon PPC Strategy" \
  --mode operations
```

---

## 3. 演进历史 (旅程)

### Phase 1~5: 基础设施搭建
*   (略，见旧版)

### Phase 7: 深度推理集成 (2025-12-07)
*   **Competitor Layering**: 竞品分层。
*   **Brand Injection**: 品牌库注入。

### Phase F: 架构升级与数据深度 (2025-12-10)
*   **双模式引擎**: 引入 `--mode` 参数，彻底解决 B2B/B2C 社区混杂问题。
*   **数据灵魂**: 增加 `price_analysis` (钱) 和 `usage_context` (地) 维度。
*   **智能过滤**: 引入上下文感知黑名单，解决泛社区 (如 `r/AskWomen`) 的误杀/漏杀问题。

### Phase G: 信号密度与解决方案 (2025-12-10)
*   **算法升级**: 引入 "Topic Relevance Density" (话题浓度)，大幅提升垂直小众社区权重。
*   **价值闭环**: 新增 `SolutionSignal` 挖掘，从只提痛点进化到给出解法。

### Phase H: 用户画像生成 (2025-12-10)
*   **Persona Injection**: 激活 `PersonaGenerator`，在 `facts.json` 中注入结构化的社区用户画像 (Label/Traits/Strategy)。

---

## 4. 核心能力 (当前现状)

1.  **全维度情报**: `facts.json` 现在包含：基础统计 + 痛点聚类 + **价格锚点** + **使用场景** + **解决方案** + **用户画像**。
2.  **角色感知**: 系统知道你是想看“产品”还是想看“运营”，自动切换数据源。
3.  **语境感知**: 系统知道“猫粮”不该看情感版，“产后恢复”必须看情感版。
4.  **精准排名**: 告别大社区霸榜，硬核垂直社区优先。

---

## 5. 未来路线图 (Phase I: 语义匹配与实时化)

### 5.1 语义匹配升级 (Hybrid Matcher)
*   **目标**: 激活 `backend/app/services/analysis/hybrid_matcher.py`。
*   **价值**: 用向量匹配替代正则，识别“隐形竞品”和“长尾痛点”。

### 5.2 实时监控 (Real-time)
*   **目标**: 建立 Brand/Topic 级别的实时监控看板。

---

**注**: 本文档作为项目的长期记忆。详细执行细节见 `docs/archive/Facts数据优化全记录_20251210.md`。
