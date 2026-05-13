# Phase 570 - candidate_extractor 切到社区 truth-source

## 发现了什么？
- `backend/app/services/semantic/candidate_extractor.py` 的 DB 路径还在直接依赖旧 projection：
  - `JOIN community_pool`
  - 用 `community_pool.tier` 决定哪些社区能进入语义候选池
- 这会导致语义候选抽取虽然已经从评论事实层取数，但社区正式资格仍可能被旧表带偏。

## 是否需要修复？
- 需要。
- 这条链会直接影响语义候选抽取和后续词库沉淀，不改的话分析链仍会残留旧口径。

## 精确修复方法
### 1. candidate_extractor 改成先取 truth-source 正式社区盘
- 更新：
  - `backend/app/services/semantic/candidate_extractor.py`
- 改动：
  - 先调用 `load_effective_truth_communities()`
  - 再从正式社区盘里筛出语义候选允许 tier：
    - `t1 / t2 / high / medium / semantic`
  - 评论查询改成：
    - `WHERE lower(c.subreddit) = ANY(:eligible_subs)`
  - 不再 `JOIN community_pool` 定义正式社区资格

### 2. 新增定向回归
- 更新：
  - `backend/tests/services/semantic/test_candidate_extractor.py`
- 覆盖：
  - 只有 truth-source 允许 tier 的社区会进入候选池
  - 低 tier truth-source 社区不会混入 `eligible_subs`

## 验证
- `pytest backend/tests/services/semantic/test_candidate_extractor.py -q`
  - `4 passed`

## 下一步系统性的计划
- 继续扫分析/报表/API/worker 里剩余旧表正式判断点
- 优先继续处理：
  - 仍直接读 `community_pool.categories / community_pool.is_active`
  - 会影响报告主链、API 返回和 worker 调度判断的点

## 这次执行的价值
- 社区层唯一真相源又向分析链深处推进了一步：
  - 现在不只是抓取、调度、报告默认社区盘在统一
  - 连语义候选抽取这条链也开始按正式社区盘运行
- 这样后面词库和语义层结果，就更不容易继续被旧 projection 口径污染。
