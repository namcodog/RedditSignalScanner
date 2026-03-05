# Phase 226 - 爆贴速递（HotPost）模块全流程诊断与首轮验收

日期：2026-02-28

## 发现了什么？

### 1. 架构理解

三种分析模式（Prompt）各解决一个核心问题：

| 模式 | 解决什么问题 | 对应 Prompt |
|------|------------|-------------|
| **Trending** | "现在什么热？" — 识别升温话题、高频关键词、社区分布 | `TRENDING_PROMPT` |
| **Rant** | "对手哪里烂？" — 聚类痛点、严重程度、迁移意向、竞品对比 | `RANT_PROMPT` |
| **Opportunity** | "什么值得做？" — 未满足需求、支付意愿、现有方案缺陷、MVP 建议 | `OPPORTUNITY_PROMPT` |

核心流程：`export_hotpost_report.py` → `HotpostService.search()` → Reddit API 采集 → 规则引擎打分/过滤 → (可选) LLM 深度分析 → `export_markdown_report()` 输出

### 2. Codex 沙箱限制（阻塞项）

Codex `--full-auto` 使用 `workspace-write` 沙箱，**不允许连接外部端口**（PostgreSQL/Redis/Reddit API 都走 localhost），导致三种模式全部报 `PermissionError: [Errno 1] Operation not permitted`。

**结论**：HotPost 模块依赖 DB+Redis+外部 API，Codex 沙箱模式无法直接执行，必须由本地 shell 运行。

### 3. 首轮执行 — 关键词歧义导致全部跑偏（v1）

使用查询词 `"adult toys"` 执行三种模式，**三份报告全部不合格**：

| 模式 | 预期 | 实际 | 判定 |
|------|------|------|------|
| Trending | 成人情趣用品市场趋势 | r/toys 的怀旧玩具讨论 | ❌ |
| Rant | 情趣用品品牌吐槽和痛点 | 3条不相关帖子 | ❌ |
| Opportunity | 情趣用品市场未满足需求 | AITAH、狗骨灰等完全无关帖子 | ❌ |

**根因**：
- `"adult toys"` 是歧义词，Reddit 搜索匹配到"成人玩儿童玩具"而非"成人用品"
- `search_subreddits(include_nsfw=False)`（service.py L489）过滤掉了目标社区
- 自动发现的社区是 r/toys，而非 r/SexToys

### 4. 修复：增加 subreddit 定向参数

让 Codex 修改了 `export_hotpost_report.py`，新增三个参数：
- `--subreddits`：指定目标社区列表
- `--time-filter`：控制时间窗口
- `--limit`：控制最大帖子数

修改文件：`backend/scripts/export_hotpost_report.py`（语法检查通过）

### 5. 二轮执行 — 定向社区后数据对了，但报告价值不达标（v2）

使用精确关键词 + 指定社区重新执行：

**Trending（v2）**
- 命令：`"sex toys vibrator dildo" --subreddits r/SexToys r/sextoys r/PleasureProducts r/TwoXChromosomes r/sexover30`
- 结果：36条帖子 ✅ 主题正确（性生活/性玩具相关）
- 问题：TwoXChromosomes 占比 100%，大社区霸占了排序；r/SexToys 的精准内容被稀释

**Rant（v2）**
- 命令：`"sex toys vibrator dildo complaint broken quality" --subreddits r/SexToys r/sextoys r/TwoXChromosomes r/sexover30 r/sex`
- 结果：仅 2 条帖子 ❌ 样本严重不足
- 问题：rant 信号词（regret/nightmare/broken）面向通用场景，不适配性玩具领域

**Opportunity（v2）**
- 命令：`"sex toys recommendation best vibrator looking for" --subreddits r/SexToys r/sextoys r/TwoXChromosomes r/sexover30 r/sex r/AskWomen`
- 结果：35条帖子但内容跑偏（性暴力、电影评论、仇男情绪）❌
- 问题：搜索词太宽，"sex" + "looking for" 命中大量无关帖

### 6. 缺失 LLM API Key

`.env` 中无 `OPENROUTER_API_KEY`、`OPENAI_API_KEY` 或 `XAI_API_KEY`，所有报告只有规则引擎输出，无话题聚类/趋势判断/商业洞察等 LLM 深度分析。

## 是否需要修复？

**是，有 4 个维度需要修复：**

### P0 - LLM API Key 配置
- 没 Key 就没有深度洞察，报告只是原始数据堆砌

### P1 - 搜索策略优化
- 大社区霸占排序问题：需要引入 Signal Density（话题浓度）权重到 trending 排序
- Rant 信号词不匹配：需要按行业定制信号词表
- Opportunity 关键词太宽：搜索词策略需要更精准

### P2 - NSFW 过滤逻辑
- `include_nsfw=False` 在自动发现社区时会误杀 NSFW 类目标社区
- 应改为：当用户指定社区时跳过 NSFW 过滤；或提供 `--include-nsfw` 参数

### P3 - 查询消歧
- 系统缺乏语义消歧能力，歧义关键词（如 "adult toys"）会导致整个流程跑偏
- 需要 LLM 预处理步骤：将用户意图转化为精准搜索词 + 匹配社区

## 精确修复方法

| 优先级 | 修复项 | 做法 | 涉及文件 |
|--------|--------|------|---------|
| P0 | 配 LLM Key | 在 `.env` 中补 `OPENROUTER_API_KEY` 或 `XAI_API_KEY` | `.env` |
| P1a | 大社区稀释 | trending 排序引入话题浓度（已有 Signal Density Phase G 代码，需确认是否激活） | `service.py` |
| P1b | Rant 信号词 | 为不同行业定制信号词表，或让 LLM 动态生成行业关键词 | `rules.py`, `keywords.py` |
| P1c | Opportunity 精度 | 启用 `ENABLE_HOTPOST_RELEVANCE_FILTER` + 收紧 relevance_terms | `service.py` L540-559 |
| P2 | NSFW 过滤 | 当 `subreddits` 指定时跳过 NSFW 过滤，或新增参数 | `service.py` L489 |
| P3 | 查询消歧 | `resolve_hotpost_query()` 激活 LLM 翻译/消歧 | `query_resolver.py` |

## 验收标准（什么算修好了）

1. 同一个提问 `"成人玩具 US/EU 市场"`，三种模式命中的帖子 ≥80% 与情趣用品直接相关
2. Trending 报告能看到具体品牌/品类/形态的升温趋势，而非泛化的性话题讨论
3. Rant 报告有 ≥10 条真实吐槽帖，痛点聚类 ≥3 个维度（材质/耐用性/包装/物流/定价）
4. Opportunity 报告给出 ≥3 个可落地的机会方向，带具体人群/痛点/未满足需求证据
5. LLM 分析层有深度洞察输出（话题聚类、趋势判断、竞品分析、MVP 建议）

## 下一步系统性计划

1. **配 LLM Key** → 重跑三模式，对比有/无 LLM 的报告质量差异
2. **搜索策略修复** → 优化关键词翻译 + 社区定向 + 信号词行业适配
3. **NSFW + 消歧修复** → 支持 NSFW 社区 + LLM 消歧
4. **第三轮验收** → 用完整提问重跑，以验收标准逐项对标

## 这次执行的价值

- 完整走通了 HotPost 模块的端到端流程，验证了管道可用性
- 精准定位了 4 个层次的问题（API配置 / 搜索策略 / 过滤逻辑 / 语义消歧）
- 修复了 `export_hotpost_report.py` 脚本，增加了 `--subreddits / --time-filter / --limit` 参数
- 为后续修复建立了清晰的优先级和验收标准

## 关键证据文件

| 文件 | 说明 |
|------|------|
| `reports/hotpost/adult_toys_trending.md` | v1 trending 报告（跑偏，命中 r/toys） |
| `reports/hotpost/adult_toys_rant.md` | v1 rant 报告（3条不相关帖子） |
| `reports/hotpost/adult_toys_opportunity.md` | v1 opportunity 报告（完全跑偏） |
| `reports/hotpost/adult_toys_trending_v2.md` | v2 trending 报告（主题对了，大社区霸占） |
| `reports/hotpost/adult_toys_rant_v2.md` | v2 rant 报告（仅2条，信号词不匹配） |
| `reports/hotpost/adult_toys_opportunity_v2.md` | v2 opportunity 报告（内容跑偏） |
| `backend/scripts/export_hotpost_report.py` | 已修改：新增 subreddits/time-filter/limit 参数 |
