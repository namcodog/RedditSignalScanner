# Phase 575 - 收掉 backfill 读旧表与 report 导出口径漏口

## 发现了什么？

还有 3 个高价值漏口会把旧表口径带回主链：

1. `execute_target_task_support.load_backfill_floor()` 还在读 `community_cache.backfill_floor`
2. `backfill_posts_workflow._load_existing_backfill_cursor()` 还在读 `community_cache.backfill_cursor`
3. `api/v1/endpoints/reports.py` 在导出社区清单时，正式分类/启用态/黑名单态还在看 `community_pool`

这 3 个点分别影响：

- backfill 完成度判断
- backfill 游标续跑
- 对外报告导出和前端展示

## 是否需要修复？

需要，而且这轮已经完成。

## 精确修复方法

### 1. backfill floor 改读 runtime truth-source

- 文件：
  - `backend/app/services/crawl/execute_target_task_support.py`
- 调整：
  - `load_backfill_floor()` 不再查 `community_cache`
  - 改为：
    - `community_registry`
    - `community_runtime_state`

### 2. backfill cursor 改读 runtime truth-source

- 文件：
  - `backend/app/services/crawl/backfill_posts_workflow.py`
- 调整：
  - `_load_existing_backfill_cursor()` 不再查 `community_cache`
  - 改从 `community_runtime_state.runtime_notes` 读取：
    - `backfill_cursor`
    - `backfill_cursor_created_at`
  - 顺手删除静默 `try/except` 兜底
  - 缺数据就回真实空值，查询异常就直接暴露

### 3. report 导出接口正式状态改读 truth-source

- 文件：
  - `backend/app/api/v1/endpoints/reports.py`
- 调整：
  - `categories`
  - `is_active`
  - `is_blacklisted`
  - `blacklist_reason`
  改成通过：
    - `community_registry`
    - `community_runtime_state`
    - `community_domain_membership`
    - `community_governance_decision`
  联查得到
- 保留：
  - `tier / priority` 继续作为旧 projection 展示字段
  - `member_count / crawl_frequency / last_crawled_at` 继续来自运行投影层

## 验证

### 编译检查

- `python -m py_compile backend/app/services/crawl/execute_target_task_support.py backend/app/services/crawl/backfill_posts_workflow.py backend/app/api/v1/endpoints/reports.py`
- 结果：通过

### 定向测试

- `SKIP_DB_RESET=1 python -m pytest backend/tests/services/crawl/test_execute_target_task_support.py -q`
- 结果：`4 passed`

- `SKIP_DB_RESET=1 python -m pytest backend/tests/services/crawl/test_backfill_posts_workflow.py -q`
- 结果：`3 passed`

- `SKIP_DB_RESET=1 python -m pytest backend/tests/api/test_reports.py -q -k "export_communities_all"`
- 结果：`2 passed`

## 这次执行的价值是什么？达到了什么目的？

这轮的意义是把“运行状态”和“报告导出”这两个最容易回漂的点堵住了：

- backfill 不再偷偷回头读旧表
- report 导出也不再把旧 `community_pool.categories / is_active` 当正式口径

社区层唯一真相源这条线，已经从抓取、调度、语义、报告默认盘，继续推进到了：

- backfill 状态读取
- backfill 游标续跑
- 对外报告社区导出
