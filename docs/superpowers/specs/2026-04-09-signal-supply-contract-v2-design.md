# Design: Signal Supply Contract V2
Date: 2026-04-09
Branch: main

## Problem Statement

当前的问题不是 Reddit 没有料，而是我们对“要抓什么料”定义得不够清楚。

具体表现：

- 采集范围偏窄，容易来回盯住少数社区
- 某些你明确关心的题材几乎不出现：
  - 电商里的宠物 / EDC / 户外 / 家居 / 小商品
  - AI 里的 GitHub 开源项目 / 大咖观点 / 标志性项目路线
- 运营时会得到错误结论：
  - “今天这个领域没有够硬的新料”

这不是市场没有信号，而是当前 `subreddit + keyword + listing/search` 合同还不够完整。

## Premise Challenges

### 挑战 1：问题不是“运营没推进”

不是。

运营已经真跑了，问题出在：
- 上游采集合同偏窄
- pack 覆盖面不够
- 某些我们重视的话题根本没被编码进规则

### 挑战 2：问题也不只是“社区太少”

也不够准确。

更本质的是三件事一起窄：
- 社区池窄
- query 桶窄
- source 模式窄

比如：
- `upstream-winds` 现在只有 `artificial / OpenAI / LocalLLaMA / MachineLearning`
- `selection-signals` 虽然已经有 `EDC / dogs / CampingGear`，但关键词还是偏泛，不够贴具体购买场景
- `reddit_search_spec_builder.py` 里很多 pack 还是固定：
  - `search:relevance:week`
  - 或少数 listing 组合

### 挑战 3：不是应该“无限放宽”

也不能这么做。

如果只是无脑加社区、加关键词，最后会得到：
- 噪音更多
- 社区礼仪帖更多
- 低信息热帖更多
- 运营队列更乱

所以问题不是“再加一点”，而是要把采集合同变成有边界的覆盖系统。

## Options Considered

| 方案 | 内容 | 成本 | 风险 | 适用场景 |
|---|---|---:|---:|---|
| A. 继续边跑边补 | 看到缺什么就往 pack 里塞社区和关键词 | S | 高 | 临时救火 |
| B. 定义 Supply Contract V2 | 给每个 scope/pack 明确覆盖主题、社区池、关键词桶、listing/search 比例、目标配比 | M | 低 | 当前最合适 |
| C. 全自动发现驱动 | 用 discovery/autoresearch 自动扩社区和 query | L | 高 | 以后再说 |

## Chosen Direction

选 **B. Supply Contract V2**。

原因：

- 它直接解决当前真问题：覆盖面没有定义清楚
- 不会把系统重新带回“今天缺什么补什么”的临时状态
- 比自动发现更稳，因为我们现在缺的不是扩张能力，而是清晰口径

## What V2 Must Define

V2 不讨论 prompt，不讨论 judge，只讨论采集合同。

必须补清这 5 层：

1. **主题面**
- 每个 scope 下面要覆盖哪些明确题材
- 不能只写抽象 pack 名，要写到可执行的主题簇

2. **社区面**
- 每个主题簇对应哪些 subreddit
- 哪些社区是主社区
- 哪些是补充社区

3. **关键词面**
- 每个主题簇要有：
  - category 词
  - problem 词
  - change 词
  - 人物 / 项目 / 品牌 / 项目名词

4. **source 面**
- 哪些题材适合 `listing-first`
- 哪些题材适合 `search-first`
- 哪些应该混合抓

5. **配比面**
- 三大领域目标配比
- pack 级最低曝光要求
- 热点 lane 的最低样本要求

## V2 First Targets

第一批优先补这些空洞：

### AI 与自动化
- GitHub 开源项目
- 大咖/关键人物路线
- 平台策略变化
- 真实 agent 落地事故

### 电商与卖家
- 宠物用品
- EDC
- 户外 / 露营
- 家居 / 小家电
- 小商品 / 高频消耗品

### 商业增长与运营
- SEO/GEO 工具生态
- Ads 预算与归因
- 漏斗与转化事故

## Success Criteria

满足这些，才算 V2 有效：

1. 不再出现“今天这个领域根本没料”的轻率结论
2. 新候选池里能明显看到更广的题材覆盖
3. 热点 lane 不再长期只出现在 AI / 增长
4. 电商不再长期只靠少数品类撑住
5. 队列扩宽后，质量闸门仍然能守住，不因为扩面而塌

## Risks

1. **扩面过快，噪音暴涨**
- 规避：V2 先做合同，不一次性全开

2. **把“覆盖更多”误解成“抓更多”**
- 规避：先定义主题簇，再扩社区和 query

3. **热点和信号重新混**
- 规避：继续保留 `lane` 边界，不因为扩面混掉内容线

## NOT in Scope

- 不改 prompt
- 不改 judge
- 不改 breakdown 主链
- 不直接做 autoresearch
- 不做自动扩社区系统
