# Phase 610 - Hotpost Platform Conversion Rant Family Contract 第一轮落地

## 时间
- 2026-03-30

## 目标
- 不再修 `TikTok` 个案
- 正式把“平台有流量但不成交/有点击但不下单”收成一类通用问题：
  - `platform_conversion_rant family`
- 让：
  - `problem_frame`
  - `query_planner`
  - `evidence_scout`
  - `search_workflow`
  都按同一份 contract 工作

## 这轮做了什么

### 1. 把平台转化类问题提升成独立 family
- 修改：
  - `backend/app/services/hotpost/problem_frame.py`
- 新增：
  - `_PLATFORM_TERMS`
  - `_PLATFORM_COMMERCE_TERMS`
- 结果：
  - 以前这类 query 只会被归到：
    - `conversion_friction`
  - 现在正式提升成：
    - `platform_conversion_friction`
  - 识别标准不再靠单个平台 patch，而是：
    - 平台词
    - 转化/销售词
    - 商业上下文

### 2. 给这类 family 单独定义检索假设
- 修改：
  - `backend/app/services/hotpost/problem_frame.py`
- 结果：
  - hypotheses 不再沿用泛转化模板
  - 当前统一变成更像 Reddit 真会搜的两条主线：
    - `tiktok ads no sales`
    - `tiktok views low conversion`
  - 额外 hypothesis 继续保留在内部：
    - `tiktok seller no orders`
    - 原始 search query

### 3. planner 正式按 family 推导社区，不再偷带泛社区
- 修改：
  - `backend/app/services/hotpost/query_planner.py`
- 结果：
  - `platform_conversion_friction` 现在会直接推导：
    - `r/{platform}`
    - `r/{platform}ads`
    - `r/{platform}shop`
    - `r/{platform}help`
  - 且在无 resolved subreddit hint 时，不再把默认泛社区一起带进来
  - 这次已经把：
    - `r/customerservice`
    - `r/smallbusiness`
    - `r/rant`
    从这类 family 的默认入口中切掉

### 4. evidence scout 按 family 发现社区
- 修改：
  - `backend/app/services/hotpost/evidence_collection_workflow.py`
- 结果：
  - subreddit suggestion query 对这类问题统一改成：
    - `{platform} seller ads shop`
  - rescued subreddit ranking 也开始按 family 给平台商业社区额外权重
  - 不再继续通过 `weak_buy_reason + business_context` 间接猜

### 5. 执行层 query ranking 接到新 family
- 修改：
  - `backend/app/services/hotpost/search_workflow.py`
- 结果：
  - query 执行顺序不再沿用旧 `conversion_friction`
  - 当前优先执行更像平台商业转化问题的 query：
    - `ads / shop / seller`
    - `sales / orders / conversion`

## 新增/更新测试
- 更新：
  - `backend/tests/services/hotpost/test_hotpost_problem_frame.py`
  - `backend/tests/services/hotpost/test_hotpost_query_planner.py`
  - `backend/tests/services/hotpost/test_evidence_collection_workflow.py`
  - `backend/tests/services/hotpost/test_hotpost_rant_benchmark.py`
  - `backend/tests/services/hotpost/test_hotpost_search_workflow.py`
- 新增验证点：
  - `platform_conversion_friction` family 判定
  - planner 的 query parts / candidate subreddits
  - scout 的 subreddit suggestion query
  - execution ranking 会优先平台商业 query

## 验证

### 定向
- `cd backend && SKIP_DB_RESET=1 ../.venv/bin/pytest tests/services/hotpost/test_hotpost_problem_frame.py tests/services/hotpost/test_hotpost_query_planner.py tests/services/hotpost/test_evidence_collection_workflow.py tests/services/hotpost/test_hotpost_rant_benchmark.py tests/services/hotpost/test_hotpost_search_workflow.py -q`
- 结果：
  - `57 passed`

### py_compile
- `cd backend && ../.venv/bin/python -m py_compile app/services/hotpost/problem_frame.py app/services/hotpost/query_planner.py app/services/hotpost/evidence_collection_workflow.py app/services/hotpost/search_workflow.py`
- 结果：
  - `通过`

### 全量 hotpost
- `cd backend && SKIP_DB_RESET=1 ../.venv/bin/pytest tests/services/hotpost -q`
- 结果：
  - `211 passed`

## 真实后端 smoke

### platform conversion rant
- query:
  - `why do tiktok views not turn into sales anymore?`
- 结果：
  - `from_cache = false`
  - `status = completed`
  - `mode_state = preview`
  - `query_family = platform_conversion_friction`
  - `primary_friction = weak_buy_reason`
  - `candidate_subreddits = ["r/tiktok","r/tiktokads","r/tiktokshop","r/tiktokhelp"]`
  - `subreddits = ["r/tiktokads","r/tiktokshop","r/tiktokhelp","r/tiktok"]`
  - `communities = ["TikTokAds","TikTokshop","TikTok"]`
  - `query_parts = ["tiktok ads no sales","tiktok views low conversion"]`
  - `evidence_count = 7`
  - `summary = TikTok内容有流量却卖不动，商家开始怀疑继续投广告到底值不值。`

这条结果说明：
- 这轮已经不再是在修 `TikTokAds` 个案
- 而是 `platform conversion rant family` 真的开始按新 contract 工作了

## 当前结论
- 这轮收的不是单题现象，而是一类问题的入口设计
- 当前已经做到：
  1. family 被显式识别
  2. hypotheses 被显式定义
  3. community discovery 被显式约束
  4. default generic fallback 被切掉
- 这轮没有证据表明误伤了 `trending`
  - 因为全量 hotpost 回归仍然全绿

## 下一步
- Phase 611 继续只打：
  - `evidence judge`
- 重点不是再加 community 规则，而是：
  - 同一类 family 进来后，哪些帖子该上前排，哪些不该
- 不回头补 prompt
- 不补兜底层
