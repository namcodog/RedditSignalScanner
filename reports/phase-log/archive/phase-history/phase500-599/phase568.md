# Phase 568 - crawl_plan 切到社区 truth-source

## 发现了什么？
- `backend/app/services/crawl/crawl_plan.py` 还整段建立在旧 projection 上：
  - 直接 `select(CommunityPool)`
  - 用 `community_pool.categories` 推 vertical
  - 用 `community_pool.is_active` 决定 plan 状态
- 这意味着前面虽然已经把：
  - 运营写入口
  - discovery
  - warmup
  - member sync
  - tier 调度
  - comment label planner
  收到 truth-source 了，但“抓取计划怎么生成”这条总入口还在认旧表。

## 是否需要修复？
- 需要。
- 这是高优先级残留点，因为它直接决定 crawler 后续拿到的 plan 是什么。

## 精确修复方法
### 1. CrawlPlanBuilder 改为 truth-source 驱动
- 更新：
  - `backend/app/services/crawl/crawl_plan.py`
- 改动：
  - 从 `load_effective_truth_communities()` 读取正式社区盘
  - 不再直接扫描 `community_pool`
  - `vertical` 改由 truth-source 当前领域盘推导
  - `status` 改为：
    - truth-source 当前正式盘 + blacklist => `active / paused`
  - `source` 改成 `truth_source`

### 2. 去掉默认吞错式兜底
- 本轮明确不再给 crawl plan 偷塞默认正式字段：
  - 缺 `tier`
  - 缺 `priority`
  - 缺 `quality_score`
- 现在会直接抛错暴露，防止用旧 projection 或假默认值继续掩盖真问题。

### 3. 新增定向回归
- 新增：
  - `backend/tests/services/crawl/test_crawl_plan.py`
- 覆盖：
  - crawl plan 只从 truth-source 读正式社区
  - truth-source projection 缺必填字段时直接失败，不写兜底

## 验证
- `pytest backend/tests/services/crawl/test_crawl_plan.py backend/tests/tasks/test_crawler_fallback.py -q`
  - `4 passed`

## 下一步系统性的计划
- 继续扫剩余 `worker / reports / API` 里的旧表正式判断点
- 优先处理：
  - `t1_stats`
  - `candidate_extractor`
  - 仍直接从 `community_pool / community_cache` 做正式判断的报表链

## 这次执行的价值
- 这一步把社区层最核心的一条总入口也收进 truth-source 了：
  - 现在不只是“谁能进正式盘、谁能被抓、谁怎么调度”统一了
  - 连“整份 crawl plan 是怎么生成的”也开始按唯一真相源执行
- 这对后面整个主链的稳定性意义很大，因为 crawler 不再从旧 projection 偷偷把错误社区带回系统。
