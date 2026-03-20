# Phase 358 - 内容哈希去重查询独立 service

## 时间
- 2026-03-17

## 本轮目标
- 收掉 `IncrementalCrawler` 里还挂着的内容哈希去重查询
- 让 dedup 查询口径开始只有一个正式真相源

## 发现了什么
- `backend/app/services/crawl/incremental_crawler.py` 里的 `_find_content_duplicate(...)`
  之前还在入口壳里自己背：
  - `text_norm_hash` 可用性判断
  - 内容拼装
  - `posts_raw` 查询
  - 失败吞并日志
- 这类查询型逻辑更合理的归宿应该是独立 service，而不是继续挂在入口壳上。

## 这次做了什么
- 新增独立 service：
  - `backend/app/services/crawl/content_duplicate_service.py`
- 正式收了：
  - `ContentDuplicateLookupInput`
  - `ContentDuplicateLookupDeps`
  - `find_content_duplicate(...)`
- 收薄入口：
  - `backend/app/services/crawl/incremental_crawler.py`
  - `_find_content_duplicate(...)` 现在只负责组装 input / deps 并调用 service
- 新增定向测试：
  - `backend/tests/services/crawl/test_content_duplicate_service.py`

## 验证
- `cd backend && SKIP_DB_RESET=1 python -m pytest tests/services/crawl/test_content_duplicate_service.py tests/services/crawl/test_incremental_crawler_dedup.py -q`
- `cd backend && python -m py_compile app/services/crawl/content_duplicate_service.py app/services/crawl/incremental_crawler.py`
- `SKIP_DB_RESET=1 make test-quality-gate`

## 结果
- 内容哈希去重查询开始有自己的正式齿轮
- `IncrementalCrawler` 又薄了一层
- dedup 查询口径不再继续长在入口壳里

## 下一步
- 继续第三轮，优先专打剩余最重的几块：
  1. `数据采集模块`
  2. `语义 / 标签模块`
  3. `facts / 报告模块` 剩余 seam
