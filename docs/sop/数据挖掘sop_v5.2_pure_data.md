# Reddit Signal Scanner SOP v5.2 (Pure Data Edition)

> **版本**: v5.2
> **代号**: Pure Data (极致提纯)
> **更新日期**: 2025-12-06
> **核心资产**: 向量混合检索 + 意图评分引擎 + **四层防御体系** + 向量去重
> **文档目标**: 记录从 v5.1 升级至 v5.2 后的完整数据提纯能力。


---

## 1. 系统核心架构：五步分析漏斗 (The 5-Step Pipeline)

v5.1 版本将原有的线性脚本重构为精密的“漏斗模型”。数据从源头进入，经过层层过滤与量化，最终产出高价值情报。

| 阶段 | 核心任务 | 关键组件与配置 | 价值与变化 (Value Add) |
| :--- | :--- | :--- | :--- |
| **Step 1: 意图解析** | 用户中文需求 -> 英文定位 | `LLM Semantic Mapping`<br>`BlacklistConfig` | **双向锁定**：<br>1. **翻译**：将“解压”翻译为 `fidget`, `stress`。<br>2. **防御**：加载 `community_blacklist.yaml`，**前置拦截**已知垃圾社区（如 `r/funny`）。 |
| **Step 2: 混合检索** | 全库扫描 (Recall) | `Vector Embedding (Phase 5)`<br>`Postgres tsvector` | **双模捕获 (Hybrid Search)**：<br>1. **显性**：SQL 关键词硬匹配。<br>2. **隐性**：**向量联想搜索**（距离 < 0.4），捕捉“没提关键词但意图相关”的帖子。 |
| **Step 3: 提纯降噪** | 清洗与初筛 (Filter) | `Text Classifier`<br>`Deduplicator`<br>`Tier Check` | **三重过滤**：<br>1. **分类器**：踢掉 Promotion/Giveaway 广告评论。<br>2. **Tier**：剔除痛点密度 < 0.1 的“死水”社区。<br>3. **去重**：基于 `deduplication.yaml` 阈值，合并重复评论。 |
| **Step 4: 价值量化** | **算分** (Scoring) | `Opportunity Scorer`<br>`Scoring Rules` | **意图识别 (Intent Engine)**：<br>不再只看痛点密度，而是计算 **Intent Score**。<br>识别 "Willing to pay" (+分) vs "Hate it" (-分)，输出最终 **Opportunity Score**。 |
| **Step 5: 交付** | 报告生成 (Delivery) | `Omni-Prompt`<br>`Pain Tree JSON` | **双模交付**：<br>1. **决策报告**：Markdown 深度文案（含机会卡片）。<br>2. **结构数据**：`pain_tree_v1.json` (Root->Symptom->Evidence) 用于可视化。 |

---

## 2. 配置中枢指南 (Configuration Control)

所有核心逻辑参数均已从代码中剥离，由项目根目录下的 `config/` 文件控制。

### 2.1 防御配置：`config/community_blacklist.yaml`
**用途**: 定义绝对排除的社区名单。
**逻辑**: 在 Step 1 阶段，凡是命中此名单的社区，无论相关性多高，直接丢弃。
```yaml
blacklist:
  - r/funny          # 泛娱乐，无商业价值
  - r/gaming         # 游戏干扰
  - r/FreeKarma4U    # 刷分垃圾场
```
**操作**: 发现报告混入无关社区时，直接追加到此文件。

### 2.2 价值配置：`config/scoring_rules.yaml`
**用途**: 定义 Opportunity Scorer 的评分权重。
**逻辑**: 在 Step 4 阶段，系统对 Top 评论进行正则匹配，计算 Intent Score。
```yaml
positive_keywords:
  - keyword: "willing to pay"
    weight: 0.15      # 强购买意愿，大幅加分
  - keyword: "shut up and take my money"
    weight: 0.20
negation_patterns:
  - pattern: "don't need"
    impact: -0.5      # 否定需求，大幅扣分
```
**操作**: 觉得系统对“伪需求”判断过宽时，调高 `positive` 的门槛或增加 `negation` 扣分。

### 2.3 去重配置：`config/deduplication.yaml`
**用途**: 控制评论去重的敏感度。
**逻辑**: 在 Step 3 阶段，MinHash 相似度 > `minhash_threshold` 的评论会被合并。
```yaml
minhash_threshold: 0.85  # 默认 0.85
```
**操作**:
*   **调高 (0.95)**: 保留更多细节，报告篇幅变长。
*   **调低 (0.75)**: 强力压缩，只看最核心观点。

---

## 3. 标准作业程序 (Execution SOP)

### 3.1 环境准备 (Pre-flight)
确保本地 Postgres 数据库已启动，且 `.env` 配置正确。
```bash
# 检查系统健康度（含向量数据量检查）
make check-health
```
*预期输出*: `✅ System is READY`，且 `embeddings.total` > 0。

### 3.2 生成深度报告 (Generate Report) - V8 更新
**核心指令**:
```bash
make report-t1 TOPIC="你的话题" DESC="你的产品描述" MODEL="x-ai/grok-4.1-fast"
```
*示例*: `make report-t1 TOPIC="家用咖啡机" DESC="高性价比智能咖啡机" MODEL="x-ai/grok-4.1-fast"`

**过程日志解读**:
1.  **Config Summary**: 启动时打印 `⚙️ Config -> blacklist:20 ...`，确认配置已加载。
2.  **Mapping**: 显示 `🧠 Expanding topic... -> Mapped to: ...`，确认语义映射成功。
3.  **Scanning**: 显示 `🔍 Top community matches...`，确认混合检索命中了哪些社区。
    *   *注意观察*: 是否有 `🚫 Blocked blacklisted community` 日志，说明黑名单生效。
    *   *注意观察*: 是否有 `❌ Dropping ... Pain density too low` 日志，说明 Tier 过滤生效。
4.  **Competitor Layering**: (Phase 7) 自动将实体分为 Platform/Brand/Channel。
5.  **Quote Scoring**: (Phase 7) 自动筛选高质量金句。
6.  **Writing**: 生成最终 Markdown。

### 3.3 交付物验收 (Acceptance)
运行完成后，检查 `backend/reports/` 目录：
1.  **主报告**: `Report_宠物智能硬件_xxxx.md`。
    *   *检查点*: 机会卡片部分是否有 **Opportunity Score**，且逻辑自洽。
    *   *检查点*: "用户痛点" 部分引用的评论是否精准（无广告）。
    *   *检查点*: **需求图谱** (2.2) 是否出现了“吐槽党/工具党”等人话术语。
    *   *检查点*: **竞争格局** (3.1) 是否已剔除 Amazon 等平台词。
2.  **痛点树**: `local-acceptance/pain_tree_v1.json`。
    *   *检查点*: JSON 结构是否完整 (`root_cause` -> `symptoms`)。

### 3.4 启动爬虫服务 (Start Crawler)
**注意**: 仅靠 `make report-t1` 只能分析**现有**数据。要让数据“活”起来，必须启动后台爬虫。

**操作**:
```bash
# 启动 Celery Worker + Beat (调度器)
make start-worker
```
*   **行为**: 这是一个后台进程。它会根据 `adaptive_scheduler` 的逻辑，自动抓取高价值社区。
*   **日志**: 查看 `logs/celery.log` 确认运行状态。
*   **停止**: 使用 `pkill -f "celery worker"`。

---

## 4. 维护与注油 (Maintenance)

### 4.1 向量数据回填 (Vector Backfill)
**⚠️ 关键逻辑**: 分析脚本 (`make report-t1`) **不会**自动触发向量化。如果你刚爬取了大量新数据，必须先运行回填，否则新数据在“隐性搜索”中不可见。

**手动操作**:
```bash
# 检查当前进度 (embeddings vs posts)
make check-health

# 启动回填 (后台运行)
make backfill-embeddings
```

**自动化配置 (CronJob 推荐)**:
建议在服务器设置定时任务，每晚执行一次：
```bash
# 编辑 crontab: crontab -e
0 4 * * * cd /path/to/project && make backfill-embeddings >> logs/cron_backfill.log 2>&1
```

### 4.2 社区价值重校准 (R-F-E Profiling)
**⚠️ 核心逻辑**: 社区的活跃度和价值不是一成不变的。我们需要定期运行 **R-F-E 模型** (Recency, Frequency, Engagement) 来给社区“体检”，识别出流量型(High Traffic)和精华型(Hidden Gem)社区，从而动态调整爬虫的调度频率。

**执行指令**:
```bash
# 运行分析脚本 (基于过去 90 天数据)
python -m backend.scripts.analyze_community_value
```

**产出解读**:
*   **🔥 High Traffic**: 日均贴 > 5。需高频抓取 (每 2h)。
*   **💎 Hidden Gem**: 贴少但互动极高 (E > 50)。需精细抓取 (每 6h)。
*   **建议频次**: 每季度或在大规模补数完成后执行一次。

### 4.3 源头自动化 (Phase 6 Automation)
我们提供了工具来主动发现新矿源。

**语义发现雷达**:
```bash
# 用关键词反搜 Reddit，发现新社区
make discover-communities KEYWORDS="dropshipping,logistics"
```
*产出*: 发现符合 `Pain Density > 0.1` 的新社区后，会打印建议列表（需人工确认后加入 `community_pool`）。

### 4.3 历史数据导入 (Data Ingest)
如果你有离线的 `.jsonl` 数据文件（System B 产出），请使用此工具入库，它会自动更新水位线，让 Celery 平滑接手。

```bash
# 导入历史数据并更新水位线
make ingest-jsonl FILE="data/history.jsonl" COMMUNITY="r/ecommerce"
```
*注意*: 必须指定 COMMUNITY，且文件格式需符合 Schema。

---

## 5. 通过 v1.0 强化计划获得了什么？(Achievements)

通过执行《分析引擎系统强化开发计划 v1.0》，我们将系统从 v4.5 升级到了 v5.1，获得了：

1.  **防御力 (Defense)**: 以前靠运气过滤垃圾社区，现在靠 `blacklist.yaml` 和 `classifier` **确定性地拦截**。
2.  **判断力 (Intelligence)**: 以前只数“骂声”（痛点密度），现在能算“买意”（Intent Score）。**商业机会识别准确率大幅提升**。
3.  **感知力 (Perception)**: 彻底激活 Phase 5 向量能力，能捕捉到“没提关键词但相关”的**隐性信号**。
4.  **控制力 (Control)**: 核心参数全部配置化，无需修改代码即可调整系统行为。

---

## 6. v5.2 升级：极致数据提纯 (Pure Data Upgrade)

通过执行 **Operation Pure Data**，我们将系统从 v5.1 升级到 v5.2，新增了：

### 6.1 四层防御网
| 层级 | 能力 | 说明 |
|------|------|------|
| **Layer 1** | 社区/作者黑名单 | 封号比封词更有效 |
| **Layer 2** | 正则模式过滤 | 拦截变种广告 |
| **Layer 3** | 向量语义去重 | 识别一稿多投 (Crosspost) |
| **Layer 4** | 垃圾精细分类 | Spam_Ad / Spam_Crypto / Spam_Bot |

### 6.2 新增数据库字段
| 字段 | 类型 | 用途 |
|------|------|------|
| `is_duplicate` | boolean | 标记重复帖子 |
| `duplicate_of_id` | bigint | 指向原帖 |
| `spam_category` | varchar | 垃圾分类标签 |

### 6.3 新增维护脚本
```bash
# 向量去重扫描
python backend/scripts/mark_duplicates.py --limit 1000 --threshold 0.95

# 垃圾成分分析
python backend/scripts/maintenance/analyze_spam_composition.py --days 30

# 作者拉黑建议
python backend/scripts/suggest_author_blacklist.py --limit 5000
```

### 6.4 报告自动过滤
`t1_stats.py` 中的关键查询已自动过滤重复帖子，确保报告数据纯净。

---

## 7. Phase 7: 深度推理与人话报告 (Deep Reasoning & Humanized Report)

> **代号**: Omni-Analyst V8 (全能分析师)  
> **上线日期**: 2025-12-07  
> **核心能力**: 竞品精准分层 + 智能引言 + 极致人话

### 7.1 核心变更
1.  **Prompt Humanization**: 彻底废弃 "Survival/Efficiency" 等术语，改用 "吐槽/避坑党"、"找货/工具党" 等卖家黑话。禁止出现任何 JSON 变量名。
2.  **Competitor Layering**: 引入 `competitor_layers.yml` 配置文件，结合 SQL ILIKE 和 LLM 回溯，精准将实体分为 Platform, Brand, Channel。彻底解决 "Amazon 既是渠道也是品牌" 的混淆。
3.  **Smart Quotes**: 引入 `QuoteExtractor`，基于情感强度和关键词相关度，自动筛选最具感染力的"用户之声"，并自动附带 🔗 帖子链接。
4.  **Grok Model**: 默认模型切换为 **x-ai/grok-4.1-fast**，利用其更强的逻辑推理和自然语言能力，大幅提升报告的可读性和去重能力。

### 7.2 品牌库资产 (Brand Library)
已注入 **1600+** 个垂直领域品牌到 `semantic_terms` 表，覆盖：
*   Ecommerce (SaaS, Logistics)
*   Food (Coffee, Snacks)
*   Home (Furniture, Appliances)
*   Outdoor (Gear, Apparel)
*   Tools (EDC, Power Tools)
*   Frugal (Discount Stores)
*   Family (Baby Gear)

### 7.3 维护指南
*   **分层规则**: 修改 `backend/config/entity_dictionary/competitor_layers.yml`。
*   **品牌扩充**: 修改 `backend/config/semantic_sets/brands_*.yml` 并运行 `migrate_brands.py`。

---

## 8. Phase 8: 性能与稳定性 (Performance & Stability)

*   **Query Optimization**: 重构 `fetch_topic_relevant_communities`，拆分全文检索与向量检索，创建 GIN 索引，解决 365 天全量查询超时问题。
*   **Data Alignment**: 修复 `TierIntelligence` 时间窗口逻辑，确保社区筛选与报告分析周期一致。修复 `Pain Cluster` 标签过滤，兼容 `Survival` 标签。

---

**文档维护**: 十一 (Architect Agent)  
**最后更新**: 2025-12-07