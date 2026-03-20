# Phase 343 - 第三轮继续推进：Incremental Dual Write Service 独立化

## 本轮目标

继续第三轮结构性打磨，把 `IncrementalCrawler._dual_write()` 里还缠着的冷热双写编排链拆成独立 service，让 `IncrementalCrawler` 继续变薄。

## 发现的问题

- `backend/app/services/crawl/incremental_crawler.py` 里的 `_dual_write()` 之前还在自己背：
  - 冷库逐条 upsert
  - `current unique` 冲突吞并
  - 冷库 flush/commit
  - 热缓存 best-effort 写入
  - `posts_latest` 刷新触发
  - comment backfill 触发
- 这让 `IncrementalCrawler` 继续同时承担：
  - 抓取入口
  - 冷热双写编排
  - 后置刷新与评论回填触发

大白话说：

- `IncrementalCrawler` 还在一边编排抓取，一边亲手跑完整双写链。

## 修复动作

### 1. 新增独立 service

新增：

- `backend/app/services/crawl/incremental_post_persistence_service.py`

正式收了：

- `DualWriteInput`
- `DualWriteDeps`
- `DualWriteResult`
- `execute_dual_write(...)`

这条 service 现在统一承接：

- 冷库逐条 upsert 编排
- `ux_posts_raw_current` 冲突识别
- 冷库 flush/commit
- 热缓存 best-effort 写入与提交
- `posts_latest` 刷新触发
- comment backfill 触发

### 2. 收薄 IncrementalCrawler

修改：

- `backend/app/services/crawl/incremental_crawler.py`

`_dual_write()` 现在改成薄委托：

1. 组装 `DualWriteInput`
2. 组装 `DualWriteDeps`
3. 调 `execute_dual_write(...)`
4. 把结果转回旧的 tuple 合同

这样旧调用口还在，但真正的编排逻辑已经回到独立齿轮里。

### 3. 补测试并锁新边界

新增：

- `backend/tests/services/crawl/test_incremental_post_persistence_service.py`

覆盖：

- `current unique` 冲突会稳定计入 duplicate
- 有新增/更新时会触发 `posts_latest` 刷新
- comment backfill 只吃新增帖子

继续保留并跑通：

- `backend/tests/services/infrastructure/test_dual_write_current_violation.py`

这样新 service 和旧 wrapper 两边的合同都被锁住了。

## 结果

- `IncrementalCrawler._dual_write()` 不再亲手维护整条冷热双写编排链
- 冷库/热缓存/刷新/comment backfill 这条 side-effect 链开始有独立真相源
- 后面再改：
  - 冲突口径
  - best-effort 热缓存
  - 刷新触发
  - 评论回填触发
  不容易再把 `IncrementalCrawler` 一起拖重

## 验证

### 定向回归

```bash
cd backend && SKIP_DB_RESET=1 python -m pytest \
  tests/services/crawl/test_incremental_post_persistence_service.py \
  tests/services/infrastructure/test_dual_write_current_violation.py -q
```

结果：

- `3 passed`

### 语法自检

```bash
cd backend && python -m py_compile \
  app/services/crawl/incremental_post_persistence_service.py \
  app/services/crawl/incremental_crawler.py \
  tests/services/crawl/test_incremental_post_persistence_service.py
```

结果：

- 通过

### 主门禁

```bash
cd /Users/hujia/Desktop/RedditSignalScanner && SKIP_DB_RESET=1 make test-quality-gate
```

结果：

- `27 passed`

## 额外记录

我额外跑了更宽的 dedup 回归，发现两条旧断点仍然存在：

- `tests/services/crawl/test_incremental_crawler_dedup.py::TestIncrementalCrawlerDedup::test_update_detection`
- `tests/services/crawl/test_incremental_crawler_dedup.py::TestIncrementalCrawlerDedup::test_scd2_creates_new_version_and_expires_previous`

这两条暴露的是旧的 `posts_raw current` 约束与版本切换链之间的历史问题，不是这次 `dual_write service` 拆分新引入的断点，所以没有混成本轮成果。

## 当前判断

这一步是第三轮里一刀真正值钱的结构性收口：

- `IncrementalCrawler` 继续变薄
- 双写 side-effect 链开始有独立齿轮
- 数据采集模块继续往“职责清楚、统一接口协同、彼此少牵连”推进

## 下一步

继续第三轮，不换打法，优先继续专打剩余最重的耦合点：

1. `facts / 报告模块`
2. `数据采集模块`
3. `语义 / 标签模块`
