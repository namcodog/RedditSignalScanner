# 2026-04-09 Signal Supply Tavily Scan V1

## 先说结论

当前 supply 的问题不是 Reddit 没料，而是我们把“值得持续监控的题材面”定义得太窄，而且窄在三层：

- 社区池太少
- 关键词桶太泛
- 来源模式太单一

Tavily 这轮侦查的价值，不是给出完美名单，而是把“我们漏掉了哪些长期值得监控的线”先捞出来，证明当前 contract 确实有结构性缺口。

## AI 方向捞到的关键信号

### 社区线索

- 已证明确实该进长期池：
  - `LocalLLaMA`
  - `ClaudeCode`
  - `AI_Agents`
  - `OpenAI`
  - `ClaudeAI`
- 候选补充社区：
  - `perplexity_ai`
  - `singularity`
  - `aicuriosity`
  - `claudeskills`

### 人物 / 项目 / 路线线索

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

### 说明

这直接证明了一个问题：我们现在的 AI supply 不是没有“大咖 / 项目 / GitHub 开源”线，而是压根没把这些名字和路线写进采集合同。

## 电商方向捞到的关键信号

### 社区线索

- 卖家侧：
  - `AmazonSeller`
  - `FulfillmentByAmazon`
  - `EtsySellers`
  - `ecommerce`
- 消费 / 选品侧：
  - `BuyItForLife`
  - `EDC`
  - `CampingGear`
  - `Frugal`
  - `dogs`
  - `Dogtraining`
- 候选补充：
  - `Bushcraft`
  - `Survival`
  - `ManyBaggers`
  - `onebag`
  - `myog`

### 题材簇线索

- 宠物不是一个词，而是一组真实场景：
  - 掉毛
  - 出行
  - 公寓养宠
  - 异味
  - 耐咬
- EDC 不是一个词，而是一组具体携带问题：
  - 整理袋
  - 口袋负担
  - 通勤携带
  - 桌面随身切换
- 户外也不是“大露营”一个词：
  - 新手露营
  - 车露
  - 潮湿天气
  - 冷天气
  - 轻量化
- 家居 / 小商品也不能继续泛写成“home / gadgets”：
  - 小厨房
  - 租房友好
  - 易清洁
  - 替换件
  - 高频消耗品

### 说明

这说明当前电商线最缺的不是再多加几个 subreddit，而是要把“品类名”拆成“购买场景 + 具体摩擦”。

## 增长方向捞到的关键信号

### 社区线索

- 已证明确实该进长期池：
  - `PPC`
  - `FacebookAds`
  - `googleads`
  - `Google_Ads`
  - `adops`
  - `SEO`
  - `bigseo`
- 候选补充：
  - `DigitalMarketing`
  - `Affiliatemarketing`
  - `InstagramMarketing`
  - `agency`
  - `NewsletterCommunity`
  - `Entrepreneur`

### 题材簇线索

- SEO / GEO：
  - 不是只看排名掉不掉
  - 还要看 AI 搜索、引用、索引、Reddit SEO、AEO/GEO
- Ads：
  - 不能只看 ROAS/CAC
  - 还要看 learning reset、no impressions、creative fatigue、budget waste
- Attribution：
  - 现在明显是独立簇，不该继续塞在 paid-economics 里一起糊
  - 关键词更像：
    - third party tracking
    - server-side
    - pixel not fed
    - platform mismatch
- Creator / affiliate / distribution：
  - 现在几乎没被当前 contract 看见
  - 但这明明就是长期重要的增长线

## 这轮侦查给出的硬判断

### 判断 1

“今天某个领域没有够硬的新料”这句话，以后不能轻易说。

在当前阶段，更准确的说法只能是：

**当前 supply contract 还没覆盖到足够宽的题材面。**

### 判断 2

当前最大的错误不是社区太少，而是：

- 主题面没拆开
- 名词桶不够具体
- 来源模式也窄

### 判断 3

下一步不能继续把这些边界写在 Python pack 文件里。

要改成：

- YAML 里管题材簇
- YAML 里管社区池
- YAML 里管关键词桶
- YAML 里管来源模式

业务代码只负责“读取配置并组装 spec”，不再定义业务边界。
