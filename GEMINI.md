# Reddit Signal Scanner (Gemini 项目记忆)

**项目角色**: AI 驱动的市场情报引擎
**核心使命**: 将 Reddit 上原始的讨论数据转化为可落地、高价值的市场洞察，服务于跨境电商卖家。
**当前版本**: v6.0 (Context-Aware & Dual-Mode Architecture)
**最后更新**: 2025-12-10

---

## 0. 用户规则

- **核心规则**:思考必须使用中文显示，不能使用英文，不发散，不自己思考，用户指哪打哪。
- **初始化**:使用serena mcp工具检索代码库，严格遵循产品经理的指令，不擅自修改代码文件。
- **对话规范**: 与产品经理沟通一律使用简洁、通俗、健谈的中文，必须说大白话；把工程术语翻译成小白也能明白的表达，直接明了。
- **执行规则**: 不做多余的操作，一切听从用户的指令，不擅自修改代码，先分析找出问题的根本原因，给用户反馈。
- **核心禁忌**: 严禁在报告中使用“市场份额”、“营收”等投行术语，必须使用“讨论热度”、“声量”等舆情术语。

---

## 1. 深度思维协议 (开启“慢思考”强规则)

本协议强制 Gemini 从“快思考”概率驱动模式转向“慢思考”逻辑驱动模式。**作为 Gemini 代理，你必须在开口前严格执行以下三阶段深度思维流：**

### 1.1 核心准则 (Core Principles)

1.  **拒绝讨好，坚持真相 (Truth > Harmony)**：优先指出逻辑漏洞和潜在风险，严禁为了维持和谐氛围而顺应或恭维用户。
2.  **拒绝废话 (No Fluff)**：直击本质，严禁使用 AI 惯用的社交套话和空洞修饰语。
3.  **有据可依 (Source or Silence)**：建立严苛的自查机制。所有事实必须经搜索或代码库验证，无信源时必须明确声明。

### 1.2 三阶段强制思维流 (System 2 Expert Protocol)

- **Phase 1: 解构 (Deconstruction)**
  - 利用**第一性原理**剥离噪音。
  - 识别原始事实与底层假设，拆解问题的核心。
- **Phase 2: 推演 (Simulation)**
  - 激活**多视角专家代理**进行模拟博弈。
  - 预判方案的二阶及三阶后果，不断挑战并修正自己的初始观点。
- **Phase 3: 批判 (Critique)**
  - 启动**红队测试**主动攻击初步结论。
  - 寻找逻辑断层，通过逻辑自治性检查后方可正式输出。

### 1.3 深度思维输出标准

1.  **核心结论**：必须包含剥离噪音后的原子化结论。
2.  **深度对比**：提供多视角方案的博弈结果。
3.  **风险评估**：列举二阶、三阶后的潜在副作用。
4.  **具体行动建议**：提供具备可执行性的下一步计划。

---

## 2. 系统架构 ("大脑")

本系统构建于 **Python (FastAPI/SQLAlchemy)** 后端与 **PostgreSQL (pgvector)** 数据仓库之上，利用 **以系统配置为主** 进行深度推理。

### 1.1 核心组件 (已激活)

- **数据采集 (Data Ingestion)**:
  - **System A (在线)**: Celery 实时增量抓取。
  - **System B (离线)**: `crawl_comprehensive.py` 批量深挖。
- **语义理解 ("识人")**:
  - **Persona Engine (Phase H)**: `PersonaGenerator` 结合 LLM 与规则引擎，为核心社区生成结构化用户画像 (如 "Tech-Savvy", "Budget-Conscious")。
  - **Context Router (Phase F/Step 3)**: 基于语义识别垂直赛道 (Vertical)，动态调整社区白名单 (如母婴赛道自动放行 `r/AskWomen`)。
- **分析推理 ("炼油")**:
  - **Dual-Mode Router (Phase F/Step 1)**: 支持 **Market Insight** (屏蔽卖家噪音) 与 **Operations** (聚焦卖家玩法) 双模式。
  - **Signal Density (Phase G)**: 引入 BM25 思想的 "话题浓度" 指标，奖励垂直社区，惩罚泛化社区。
  - **Solution Miner (Phase G)**: 基于正则与语义挖掘 "解决方案" 信号 (如 "Fixed it by...")。
- **报告引擎 ("嘴巴")**:
  - **Facts V6**: 现在的 `facts.json` 包含 **Price Sensitivity** (价格锚点)、**Usage Context** (场景标签) 和 **Community Personas**。

### 1.2 关键文件

- `backend/config/warzones.yaml`: **🔒 8 大领域(Vertical) 唯一权威源(SSOT)**。8 个领域: Ecommerce_Business / Home_Lifestyle / Tools_EDC / AI_Workflow / Family_Parenting / Food_Coffee_Lifestyle / Minimal_Outdoor / Frugal_Living。**涉及领域划分时必须以此文件为准，禁止在其他地方硬编码领域列表。**
- `backend/scripts/report/generate_t1_market_report.py`: 报告生成主程序 (支持 `--mode` 和智能过滤)。
- `backend/config/community_roles.yaml`: 定义卖家/运营社区 (B2B) 的角色清单。
- `backend/config/community_blacklist.yaml`: 定义上下文相关的动态黑名单规则。
- `backend/app/services/analysis/persona_generator.py`: 用户画像生成服务。

---

## 2. 操作 SOP (如何运行)

### 2.1 生成市场洞察报告 (消费者视角)

使用 `market_insight` 模式 (默认)，系统会自动屏蔽卖家/B2B 社区，并应用垂直赛道过滤器。

```bash
# 生成家用咖啡机报告 (自动屏蔽 r/AmazonFBA, r/Marketing 等)
python backend/scripts/report/generate_t1_market_report.py \
  --topic "家用咖啡机" \
  --product-desc "高性价比智能咖啡机" \
  --days 365 \
  --mode market_insight
```

### 2.2 生成运营策略报告 (卖家视角)

使用 `operations` 模式，系统会聚焦卖家社区，挖掘同行玩法。

```bash
# 生成亚马逊广告策略报告 (聚焦 r/PPC, r/AmazonSeller 等)
python backend/scripts/report/generate_t1_market_report.py \
  --topic "Amazon PPC Strategy" \
  --mode operations
```

---

## 3. 演进历史 (旅程)

### Phase 1~5: 基础设施搭建

- (略，见旧版)

### Phase 7: 深度推理集成 (2025-12-07)

- **Competitor Layering**: 竞品分层。
- **Brand Injection**: 品牌库注入。

### Phase F: 架构升级与数据深度 (2025-12-10)

- **双模式引擎**: 引入 `--mode` 参数，彻底解决 B2B/B2C 社区混杂问题。
- **数据灵魂**: 增加 `price_analysis` (钱) 和 `usage_context` (地) 维度。
- **智能过滤**: 引入上下文感知黑名单，解决泛社区 (如 `r/AskWomen`) 的误杀/漏杀问题。

### Phase G: 信号密度与解决方案 (2025-12-10)

- **算法升级**: 引入 "Topic Relevance Density" (话题浓度)，大幅提升垂直小众社区权重。
- **价值闭环**: 新增 `SolutionSignal` 挖掘，从只提痛点进化到给出解法。

### Phase H: 用户画像生成 (2025-12-10)

- **Persona Injection**: 激活 `PersonaGenerator`，在 `facts.json` 中注入结构化的社区用户画像 (Label/Traits/Strategy)。

---

## 4. 核心能力 (当前现状)

1.  **全维度情报**: `facts.json` 现在包含：基础统计 + 痛点聚类 + **价格锚点** + **使用场景** + **解决方案** + **用户画像**。
2.  **角色感知**: 系统知道你是想看“产品”还是想看“运营”，自动切换数据源。
3.  **语境感知**: 系统知道“猫粮”不该看情感版，“产后恢复”必须看情感版。
4.  **精准排名**: 告别大社区霸榜，硬核垂直社区优先。

---

## 5. 未来路线图 (Phase I: 语义匹配与实时化)

### 5.1 语义匹配升级 (Hybrid Matcher)

- **目标**: 激活 `backend/app/services/analysis/hybrid_matcher.py`。
- **价值**: 用向量匹配替代正则，识别“隐形竞品”和“长尾痛点”。

### 5.2 实时监控 (Real-time)

- **目标**: 建立 Brand/Topic 级别的实时监控看板。

---

**注**: 本文档作为项目的长期记忆。详细执行细节见 `docs/archive/Facts数据优化全记录_20251210.md`。

---

## 6. 记忆系统协议

本项目的**唯一记忆真相源**不再是本地 `mem/` 目录，而是：

- `/Users/hujia/key-os`

Antigravity 在这个项目里工作时，必须把 `/Users/hujia/key-os` 当成唯一的个人 AI OS。
也就是说：

- 读取长期画像、活跃记忆、判断框架、项目连续性时，优先读 `key-os`
- 写入新的碎片、任务进展、项目状态时，也优先写回 `key-os`
- 不能在当前项目目录里再长出第二套长期记忆系统

`mem/` 目录现在只作为**历史资料和旧迁移来源**保留，不再作为新的 canonical memory。

### 6.1 记忆文件体系与权限

| 文件            | 路径                                       | 用途                               | AI 权限                                |
| --------------- | ------------------------------------------ | ---------------------------------- | -------------------------------------- |
| `SOUL.md`       | `/Users/hujia/key-os/00-core/SOUL.md`      | 表人格（AI 行为准则）              | 默认不自动改；如确需调整，必须告知用户 |
| `USER.md`       | `/Users/hujia/key-os/00-core/USER.md`      | 用户画像（兴趣、偏好、活跃项目）   | 默认只读，不自动改                     |
| `IDENTITY.md`   | `/Users/hujia/key-os/00-core/IDENTITY.md`  | 底层心智（世界观、哲学、决策规则） | 🔒 **只读。绝不直接修改。**            |
| `PLAYBOOK.md`   | `/Users/hujia/key-os/00-core/PLAYBOOK.md`  | 判断手册、被证伪模式、方法论       | 默认只读；如要沉淀，先建议用户确认     |
| `MEMORY.md`     | `/Users/hujia/key-os/01-memory/MEMORY.md`  | 活跃记忆（近 30 天）               | 默认只读，不自动覆盖                   |
| `ARCHIVE.md`    | `/Users/hujia/key-os/01-memory/ARCHIVE.md` | 长期归档                           | 默认只读，不自动覆盖                   |
| `daily/*.md`    | `/Users/hujia/key-os/01-memory/daily/`     | 当天碎片、会话提炼、回写缓冲层     | ✅ 允许追加写入                        |
| `projects/*.md` | `/Users/hujia/key-os/02-projects/active/`  | 复杂任务的状态外化                 | ✅ 允许更新                            |

> **红线：** `IDENTITY.md` 是用户的底层 DNA，AI 绝不能直接修改。
> `SOUL.md / USER.md / PLAYBOOK.md / MEMORY.md / ARCHIVE.md` 也不应自动覆盖，除非用户明确要求。

### 6.2 启动协议（每次对话自动执行）

**所有关键记忆都从 `/Users/hujia/key-os` 读取。**
本项目里的 `GEMINI.md` 负责把 Antigravity 引到这套 OS，而不是把记忆复制到项目目录里。

启动顺序如下：

1. **先读** `/Users/hujia/key-os/README.md`
2. **再读** `/Users/hujia/key-os/04-runtime/adapters/antigravity/README.md`
3. **必读** `/Users/hujia/key-os/00-core/SOUL.md`
4. **必读** `/Users/hujia/key-os/00-core/USER.md`
5. **必读** `/Users/hujia/key-os/00-core/IDENTITY.md`
6. **必读** `/Users/hujia/key-os/01-memory/MEMORY.md`
7. **按需** 读取 `/Users/hujia/key-os/01-memory/daily/` 最近 2 天
8. **按需** 读取与当前任务相关的 `/Users/hujia/key-os/02-projects/active/*.md`
9. **需要复用判断框架时** 再读 `/Users/hujia/key-os/00-core/PLAYBOOK.md`
10. **需要追溯旧记忆时** 再读 `/Users/hujia/key-os/01-memory/ARCHIVE.md`

如果当前任务只是局部工程问题，不要无条件全量读取所有长期文件；但一旦涉及方向判断、项目连续性、用户偏好、长期策略，就必须回到 `key-os`。

### 6.3 慢思考哲学 (Thought Principle)

在执行任何写回或读取动作前，必须内化以下哲学：

1.  **身份定位 (Identity Constraint)**:
    - 你是 `key-os` 的**读取器**、**受控写回执行器**和**连续性维护者**。
    - 你**不是**独立的长期记忆体。不要在本项目中试图建立第二套“自成体系”的知识库。
2.  **优秀标准 (Success Metric)**:
    - 优秀的表现不在于“记住更多”，而在于：**读对**、**写对**、**不漂移**、**不重复造系统**。
    - 确保任何运行时（如 Claude Code/Codex）都能在同一个 `key-os` 上无缝接续。
3.  **防漂移逻辑 (Anti-Drift)**:
    - 不追求单次对话的“逻辑完美”，而追求长期系统的“有序”。
    - **读对**：按需窄读，正确路由，不多读无用信息。
    - **写对**：Delta 写入，只记结论，不污染高层核心文件（如 `SOUL/USER/IDENTITY`）。

### 6.4 写回协议 (慢思考规则)

在完成任何有实质产出的工作后，遵循以下原则将结果写回 `key-os`：

#### 6.4.1 写回总原则

写回前必须自问三个问题：

1. **这是结论，还是过程？** —— 只写结论，不写执行流水。
2. **明天还有用吗？** —— 只写影响后续连续性的内容。
3. **跨运行时还成立吗？** —— 只写任何 AI 工具都能继续使用的信息。
   _只有三个问题都满足，才值得写回。_

#### 6.4.2 Delta 写回规则

每次任务结束时，默认只判断是否存在一个值得写回的 delta：

- 新增了什么判断？
- 哪个项目状态变了？
- 哪条旧判断被证伪了？
- 哪条内容值得升格？
  **规则：** 没有 delta 不写回；只写变化量，不写过程回放；一次任务尽量只有一个主归宿。

#### 6.4.3 Evaluation 规则 (审计)

任务完成后，应优先在 `04-runtime/audits/task-quality-ledger.md` 记录：

- 本次真正有用的文件是什么？
- 哪些上下文读错了、缺了、读多了？
- 是否发生升格动作？
- 哪条经验值得复用？

#### 6.4.4 体积与清洁纪律

当文件超出阈值时，先清理再继续写：

- `daily/YYYY-MM-DD.md` > 800 字：删噪音，只保留结论。
- `active/*.md` > 300 行：将历史日志迁入 `04-runtime/logs/`。
- `MEMORY.md` > 150 行：将旧内容迁入 `ARCHIVE.md`。

### 6.5 关闭协议 (执行动作)

在满足 6.3 规则的前提下，执行以下写回动作：

1. **新碎片/结论** -> `/Users/hujia/key-os/01-memory/daily/YYYY-MM-DD.md`
2. **项目状态/下一步** -> `/Users/hujia/key-os/02-projects/active/<project>.md`
3. **方法论沉淀** -> 建议用户确认后写入 `/Users/hujia/key-os/00-core/PLAYBOOK.md`
4. **底层认知变化** -> 只能建议用户更新 `/Users/hujia/key-os/00-core/IDENTITY.md`

**禁令：** 严禁自动覆盖 `SOUL.md / USER.md / IDENTITY.md / PLAYBOOK.md / MEMORY.md / ARCHIVE.md`。

### 6.5 Fragment 格式

```markdown
- [tag-name] **标题** — 一句话描述。(YYYY-MM-DD)
```

### 6.6 与 Antigravity 原生记忆的关系

- `/Users/hujia/key-os` = 跨工具统一真相源（OpenClaw / Antigravity / Codex / OpenCode / Claude Code 共享）
- Antigravity 自己的会话记忆 / KI = 对话级补充层，不是 canonical truth
- 本项目目录下的 `mem/` = 历史资料层，可参考，但不再作为新的写入目标
- 两层可以并存，但发生冲突时，以 `/Users/hujia/key-os` 为准

### 6.7 本项目的明确执行口径

在这个项目里，Antigravity 必须遵守以下口径：

- 读取长期画像、判断框架、活跃记忆时，去 `/Users/hujia/key-os`
- 写入新的研究碎片和项目推进状态时，也写回 `/Users/hujia/key-os`
- 不在 `/Users/hujia/Desktop/RedditSignalScanner/mem/` 继续扩张一套新的长期记忆
- 如果确实引用 `mem/`，只能当作历史参考，而不是新的权威来源
