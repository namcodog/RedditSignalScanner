# Phase 608 - Hotpost Rant 样本入口与社区发现第一轮收口

## 时间
- 2026-03-30

## 目标
- 只继续收 `rant` 的 `evidence scout / community discovery`
- 不再补页面话术，不再做单题 patch
- 重点验证：
  - generic product complaint 能不能脱离泛社区
  - platform conversion rant 这条 live 是否也更稳
- 明确不误伤 `trending`

## 这轮做了什么

### 1. generic complaint 不再先吃默认泛社区
- 修改：
  - `backend/app/services/hotpost/query_planner.py`
- 结果：
  - 当 `query_family = generic_complaint_discovery` 且没有稳定 subreddit hint 时
  - `candidate_subreddits` 先留空
  - 不再默认塞：
    - `r/customerservice`
    - `r/smallbusiness`
    - `r/rant`
  - 把社区发现权真正交给后面的 subreddit scout

### 2. rant 的 subreddit rescue 改成按对象发现，而不是按泛抱怨兜底
- 修改：
  - `backend/app/services/hotpost/evidence_collection_workflow.py`
- 新增：
  - generic complaint 的对象词提取
  - business/platform 语境判断
  - subreddit suggestion query builder
  - rescued subreddit ranking
- 结果：
  - generic complaint 现在优先按对象搜社区
    - 例如：
      - `coffee machine`
  - platform + business conversion rant 则优先搜更贴题的提示词
    - 例如：
      - `tiktok shop seller ads`
  - rescued subreddit 不再只按名称相似度排
  - 会额外参考：
    - `public_description`
    - 对象词命中
    - generic complaint 噪音惩罚

### 3. 补了定向回归
- 新增/更新：
  - `backend/tests/services/hotpost/test_evidence_collection_workflow.py`
  - `backend/tests/services/hotpost/test_hotpost_query_planner.py`
- 覆盖点：
  - generic rant suggestion query 不再被缩成 maintenance 类子问题
  - platform business rant suggestion query 会偏向 `ads/shop`
  - generic rant rescues 时优先贴题社区
  - planner 对 generic complaint 会 defer 默认泛社区

## 验证

### 定向
- `cd backend && SKIP_DB_RESET=1 ../.venv/bin/pytest tests/services/hotpost/test_evidence_collection_workflow.py -q`
- 结果：
  - `16 passed`

### query + planner + workflow + bundle
- `cd backend && SKIP_DB_RESET=1 ../.venv/bin/pytest tests/services/hotpost/test_hotpost_query_resolver.py tests/services/hotpost/test_hotpost_query_planner.py tests/services/hotpost/test_evidence_collection_workflow.py tests/services/hotpost/test_hotpost_response_bundle.py -q`
- 结果：
  - `60 passed`

### planner + scout 复验
- `cd backend && SKIP_DB_RESET=1 ../.venv/bin/pytest tests/services/hotpost/test_hotpost_query_planner.py tests/services/hotpost/test_evidence_collection_workflow.py -q`
- 结果：
  - `30 passed`

### 全量 hotpost
- `cd backend && SKIP_DB_RESET=1 ../.venv/bin/pytest tests/services/hotpost -q`
- 结果：
  - `210 passed`

## 真实后端输出

### 1. generic product complaint 已明显回正
- query:
  - `what do people complain most about coffee machines overall now`
- 结果：
  - `from_cache = false`
  - `status = completed`
  - `mode_state = standard`
  - `query_family = generic_complaint_discovery`
  - `primary_friction = trust_gap`
  - `candidate_subreddits = []`
  - `subreddits = ["r/buyusedcoffeemachines","r/coffee_machines","r/coffee","r/espresso","r/brevillecoffee"]`
  - `communities = ["Coffee","espresso","BrevilleCoffee","Coffee_Machines"]`
  - `evidence_count = 30`
  - `summary = 大家最常抱怨的不是一个点坏了，而是宣传、体验和实际表现经常对不上。`

这条结果说明：
- generic complaint 已经开始真正从“对象社区”拿样本
- 不再被：
  - `smallbusiness`
  - `rant`
  这类泛社区轻易吸走

### 2. platform conversion rant 还留有一层 live 不确定性
- query:
  - `why do tiktok views stop turning into sales for stores now again`
- 当前表现：
  - API 返回 `queued`
  - 多轮 polling 后仍未进入终态
- 当前判断：
  - 这不是 generic complaint 路线的问题
  - 但说明 platform conversion rant 的 live smoke 这轮还不能宣告完全收尾
  - 下一步仍要继续盯：
    - `platform conversion rant`
    - `community discovery`
    - `queued -> completed` 的实际落地稳定性

## 当前结论
- 这轮最值钱的结果已经拿到了：
  - `generic complaint` 的样本入口明显回正
  - 这说明 `ProblemFrame -> planner defer -> subreddit scout` 这条新 contract 正在生效
- 当前没有证据表明这轮误伤了 `trending`
- 当前剩余最大不确定性已经进一步收敛成：
  - platform conversion rant 的 live 样本入口和终态稳定性

## 下一步
- Phase 609 继续只打一件事：
  - `platform conversion rant` 的 `evidence scout / live completion`
- 目标：
  - 让：
    - `TikTok`
    - `TikTokAds`
    - `TikTokShop`
  这类值钱社区在 live 下更稳定地出现
- 不回头补页面，不转去改 prompt，不先换模型
