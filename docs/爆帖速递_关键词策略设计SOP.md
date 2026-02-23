# 爆帖速递：关键词策略设计与问题结构化 SOP

> 版本：v1.2  
> 日期：2026-02-03  
> 基于案例：「一张造」品牌海外市场洞察

---

## 📌 文档目的

本文档建立爆帖速递（Hotpost）报告生成的**问题设计标准流程**，帮助用户：
1. 理解三种模式（Trending/Rant/Opportunity）的本质区别
2. 掌握关键词设计原则
3. 形成可复用的迭代优化思路

---

## 一、问题设计流程总览

```
1. 确定品牌定位 → 2. 中文→英文解析（系统自动） → 3. 选择活跃品类 → 4. 设计三组关键词 → 5. 确定社区策略 → 6. 迭代优化
```

> 说明：用户可直接输入中文，系统会自动做“关键词解析/转译”，并用英文去检索 Reddit。

---

## 二、三种模式的本质区别

| 模式 | 本质问题 | 用户行为 | 适合的关键词类型 |
|------|---------|---------|----------------|
| **Trending** | "大家在聊什么？" | 讨论/分享/展示 | **品类名词** |
| **Rant** | "大家在骂什么？" | 吐槽/抱怨/求助 | **品类 + 负面词** |
| **Opportunity** | "大家在找什么？" | 寻求/推荐/询问 | **需求动词 + 场景** |

### 模式选择指南

| 我想了解... | 选择模式 |
|------------|---------|
| 这个品类在 Reddit 上有没有热度？ | Trending |
| 用户对现有产品有什么不满？ | Rant |
| 用户在寻找什么类型的解决方案？ | Opportunity |

---

## 三、关键词设计原则

### 3.1 核心原则

| 原则 | 说明 | 示例 |
|------|-----|------|
| **长度控制** | 3-5 个词组最佳，太长会匹配失败 | ✅ `paint by numbers kit` ❌ `relaxing creative hobby for anxiety stress relief` |
| **OR 语法** | 用于组合多个词组 | `hobbies for anxiety OR creative hobby recommendation` |
| **用户视角** | 用用户真实提问方式 | ✅ `hobbies for anxiety` ❌ `therapeutic hobby` |
| **品类精准** | 选择活跃度高的品类 | ✅ `paint by numbers` ❌ `kintsugi` (太小众) |

**系统预检规则（新增）**
- **关键词长度预检**：单条关键词超过 50 字符，系统会自动拆分为多条查询并合并去重，同时提示“已拆分为 N 次查询，会消耗更多 API 次数”。

### 3.2 三种模式的关键词公式

| 模式 | 公式 | 示例 |
|------|-----|------|
| **Trending** | `[品类名词] + kit/hobby/DIY` | `paint by numbers kit OR art kit adult` |
| **Rant** | `[品类名词] + quality/disappointed/cheap/problem` | `paint kit quality OR kit materials disappointing` |
| **Opportunity** | `[需求动词] + [场景/人群]` | `hobbies for anxiety OR stress relief craft` |

---

## 四、社区策略

### 4.1 策略选择

| 模式 | 社区策略 | 原因 |
|------|---------|-----|
| **Trending** | **限定社区**（5-10个） | 品类讨论集中在垂直社区，限定可减少噪音 |
| **Rant** | **限定社区**（5-10个） | 吐槽集中在使用者社区 |
| **Opportunity** | **不限社区** | 需求分散在各种生活/心理/职业社区 |

> 系统限制：社区最多 10 个（超过会被拒绝）。

### 4.2 社区发现方法

1. **直接搜索**：在 Reddit 搜索品类关键词，看结果主要来自哪些社区
2. **社区浏览**：访问 `reddit.com/r/[品类名]` 看是否存在
3. **关联发现**：从一个社区的侧边栏找到相关社区推荐

### 4.3 系统默认检索参数（新增）

| 参数 | Trending | Rant | Opportunity | 说明 |
|------|---------|------|-------------|------|
| time_filter | all | all | month | 默认时间范围，确保样本量 |
| sort | top | top | relevance | 机会模式优先相关性 |
| limit | 30（上限 100） | 30（上限 100） | 30（上限 100） | 单次返回上限 |
| subreddits | 0-10 个 | 0-10 个 | 不限（可为空） | 为空时系统自动推荐 5 个 |
| 关键词拆分 | >50 字符自动拆分 | 同上 | 同上 | 拆分后合并去重 |

> 注：实际参数以系统配置为准，默认值可通过环境变量覆盖。

---

## 五、迭代优化决策树

```
结果太少？
├── 品类太小众 → 换更活跃的品类
├── 限定社区太严格 → 减少社区数量或不限社区
├── 关键词太长 → 缩短到 3-5 个词组
└── 双重过滤 → Opportunity 模式不限社区

结果噪音多？
├── 关键词太泛 → 增加品类限定词
├── 无社区限制 → Trending/Rant 限定垂直社区
└── 匹配到游戏/影视 → 添加排除词或换关键词

完全无结果？
├── 关键词太长 → Reddit API 可能整体匹配失败
├── 社区不活跃 → 换到更大的泛社区
└── 品类在 Reddit 无讨论 → 考虑换数据源
```

---

## 六、完整案例：「一张造」品牌

### 6.1 品牌定位
- **产品**：艺术类 DIY 套装（文物修复、敦煌艺术、治愈手工）
- **目标**：了解海外用户对此类产品的讨论、痛点、需求

### 6.2 关键词迭代过程

#### V1 初版（关键词太泛）

| 模式 | 关键词 | 结果 | 问题 |
|------|-------|------|-----|
| Trending | `DIY craft kit traditional art cultural craft...` | 30条 | 噪音多 |
| Rant | `DIY kit disappointed craft kit problem...` | 10条 | 噪音多 |
| Opportunity | `relaxing craft recommendation therapeutic DIY...` | 22条 | 噪音多 |

**教训**：关键词太泛，无社区限制 → 匹配到游戏、影评等不相关内容

---

#### V2（限定社区 + 聚焦金缮）

| 模式 | 关键词 | 社区 | 结果 | 问题 |
|------|-------|-----|------|-----|
| Trending | `kintsugi repair kit ceramic mending...` | 5个 | 2条 | 金缮太小众 |
| Rant | `kit disappointed cheap materials poor quality...` | 5个 | 19条 ✅ | - |
| Opportunity | `relaxing craft recommendation therapeutic hobby...` | 5个 | 5条 | 数据量有限 |

**教训**：金缮品类讨论量本身有限，需要换更活跃的品类

---

#### V3（放宽社区 + OR 语法）

| 模式 | 关键词 | 社区 | 结果 | 问题 |
|------|-------|-----|------|-----|
| Trending | `pottery repair OR ceramic restore OR broken pottery gold...` | 10个 | 1条 | 双重过滤太严格 |
| Rant | `craft kit quality OR DIY kit instructions...` | 10个 | 0条 | 双重过滤太严格 |
| Opportunity | `relaxing hobby recommendation OR creative activity stress relief...` | 10个 | 0条 | 双重过滤太严格 |

**教训**：限定社区 + 精确关键词 = 交集为空

---

#### V4（不限社区）

| 模式 | 关键词 | 社区 | 结果 | 发现 |
|------|-------|-----|------|-----|
| Trending | `kintsugi kit OR pottery repair kit...` | 不限 | 1条 | 金缮确实太小众 |
| Rant | `craft kit disappointed OR DIY kit cheap quality...` | 不限 | 23条 ✅ | 匹配到游戏等噪音 |
| Opportunity | `relaxing hobby recommendation OR stress relief craft...` | 不限 | 10条 ✅ | 能拿到结果 |

**教训**：需要换一个更活跃的品类

---

#### V5（换赛道：Paint By Numbers）✅

| 模式 | 关键词 | 社区 | 结果 |
|------|-------|-----|------|
| **Trending** | `paint by numbers kit OR miniature painting hobby OR art kit adult OR mural painting DIY` | 10个社区 | **25条** ✅ |
| **Rant** | `paint kit quality OR art set cheap OR craft kit instructions OR beginner painting kit disappointed` | 10个社区 | 4条 ✅ |
| Opportunity | (关键词太长) | 10个社区 | 0条 ❌ |

**成功原因**：Paint By Numbers 是 Reddit 上活跃度最高的艺术类 DIY 品类

---

#### V6（Opportunity 优化）✅ 最终版

| 模式 | 关键词 | 社区 | 结果 |
|------|-------|-----|------|
| Trending | (沿用 v5) | 10个 | 25条 ✅ |
| Rant | (沿用 v5) | 10个 | 4条 ✅ |
| **Opportunity** | `hobbies for anxiety OR creative hobby recommendation OR paint by numbers relaxing` | **不限** | **20条** ✅ |

**成功原因**：用更接近用户真实提问方式的短关键词 + 不限社区

### 6.3 最终关键词配置

```yaml
trending:
  purpose: "发现品类热点话题"
  keywords: "paint by numbers kit OR miniature painting hobby OR art kit adult OR mural painting DIY"
  subreddits:
    - r/paintbynumbers
    - r/crafts
    - r/minipainting
    - r/Art
    - r/DIY
    - r/PaintingTutorials
    - r/learnart
    - r/somethingimade
    - r/ArtFundamentals
    - r/Illustration
  strategy: "限定社区 + 品类名词"

rant:
  purpose: "挖掘用户痛点"
  keywords: "paint kit quality OR art set cheap OR craft kit instructions OR beginner painting kit disappointed"
  subreddits: (同 trending)
  strategy: "限定社区 + 品类 + 负面词"

opportunity:
  purpose: "发现需求机会"
  keywords: "hobbies for anxiety OR creative hobby recommendation OR paint by numbers relaxing"
  subreddits: null  # 不限社区
  strategy: "不限社区 + 需求动词 + 场景"
```

---

## 七、核心洞察总结

### 7.1 品类热度 (Trending)
- Paint By Numbers 是 Reddit 上活跃度最高的艺术类 DIY 品类
- 核心社区：`r/paintbynumbers` (占比 92%)
- 热点话题：购物指南、合法网站、技巧教程、作品分享

### 7.2 用户痛点 (Rant)

| 痛点 | 占比 | 商业影响 |
|------|-----|---------|
| 颜料附着力差 | 30% | 需要 gesso 预处理 |
| 刷子质量低 | 15% | 用户自购替换 |
| 说明书不清 | 15% | 需要视频教程 |
| 工具噱头感 | 20% | 需要实用演示 |

### 7.3 需求机会 (Opportunity)
- **目标人群**：ADHD 女性
- **核心需求**：低门槛、放松型创意爱好
- **替代品短板**：Diamond art "太小太精细"
- **差异化机会**：大颗粒、低细节、ADHD 友好设计

---

## 八、常见问题 FAQ

### Q1: 关键词用中文还是英文？
**A**: 搜索 Reddit 必须用英文，但用户可以用中文输入，系统会自动转译为英文关键词。

### Q2: 社区名称格式是什么？
**A**: 统一使用 `r/社区名` 格式，如 `r/paintbynumbers`。系统会自动处理大小写。

### Q3: OR 语法怎么用？
**A**: 用于组合多个词组，表示"或"关系。例如 `A OR B OR C` 会匹配包含 A 或 B 或 C 的帖子。

### Q4: 为什么 Opportunity 要不限社区？
**A**: 因为用户的需求（如"解压爱好推荐"）可能出现在任何社区（心理、职业、生活方式等），不像品类讨论集中在垂直社区。
> 风险提示：不限社区会带来噪音和更高 API 消耗，建议先不限社区拿结果，再用关键词过滤降噪。

### Q5: 如何判断品类是否活跃？
**A**: 
1. 在 Reddit 搜索品类关键词，看结果数量
2. 检查是否有专属社区（如 r/paintbynumbers）
3. 查看相关社区的成员数和活跃度

### Q6: 默认时间范围是什么？
**A**: Trending/Rant 默认 all（全量），Opportunity 默认 month（最近一个月）。

### Q7: 社区上限与自动发现？
**A**: 用户最多可传 10 个社区；不传时系统会自动推荐 5 个相关社区。

### Q8: API 频率会不会很贵？
**A**: 系统有默认限流（例如 100 次/10 分钟），拆分关键词或不限社区会提高调用次数。

---

## 九、输出物清单

| 文件 | 路径 | 说明 |
|------|-----|------|
| 整合报告 | `reports/yizhangzao_整合报告_v1.md` | 最终版完整报告 |
| Trending 报告 | `reports/yizhangzao_v5_trending.md` | 25条帖子 |
| Rant 报告 | `reports/yizhangzao_v5_rant.md` | 4条帖子 |
| Opportunity 报告 | `reports/yizhangzao_v6_opportunity.md` | 20条帖子 |
| JSON 数据 | `reports/yizhangzao_v5_*.json` | 原始数据 |

---

## 十、模块优化建议

基于「一张造」案例的实践经验，从**数据质量、算法逻辑、用户体验、工程健壮性**四个维度提出优化建议：

### 10.1 数据质量层

| 问题 | 现象 | 建议 | 优先级 |
|------|-----|------|-------|
| **Opportunity 匹配精度低** | 搜索 `stress relief craft` 匹配到理财帖、恐怖故事等不相关内容 | **增加后置过滤**：对返回的帖子做语义相关性打分，过滤低相关帖 | P2 |
| **垂直品类数据稀疏** | 金缮(kintsugi)只有 1-2 条结果 | **引入历史数据库**：先在本地 DB 积累数据，再做检索，不完全依赖实时 API | P3 |
| **社区发现不智能** | 用户需要手动指定社区 | **自动社区推荐**：根据关键词自动推荐相关社区（可用 LLM 或规则库） | P1 |

### 10.2 算法逻辑层

| 问题 | 现象 | 建议 | 优先级 |
|------|-----|------|-------|
| **关键词过长导致 0 结果** | V5 Opportunity 关键词太长，Reddit API 返回空 | **关键词长度预检**：超过 50 字符自动拆分或警告 | P0 |
| **OR 语法支持不稳定** | Reddit 对复杂布尔表达式支持有限 | **多次查询合并**：拆成多个单独查询，后端合并去重 | P2 |
| **模式与社区策略绑定** | Trending/Rant 应限社区，Opportunity 应全站 | **智能社区策略**：根据模式自动调整社区策略，而非让用户选 | P1 |
| **默认时间范围偏窄** | Trending 只看周内样本太少 | **默认 time_filter=all**：保证样本量，必要时再缩小 | P1 |

### 10.3 用户体验层

| 问题 | 现象 | 建议 | 优先级 |
|------|-----|------|-------|
| **问题设计门槛高** | 用户不知道该用什么关键词 | **问题设计助手**：引导用户填写品类、痛点词、场景，自动生成关键词 | P1 |
| **迭代过程繁琐** | 需要手动多次调整关键词 | **A/B 测试**：支持一次输入多组关键词，自动对比效果 | P2 |
| **结果解释不足** | 用户不知道为什么是这些结果 | **增加调试信息**：返回实际使用的关键词、命中社区、过滤规则等 | P2 |

**问题设计助手 UI 示意**：

```
┌─────────────────────────────────────────────┐
│ 1. 你想分析什么品类？                         │
│    [艺术类 DIY 套装]                          │
│                                             │
│ 2. 选择分析模式：                             │
│    ○ Trending - 看品类热度                   │
│    ○ Rant - 挖用户痛点                       │
│    ○ Opportunity - 找需求机会                │
│                                             │
│ 3. 补充信息 (可选)：                          │
│    目标用户：[焦虑人群、ADHD 用户]             │
│    竞品关键词：[paint by numbers, diamond art]│
│                                             │
│ [自动生成关键词]  [直接输入关键词]             │
└─────────────────────────────────────────────┘
```

**问题设计助手输出字段清单（新增）**

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| mode | string | 选择的分析模式 | `trending` |
| keywords | string | 最终英文关键词（支持 OR 语法） | `paint by numbers kit OR art kit adult` |
| subreddits | list[string] \| null | 推荐社区列表（Opportunity 可为空） | `["r/crafts","r/paintbynumbers"]` |
| time_filter | string | 时间范围 | `all` |
| notes | list[string] | 风险/提示信息 | `["已自动拆分为 2 次查询"]` |

### 10.4 工程健壮性层

| 问题 | 现象 | 建议 | 优先级 |
|------|-----|------|-------|
| **Schema 与 LLM 输出不同步** | LLM 返回 `evidence_posts` 但 Schema 没定义，导致 ValidationError | **输出过滤 + 记录日志**：在落库前过滤多余字段并记录差异；Schema 保持严格 | P0 |
| **错误信息不友好** | 用户看到 Pydantic ValidationError 调用栈 | **错误包装**：捕获异常，返回用户友好的错误信息 | P1 |
| **缺乏预检机制** | 关键词太长/社区不存在等问题到执行时才发现 | **请求预检**：在执行前检查关键词长度、社区有效性等 | P0 |

### 10.6 痛点标签维护（新增）

为避免“所有痛点都归为 pricing/ux”，需保持痛点词库可维护：
- 质量类：`quality`（材料廉价、做工差、易损）
- 说明书/教程：`instructions`（说明书不清、缺教程）
- 物流类：`shipping`（运输破损、延迟）
- 兼容性：`compatibility`（不兼容、仅支持某平台）

词库维护入口：`backend/config/boom_post_keywords.yaml`

**Schema 宽松模式代码示例**：

```python
# backend/app/schemas/hotpost.py
from pydantic import ConfigDict

class HotpostTopic(ORMModel):
    model_config = ConfigDict(extra='ignore')  # 忽略未定义字段
    ...
```

### 10.5 优先级总览

| 优先级 | 改进项 | 价值 | 成本 |
|-------|-------|-----|------|
| **P0** | Schema 宽松模式 | 避免 LLM 输出导致阻塞 | 低 |
| **P0** | 关键词长度预检 | 避免空结果 | 低 |
| **P1** | 自动社区推荐 | 降低使用门槛 | 中 |
| **P1** | 问题设计助手 | 提升用户体验 | 中 |
| **P1** | 智能社区策略 | 减少用户决策负担 | 中 |
| **P2** | Opportunity 后置过滤 | 提升结果精度 | 中 |
| **P2** | 多查询合并 | 解决 OR 语法问题 | 中 |
| **P3** | 历史数据库检索 | 解决稀疏品类问题 | 高 |

---

## 十一、已知问题与修复记录

### 11.1 Schema 兼容性问题（已修复）

**问题 1**：`HotpostTopic.evidence_posts` 字段缺失
- **错误信息**：`ValidationError: topics.0.evidence_posts - Extra inputs are not permitted`
- **根因**：LLM 返回 `evidence_posts` 但 Schema 只定义了 `evidence`
- **修复**：在 `HotpostTopic` 中添加 `evidence_posts` 字段

**问题 2**：`UnmetNeedEvidence` 缺少多个字段
- **错误信息**：`ValidationError: unmet_needs.0.evidence.0.comments/subreddit/key_quote - Extra inputs are not permitted`
- **根因**：LLM 返回的字段多于 Schema 定义
- **修复**：在 `UnmetNeedEvidence` 中添加 `comments`、`subreddit`、`key_quote` 字段

### 11.2 运行环境问题

- **现象**：代码已修复但仍报 ValidationError
- **根因**：后端服务未重启，运行的是旧版本代码
- **解决**：重启后端服务，确保加载最新代码

---

> **文档维护**：本文档基于「一张造」案例总结，后续可根据更多案例持续迭代优化。  
> **版本**：v1.1  
> **更新日期**：2026-02-03
