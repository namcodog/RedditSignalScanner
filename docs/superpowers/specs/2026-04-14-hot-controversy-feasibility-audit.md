# Design: hot 争议图表可行性审计
Date: 2026-04-14
Branch: main

## Problem Statement

要审计的不是“能不能做一个好看的图”，而是：
- 小程序 `hot` 卡能不能稳定产出 `支持 / 反对 / 中性 + 分歧点`
- Reddit API 会不会因为这个需求必须换方案
- LLM 放在这条链上，怎样用才最值

## Premise Challenges

- 这不是前端需求，核心瓶颈在评论样本和聚合方式。
- 这不是“全仓情绪分析系统”，第一版只该服务小程序 `hot` 卡。
- 这不是实时功能，正确位置是发卡前离线计算，不是小程序运行时计算。

## Options Considered

| 方案 | What | Effort | Risk | Best for |
|---|---|---:|---|---|
| A. 纯文案推断 | 直接从 `flashpoint/fight_line` 写支持反对中性 | S | High | 演示，不追求真 |
| B. 评论浅聚合 | 保持现有主链，只把 `hot` 的评论样本抓深一点，发卡前聚合出争议字段 | M | Low | 小程序第一版最小可行 |
| C. 全量评论标注系统 | 把评论级 labeling 正式接入 hot 主链，做更真占比 | L | Med | 以后品牌舆情产品化 |

## Chosen Direction

选择 **B. 评论浅聚合**。

## Feasibility Verdict

- **可行性**：可行
- **Reddit API**：不需要换接口，只需要调整你当前的抓取深度和调用预算
- **LLM 作用**：有价值，但只该负责“聚合与总结”，不该负责“小程序实时分析”

## Evidence

### 当前链路限制

- 当前供给配置里，评论抓取深度只有 `3~5`：
  - `comments_fetch_limit: 3`
  - `comments_fetch_limit: 5`
- 位置：
  - `backend/config/hotpost_supply_discovery_v2.yaml`

- 当前小程序 `hot` 卡详情只保留 5 个字段：
  - `flashpoint`
  - `fight_line`
  - `why_test_now`
  - `continue_signal`
  - `stop_signal`
- 位置：
  - `hotpost-mini/hotpost-mini-app/src/services/clues.ts`

- mini 发布链已经是现成插入点：
  - `backend/app/services/hotpost/mini_snapshot.py`
  - `hotpost-mini/hotpost-mini-app/cloudfunctions/miniRelease/store.js`

### Reddit API 约束

- Reddit 公开文档说明 listing 类接口支持分页和 `limit`，可以按切片读取内容：
  - `https://www.reddit.com/dev/api/`
- Reddit 官方说明免费 Data API 速率限制：
  - OAuth：`100 queries/minute`
  - 非 OAuth：`10 queries/minute`
  - 来源：`https://redditinc.com/news/apifacts`
- 官方条款同时说明：
  - Reddit 可随时调整 API limit
  - 超出免费或商业使用可能需要单独协议
  - 来源：`https://redditinc.com/policies/data-api-terms`

结论：
- **这个需求不要求 Reddit API 换玩法**
- 但如果你把每张 `hot` 卡的评论样本从 `3~5` 提到 `20~30`，请求成本会明显上升，要盯 rate limit 和预算

### LLM 现有杠杆

- 仓库里已经有评论级 LLM labeling 能力，能打：
  - `sentiment`
  - `aspect_tags`
  - `intent`
- 证据：
  - `backend/tests/services/labeling/test_llm_labeler.py`

结论：
- **LLM 不该直接决定页面长什么样**
- **LLM 最值钱的位置，是把评论样本聚合成：**
  - `support_ratio`
  - `oppose_ratio`
  - `neutral_ratio`
  - `support_point`
  - `oppose_point`
  - `neutral_point`
  - `debate_focus`

## Recommended Minimal Architecture

```text
Reddit post + comments
    ↓
抓取时把 hot 评论样本从 3~5 提到 20~30
    ↓
发卡前离线聚合
    ↓
LLM 只做立场归纳与粗粒度占比
    ↓
mini_snapshot 给 hot 卡补 controversy_chart
    ↓
小程序首页显示三柱图 + 分歧点
```

## Success Criteria

- 首页用户不用读长文，就知道：
  - 哪边声音更大
  - 双方在争什么
  - 这张 `hot` 卡为什么值
- 不新增小程序运行时请求
- 不改 `signal / breakdown`

## Risks

- 风险 1：评论样本太浅，比例会假
  - 规避：先把 `comments_fetch_limit` 提到最小可用深度
- 风险 2：LLM 过度自由发挥
  - 规避：只输出固定字段，不输出长分析
- 风险 3：请求成本上升
  - 规避：只对 `hot` 卡深抓评论，不对所有 lane 扩散

## NOT in Scope

- 不做小程序端实时情绪分析
- 不做 `signal` 或 `breakdown` 同款图表
- 不做品牌舆情完整版后台
