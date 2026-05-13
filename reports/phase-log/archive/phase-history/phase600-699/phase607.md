# Phase 607 - Hotpost Core Contract 第一轮系统化落地

## 时间
- 2026-03-30

## 目标
- 不再按单题 patch 修 `rant`
- 正式把 `hotpost` 拉回“稳固底座 + skill contract”的方向
- 本轮先把 `rant` 的 `ProblemFrame / cache contract / generic rant summary-action / platform seed subreddit` 这几层补齐
- 明确不误伤 `trending` 主链

## 这轮做了什么

### 1. 补了 `ProblemFrame` 底座
- 新增：
  - `backend/app/services/hotpost/problem_frame.py`
- 作用：
  - 把 `rant` query 先压成稳定结构，不再让 `fast` 一次输出直接决定整条链
  - 明确：
    - `query_family`
    - `primary_friction`
    - `secondary_frictions`
    - `retrieval_hypotheses`
    - `forbidden_narrowing_terms`

### 2. 把 planner / retrieval / response 接到新 contract
- 修改：
  - `backend/app/services/hotpost/query_planner.py`
  - `backend/app/services/hotpost/retrieval_precision.py`
  - `backend/app/services/hotpost/search_workflow.py`
  - `backend/app/services/hotpost/response_bundle.py`
  - `backend/app/services/hotpost/hotpost_deps_factory.py`
  - `backend/app/schemas/hotpost.py`
- 结果：
  - `rant` 不再只靠命中词和单条 query 往下撞
  - debug contract 里也能看到：
    - `query_family`
    - `primary_friction`
    - `retrieval_hypotheses`
    - `forbidden_narrowing_terms`

### 3. 收紧 `generic rant` 的总结和动作建议
- 修改：
  - `backend/app/services/hotpost/response_bundle.py`
- 结果：
  - `generic_complaint_discovery / trust_gap` 不再滑回：
    - “流量不稳定”
    - “转化起不来”
    这类 TikTok 式错总结
  - 没有明确证据时，也优先回到“宣传、承诺、体验对不上”的 generic 产品抱怨语境

### 4. 加了 cache contract 版本闸门
- 修改：
  - `backend/app/services/hotpost/cache.py`
  - `backend/app/services/hotpost/query_resolver.py`
- 结果：
  - 旧 query/result cache 不会再绕过这轮 contract
  - 这次版本推进到：
    - `HOTPOST_CACHE_CONTRACT_VERSION = v3`
    - `HOTPOST_QUERY_TRANSLATE_CONTRACT_VERSION = v3`

### 5. 补了英文泛吐槽 family 识别
- 修改：
  - `backend/app/services/hotpost/problem_frame.py`
- 结果：
  - 英文问法里的：
    - `complain`
    - `complaining`
    - `complains`
  现在也会被识别成 `generic_complaint_discovery`
  - 不再掉回 `specific_issue`

### 6. 把 platform conversion rant 的 subreddit seed 接回来
- 修改：
  - `backend/app/services/hotpost/query_planner.py`
- 结果：
  - 对 `weak_buy_reason + 平台词` 这类 `rant`，即使没有 subreddit hint，也会自动补回：
    - `r/{platform}`
    - `r/{platform}help`
    - `r/{platform}ads`
    - `r/{platform}shop`
  - 这轮验证的是：
    - `TikTok` 这类 conversion rant 不再只掉回 `smallbusiness`

## 新增/更新测试
- 新增：
  - `backend/tests/services/hotpost/test_hotpost_problem_frame.py`
  - `backend/tests/services/hotpost/test_hotpost_rant_benchmark.py`
- 更新：
  - `backend/tests/services/hotpost/test_hotpost_cache.py`
  - `backend/tests/services/hotpost/test_hotpost_query_planner.py`
  - `backend/tests/services/hotpost/test_hotpost_query_resolver.py`
  - `backend/tests/services/hotpost/test_hotpost_response_bundle.py`

## 验证

### 定向
- `tests/services/hotpost/test_hotpost_cache.py`
- `tests/services/hotpost/test_hotpost_query_resolver.py`
- `tests/services/hotpost/test_hotpost_response_bundle.py`
- `tests/services/hotpost/test_hotpost_problem_frame.py`
- 结果：
  - `38 passed`

### planner + problem + workflow
- `tests/services/hotpost/test_hotpost_query_planner.py`
- `tests/services/hotpost/test_hotpost_problem_frame.py`
- `tests/services/hotpost/test_hotpost_search_workflow.py`
- 结果：
  - `33 passed`

### 全量 hotpost
- `cd backend && SKIP_DB_RESET=1 ../.venv/bin/pytest tests/services/hotpost -q`
- 结果：
  - `206 passed`

## 真实后端输出

### 1. generic product complaint
- query:
  - `what do people complain most about coffee machines overall?`
- 结果：
  - `from_cache = false`
  - `status = completed`
  - `query_family = generic_complaint_discovery`
  - `primary_friction = trust_gap`
  - `summary = 大家最常抱怨的不是一个点坏了，而是宣传、体验和实际表现经常对不上。`

这说明：
- `generic rant` 的 family 和 summary 已经回正
- 这轮 contract 不是只在测试里成立，live 也成立

### 2. live 还暴露出的下一层问题
- generic complaint 的 community scout 还不够准
- uncached 英文 `rant` 在真 Reddit live 下，样本仍可能被：
  - `smallbusiness`
  - `rant`
  这种泛社区吃掉
- 所以现在下一层真正该打的，不再是 summary/prompt，而是：
  - `evidence scout`
  - `community discovery`
  - `generic product complaint` 的样本纯度

## 当前结论
- 这轮已经把 `rant` 从“单题 patch”正式拉回了 `core contract` 路线
- 已经补上的不是话术，而是：
  - `ProblemFrame`
  - cache contract
  - generic rant summary/action contract
  - platform seed subreddit contract
- `trending` 这轮没有被带坏

## 下一步
- Phase 608 只打一件事：
  - `rant evidence scout / community discovery`
- 重点是把：
  - generic product complaint
  - platform conversion rant
  的 live 样本纯度拉起来
- 不再回头补页面词或单题 prompt
