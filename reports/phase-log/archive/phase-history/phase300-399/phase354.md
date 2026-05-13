# Phase 354 - 单社区抓取主链独立 workflow

## 时间
- 2026-03-17

## 本轮目标
- 收掉 `crawler_task._crawl_single(...)` 里还缠着的单社区抓取主链
- 让 `crawler_task` 继续变薄，同时保住 `_crawl_single` / `_crawl_single_impl` 现有入口合同

## 发现了什么
- `_crawl_single(...)` 之前还同时背着四类职责：
  - 抓取策略与 rate-limit fallback
  - Redis 缓存和 `community_cache` 写入
  - subreddit snapshot 持久化
  - preview comments 同步
- 这会让 `crawler_task` 继续既当入口、又亲手跑整条单社区抓取 workflow。

## 这次做了什么
- 新增独立 workflow：
  - `backend/app/services/crawl/single_crawl_workflow.py`
- 正式收了：
  - `SingleCrawlWorkflowInput`
  - `SingleCrawlWorkflowDeps`
  - `SingleCrawlWorkflowResult`
  - `run_single_crawl_workflow(...)`
- 收薄入口：
  - `backend/app/tasks/crawler_task.py`
  - `_crawl_single(...)` 现在只负责：
    1. 记录开始日志
    2. 组装 workflow input / deps
    3. 调 workflow
    4. 记录 rate-limit 和完成日志
    5. 返回旧 payload 合同
- 新增定向测试：
  - `backend/tests/services/crawl/test_single_crawl_workflow.py`

## 验证
- `cd backend && SKIP_DB_RESET=1 python -m pytest tests/services/crawl/test_single_crawl_workflow.py tests/tasks/test_comments_preview_toggle.py -q`
- `python -m py_compile backend/app/services/crawl/single_crawl_workflow.py backend/app/tasks/crawler_task.py`
- `SKIP_DB_RESET=1 make test-quality-gate`

## 结果
- `_crawl_single(...)` 这条单社区抓取主链已经开始有自己的独立齿轮了
- `crawler_task` 更像 task 入口，不再亲手跑完整单社区抓取 side-effect 链
- `_crawl_single` / `_crawl_single_impl` 外部调用口径保持不变，现有 seam 没被砍断

## 下一步
- 继续第三轮，优先专打剩余最重的几块：
  1. `facts / 报告模块`
  2. `数据采集模块` 剩余 wrapper / side-effect
  3. `语义 / 标签模块` 剩余 sync / import-export 接缝
