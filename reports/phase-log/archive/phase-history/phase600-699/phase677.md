# Phase 677 - organic-discovery 与 category-winds 收口

## 发现了什么

- `organic-discovery` 的问题不是供给不够，而是旧全局写法会把 AI 搜索和 SEO 风向写成论坛转述。
- `category-winds` 的问题更靠前一层：
  - 旧供给还在抓卖家运营和投放讨论
  - `cap=1` 时，promo/sticky 还会把真实帖子直接挤掉
  - comment 层的 `SCAM WARNING / bot` 文本会污染 quote

## 是否需要修复

需要，而且两条线要分开修：

- `organic-discovery`：直接做 pack 专用写法
- `category-winds`：先修供给，再做 pack 专用写法

## 精确修复方法

### 1. organic-discovery

- 新增：
  - `backend/app/services/hotpost/organic_discovery_overrides.py`
- 生成链已接线：
  - `backend/app/services/hotpost/card_content_generator.py`
- 测试补齐：
  - `backend/tests/services/hotpost/test_organic_discovery_overrides.py`
  - `backend/tests/services/hotpost/test_card_content_generator.py`

canary 结果：

- baseline `human_summary_tight_why_now_v1 = 0/2 pass`
- `organic_discovery_readout_v1 = 2/2 pass`
- 结论：`keep`

### 2. category-winds

供给修复：

- `backend/app/services/hotpost/topic_pack_scope_ecommerce.py`
  - pack 改成更像赛道冷热/拥挤度的社区和 query
- `backend/app/services/hotpost/reddit_search_spec_builder.py`
  - `category-winds` 改成 `search-first`
  - bucket 顺序改成 `problem -> change -> category`
- `backend/app/services/hotpost/source_scope_candidate_collector.py`
  - `category-winds` 加入单 spec 单帖
  - 先过滤 noise，再应用 `cap=1`
- `backend/app/services/hotpost/reddit_candidate_mapper.py`
  - 过滤 bot / automod / scam warning comment

专用写法：

- 新增：
  - `backend/app/services/hotpost/category_winds_overrides.py`
- 生成链已接线：
  - `backend/app/services/hotpost/card_content_generator.py`
- live canary runner：
  - `backend/scripts/evals/run_category_winds_canary_v1.py`

canary 结果：

- baseline `human_summary_tight_why_now_v1 = 0/2 pass`
- `category_winds_readout_v1 = 2/2 pass`
- 结论：`keep`

## 下一步系统性的计划是什么

这轮两条 pack 已经收口，不再继续在这两个 pack 上开新实验。

下一步回到系统层面：

1. 继续用当前稳定资产产卡
2. 不重开 `tools-efficiency`
3. 下一轮如果再扩 pack，单独立新题
4. 如果要继续拔高产品价值，优先考虑 `breakdown skill optimization`

## 这次执行的价值是什么

这轮真正完成的是把用户指定的两条新 pack 主线都跑成了成熟资产：

- `organic-discovery`
- `category-winds`

也就是说，`paid-economics / selection-signals / agent-builder / organic-discovery / category-winds` 现在都已经有了 pack 级稳定写法。

这不是多写了几句 prompt，而是把 pack 方法论真正复制成了系统能力。
