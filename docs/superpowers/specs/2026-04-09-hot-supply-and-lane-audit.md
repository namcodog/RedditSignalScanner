# Audit: Hot / Supply / Lane 深度审计
Date: 2026-04-09
Branch: main

> 这份审计保留作历史问题定位材料。
> 其中关于发布比例的旧口径，已被 [2026-04-09-v1-density-first-contract.md](/Users/hujia/Desktop/RedditSignalScanner/docs/superpowers/specs/2026-04-09-v1-density-first-contract.md) 的 `1.0` 新合同替代。

## 审计范围

本次只审下面 4 条链路，不做方案粉饰：

1. `hot` 判定是否被错误的前置规则卡死
2. `search / listing` 是否被错误当成帖子性质，而不是检索方式
3. “R站老炮儿”角色 prompt 是否真的进入了判断层
4. lane / 领域比例是否已经被工作流真正执行，而不是只写在 SOP

---

## Finding 1: `hot` 仍然被“来源方式”过早拦截

**严重性：P0**

### 证据

- [card_lane_policy.py](/Users/hujia/Desktop/RedditSignalScanner/backend/app/services/hotpost/card_lane_policy.py):64

```python
if not is_listing and not payload.get("allow_search_hot", False):
    return "signal"
```

### 结论

当前实现把：

- `listing`
- `search`

当成了 `hot` 的第一层硬门禁。

这会导致：

- 帖子本身已经很热
- 讨论也有焦点
- 但只要它是从 `search` 命中的，且 pack 没开 `allow_search_hot`

它就会在真正内容判断前，被直接打回 `signal`。

### 为什么这是错的

`search` / `listing` 只是 **检索方式**，不是 **帖子性质**。

帖子该不该进 `hot`，应该主要看：

- 本身热不热
- 大家是不是在围着一个焦点吵
- 有没有群体报数或清晰对立

而不是先看：

- 它是被 `search` 找到的，还是被 `listing` 找到的

### 影响

- 真热点会被错误打回 `signal`
- 尤其会伤到：
  - AI 路线之争
  - GEO / SEO / Ads 争论
  - 平台策略之争

---

## Finding 2: `hot` 不只被 lane policy 卡，还被 `signal_input_quality` 二次误伤

**严重性：P0**

### 证据

- [review_queue_policy.py](/Users/hujia/Desktop/RedditSignalScanner/backend/app/services/hotpost/review_queue_policy.py):26
- [card_content_generator.py](/Users/hujia/Desktop/RedditSignalScanner/backend/app/services/hotpost/card_content_generator.py):94

当前逻辑是：

- 只要是 `validate`
- 就统一先过 `assess_signal_input_quality(...)`

而 `hot` 也是 `validate + lane=hot`。

### 结论

这意味着：

- `hot` 候选在进入队列前，被用 `signal` 的输入质量规则过滤一次
- `hot` draft 在生成内容前，又被用 `signal` 的输入质量规则过滤一次

### 为什么这是错的

`signal` 和 `hot` 的合格标准根本不是一回事：

- `signal` 看：需求/替代/避坑/求解法
- `hot` 看：这帖为什么火、大家在吵什么

把 `signal` 的门禁套到 `hot` 上，会直接误伤：

- 单帖高热争论
- 短句集体反应
- 话题型路线之争

### 影响

`hot` 不是只在 lane 规则里被收窄一次，
而是在真正进入前台前，被 `signal` 逻辑再压一遍。

这会让：

- `runtime hot` 薄
- `published hot` 更薄

---

## Finding 3: `agent-builder` 曾经吸走了本该进入 `upstream-winds` 的“开源路线/项目争论”

**严重性：P1**

### 证据

旧配置里：

- [hotpost_supply_discovery_v2.yaml](/Users/hujia/Desktop/RedditSignalScanner/backend/config/hotpost_supply_discovery_v2.yaml)
  - `upstream-winds.topic_clusters` 包含 `open-source-projects`
  - `agent-builder.topic_clusters` 也包含 `open-source-projects`

而同时：

- `upstream-winds.allow_search_hot = true`
- `agent-builder.allow_search_hot = false`

### 结论

这会造成：

- 同样是“开源路线 / 项目发布 / open source 争论”
- 一部分被分到 `upstream-winds`
- 一部分被分到 `agent-builder`

结果：

- 被送进 `agent-builder` 的那部分，即使够热，也会天然进不了 `search-based hot`

### 当前状态

这个点我已经做了**窄修**：

- 把 `open-source-projects` 从 `agent-builder` 移掉，只留在 `upstream-winds`

但这里暴露的是更大的结构问题：

**pack 之间的题材边界还不够硬。**

---

## Finding 4: “R站老炮儿” prompt 现在只影响“写卡”，没有接管“判断”

**严重性：P0**

### 证据

检索结果显示：

- [reddit_guide_prompt_assets.py](/Users/hujia/Desktop/RedditSignalScanner/backend/app/services/hotpost/reddit_guide_prompt_assets.py)
- [card_content_prompts.py](/Users/hujia/Desktop/RedditSignalScanner/backend/app/services/hotpost/card_content_prompts.py)
- [card_content_generator.py](/Users/hujia/Desktop/RedditSignalScanner/backend/app/services/hotpost/card_content_generator.py)

角色 prompt 只在：

- `build_signal_prompt`
- `build_breakdown_prompt`
- `card_content_generator`

这条链路里被使用。

它没有进入：

- `build_reddit_search_specs`
- `collect_scope_candidates`
- `infer_validation_lane`
- `filter_actionable_candidates`
- `card_selection_policy`

### 结论

现在的“R站老炮儿”更像：

- **写卡人格**

而不是：

- **选卡人格**
- **判断人格**
- **检索人格**

### 影响

你角色 prompt 里最值钱的那部分：

- 这帖值不值得看
- 这是不是大家正在吵的焦点
- 这是不是藏在评论区里的真东西

目前还没有真正进系统关键路径。

所以你会感觉：

**prompt 很强，但像纸上谈兵。**

这个感觉是对的。

---

## Finding 5: lane mix 目标已经写进文档，但没有写进实际调度器

**严重性：P0**

### 证据

我们已经定了：

- 最近 20 张：
  - `signal / hot / breakdown = 10 / 6 / 4`
- 领域：
  - `AI / 增长 / 电商 = 7 / 7 / 6`

但实际调度代码：

- [card_selection_policy.py](/Users/hujia/Desktop/RedditSignalScanner/backend/app/services/hotpost/card_selection_policy.py)

只做了两件事：

1. `lane == hot` 给一个固定加分 `+40`
2. 按 **全历史** `published_items` 算领域缺口

而且领域目标还是硬编码在 Python 里：

```python
_TARGET_SCOPE_SHARE = {
    "ai-automation": 0.38,
    "business-growth-ops": 0.34,
    "ecommerce-sellers": 0.28,
}
```

### 结论

当前真实执行的是：

- 看全历史领域比例
- 给 `hot` 一个固定奖励

而不是：

- 看最近 20 张
- 按 `10 / 6 / 4`
- 按 `7 / 7 / 6`

### 影响

所以现在你看到的：

- 最近 20 张 `signal = 17 / hot = 3 / breakdown = 0`

不是意外，
而是因为**代码里根本没有按新配比调度。**

---

## Finding 6: `breakdown` 目前没有独立的供给恢复机制

**严重性：P1**

### 证据

- `materialize_breakdown_drafts.py` 本轮输出：
  - `materialized = 0`
  - `skipped_existing = 1`
- `queue --type write` 里没有新的 write draft，只有旧的候选和一个旧 draft

### 结论

`breakdown` 当前不是“发得少”，而是：

- suggestion 密度不够
- materialize 没有新草稿
- 发布侧也没有 lane 补偿逻辑

所以最近 20 张里它掉到 `0`，并不奇怪。

---

## Finding 7: 当前 review 队列是“可操作队列”，不是“按目标配比驱动的发布队列”

**严重性：P1**

### 证据

- [review_cards.py](/Users/hujia/Desktop/RedditSignalScanner/backend/scripts/hotpost/review_cards.py)
- [review_queue_policy.py](/Users/hujia/Desktop/RedditSignalScanner/backend/app/services/hotpost/review_queue_policy.py)

当前队列先做的是：

- 去重
- 去 reject
- 去已发布 / 已 draft
- 过 `signal_input_quality`
- 再按 `card_selection_policy` 排序

### 结论

当前 `queue` 是一个：

- “什么东西还能操作”的队列

不是一个：

- “为了达到 10/6/4 和 7/7/6，这轮最该发什么”的队列

### 影响

这会导致：

- 工具很顺手
- 但运营目标不会自动达成

---

## 审计结论

当前主问题不是单点 bug，而是 **三层错位**：

### 一层：供给层
- pack 题材边界仍有串味
- `hot` 供给还不够像“争论型供给”

### 二层：判断层
- `hot` 被来源方式过早拦截
- `hot` 又被 `signal` 门禁二次误伤
- 角色 prompt 没有进入判断主链

### 三层：运营层
- lane / 领域比例写进了 SOP
- 但没有写进真实调度器

---

## 现在最应该做的顺序

1. **把 `hot` 从 `signal_input_quality` 里拆出来**
2. **取消“search-based hot pack 白名单”式前置拦截**
3. **把最近 20 张的 lane/domain mix 真接进调度器**
4. **给 `breakdown` 做独立的供给恢复**
5. **再考虑让“R站老炮儿”进入 judge，而不只是写卡**

---

## 一句话结论

**现在不是 Reddit 料不够。**
**也不是 prompt 不够强。**

而是：

**“判断层”和“运营层”还没有真正按你定义的产品在工作。**
