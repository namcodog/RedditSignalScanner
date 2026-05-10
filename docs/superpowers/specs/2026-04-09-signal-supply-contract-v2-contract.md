# Signal Supply Contract V2
Date: 2026-04-09
Status: Draft Contract

## 1. 发现了什么

当前问题不是 Reddit 没有料，而是我们把供给合同做窄了，而且窄在最不该窄的地方：

- 题材面窄
- 社区池窄
- 关键词桶窄
- 来源模式窄
- 这些边界还被直接写在 Python 文件里

这会直接带来两个后果：

1. 运营会得到错误结论
   例如“今天 AI / 电商 / 选品没有够硬的新料”。

2. 前台容易长出“正确的废话”
   因为长期只盯同一批社区、同一批泛词、同一批话题，自然只能生成大家都知道的正确观点。

## 2. 本合同要解决什么

这份合同只解决一件事：

**把 Signal 的上游供给合同重做成 YAML-first 的配置系统。**

也就是说，后面“抓什么料”这件事，不再藏在 Python 里，而是明确配置在 YAML 里。

## 3. 硬规则

### 3.1 禁止硬编码业务边界

以下内容不允许再继续硬编码在 Python 里：

- 题材簇
- 社区池
- 关键词桶
- source mode
- pack 级 target share
- search-first / listing-first 策略

Python 业务层只允许：

- 读取 YAML
- 校验 YAML
- 组装 Reddit specs
- 做运行态审计

### 3.2 不再接受“没料”式结论

在以下条件没满足前，不允许再说：

> 今天这个领域没有够硬的新料

必须先确认：

- 该领域的候选社区池已覆盖
- 该领域的关键词桶已覆盖
- 该领域的 listing/search 两种来源都被扫过
- 该领域滚动 7 天 coverage floor 已达到

如果这些没满足，正确结论只能是：

**当前 supply contract 没覆盖到足够宽的料面。**

### 3.3 覆盖优先于润色

在 Supply Contract V2 没落好之前：

- 不再把“继续调措辞 / 调 prompt / 调 polish”当主线
- 主线必须是扩大有效题材覆盖

## 4. V2 的配置真相源

V2 先以这份 YAML 草案为单一配置入口：

- [hotpost_supply_discovery_v2.yaml](/Users/hujia/Desktop/RedditSignalScanner/backend/config/hotpost_supply_discovery_v2.yaml)

它现在是 discovery draft，下一步会变成正式运行配置。

## 5. 题材面 V2

### 5.1 AI 与自动化

不是再泛写成“AI 工具 / 上游风向”，而是至少覆盖这 5 个簇：

1. GitHub 开源项目
2. 大咖 / 关键人物路线
3. 标志性项目路线
4. agent 事故
5. 平台策略变化

具体可执行面已经写进 YAML：

- 人物：
  - Andrej Karpathy
  - Simon Willison
- 项目 / 路线：
  - AutoResearch
  - Gemini CLI
  - Vibe Kanban
  - LLM Council
  - OpenWebUI
  - CrewAI
  - LangChain
  - OLMo
  - MiniMax
- 社区：
  - `LocalLLaMA`
  - `ClaudeCode`
  - `AI_Agents`
  - `OpenAI`
  - `ClaudeAI`
  - 以及候选补充社区

### 5.2 电商与卖家

不是再泛写成“选品 / 类目风向”，而是至少覆盖这 5 个簇：

1. 宠物
2. EDC
3. 户外
4. 家居
5. 小商品

而且每个簇都要按“场景 + 摩擦”写，不再只写品类词。

例如：

- 宠物：
  - 掉毛
  - 出行
  - 公寓养宠
  - 异味
  - 耐咬
- 家居：
  - 小厨房
  - 租房友好
  - 易清洁
  - 占地
  - 噪音

### 5.3 商业增长与运营

不是再泛写成“SEO / Ads / funnel”，而是至少覆盖这 5 个簇：

1. SEO / GEO
2. Ads
3. attribution
4. funnel
5. creator / affiliate / distribution

其中 attribution 和 creator / affiliate / distribution 不能再被当成附属话题，必须视为独立簇。

## 6. 来源模式 V2

V2 不接受“默认一律 `search:relevance:week`”这种窄策略。

每个题材簇都必须明确：

- `search-first`
- `listing-first`
- `mixed`

### 基本原则

- 开源项目 / 人物路线 / agent 事故：
  - 偏 `search-first` 或 `mixed`
- 类目风向 / 卖家群体报数 / 争议型热点：
  - 偏 `listing-first` 或 `mixed`
- 实操求解法 / 特定场景购买摩擦：
  - 偏 `search-first`

## 7. 覆盖与配比规则

### 7.1 scope 级目标

先按这个目标跑：

- `AI 与自动化 = 34%`
- `商业增长与运营 = 33%`
- `电商与卖家 = 33%`

这不是为了平均主义，而是为了防止任何一个大域长期被饿死。

### 7.2 coverage floor

滚动 7 天必须满足：

- 每个 scope 至少 `12` 条候选
- 每个 scope 至少 `4` 条 listing-first 候选
- 热点 lane 至少 `6` 条候选

没达到 floor 时，不允许下“没料”结论。

## 8. 运行时边界

### 8.1 允许什么

- YAML 描述题材簇
- YAML 描述社区池
- YAML 描述关键词桶
- YAML 描述来源模式
- Python 根据 YAML 组装 specs

### 8.2 不允许什么

- 在 `topic_pack_scope_*.py` 里继续写业务供给规则
- 在 `reddit_search_spec_builder.py` 里继续写 pack 白名单和固定优先级
- 用临时补丁继续往窄 pack 里塞社区和词

## 9. 实施顺序

### Step 1

先冻结当前 Python 里的供给硬编码面，不再继续往里加新业务规则。

### Step 2

把三大 scope 的题材簇、社区池、关键词桶、来源模式搬进 YAML。

### Step 3

做一个统一的配置读取层：

- 读 YAML
- 校验 schema
- 产出 `topic packs / keyword buckets / source strategy`

### Step 4

让 `reddit_search_spec_builder.py` 只消费配置，不再拥有业务边界。

### Step 5

补一个 supply coverage 审计：

- 题材簇是否有命中
- 哪些簇长期没候选
- 哪些簇只有 search 没 listing
- 哪些簇只有 listing 没 search

## 10. 这次执行的价值是什么

这份合同的价值，不是“以后能多抓一点帖”。

真正的价值是：

**把产品从“少数社区 + 少数泛词的窄系统”，拉回“题材覆盖清楚、来源模式清楚、边界不再写死在代码里”的信号雷达。**

一句话：

**V2 的目标不是再把卡写顺一点，而是先把该看的世界看对。**
